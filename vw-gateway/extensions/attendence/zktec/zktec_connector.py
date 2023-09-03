import json
import os
from threading import Thread
import traceback
from thingsboard_gateway.connectors.connector import Connector, log
from thingsboard_gateway.gateway.constant_enums import DownlinkMessageType, Status
from pathlib import Path
from zk import ZK, const
from zk.exception import ZKErrorResponse, ZKNetworkError
from datetime import datetime
import time
import pytz
import logging
from simplejson import dumps
import threading
import signal
import sys
from schema import Schema, And, Use, Optional, SchemaError, Or
from functools import reduce

sem = threading.Semaphore(1)

MASCK_MAX = 62
MASCK_MIN = 1

def _check_magic_number(magic_number):
    if (magic_number > MASCK_MAX or magic_number < 0):
        raise Exception(
            'Magic number must bigger than {} and smaller than {}'.format(MASCK_MIN, MASCK_MAX))


def _check_user_id_company(user_id_company):
    if (user_id_company >= (MASCK_MIN << 9)):
        raise Exception(
            'Uaser ID from company must be bigger than 1 and smaller than {}'.format(MASCK_MIN))


def is_device_id(magic_number, user_id_device):
    if magic_number == 0x0:
        return True
    return (int(user_id_device) >> 9) == magic_number


def convert_to_device_id(magic_number, user_id_company):
    if magic_number == 0x0:
        return user_id_company
    _check_magic_number(magic_number)
    _check_user_id_company(user_id_company)
    return (magic_number << 9) | user_id_company


def convert_to_company_id(magic_number, user_id_device):
    user_id_device = int(user_id_device)
    if magic_number == 0x0:
        return user_id_device
    _check_magic_number(magic_number)
    return (magic_number << 9) ^ user_id_device


def not_equal_packet(packet_send, packet_save):
    if len(packet_send["telemetry"]) != 0 or packet_save["attributes"] != packet_send["attributes"]:
        return True


ATTENDANCE_TELEMETRY_SCHEMA = Schema({
    Optional('deviceName'): And(str, len),
    Optional('deviceType'): And(str,len),
    Optional('attributes'):[{
        'Device_name': str
    }],
    Optional('telemetry'):[{
        "ts": Or(int, float),
        "values": {
            "user_id": And(int),
            "timestamp":  And(str, len),
            "punch": And(str, len),
            "device_name":  And(str, len),
        }
    }]
}, ignore_extra_keys=True)


class ZktecPro(Connector, Thread):

    def __init__(self, gateway, config, connector_type):
        super().__init__()
        self.statistics = {'MessagesReceived': 0,
                           'MessagesSent': 0}
        self.gateway = gateway  # Reference to TB Gateway
        self.connector_type = connector_type  # Use For Convertor
        self.config = config  # zktec.json Contents

        # Extract main sections from configuration ---------------------------------------------------------------------
        self.__device = config.get('device')
        self.__storage_path = config.get('storage', ".")
        self._name = self.__device.get('name', 'zktec')
        self._ip = self.__device.get('ip', '127.0.0.1')
        self._port = self.__device.get('port', "1883")
        self._password = self.__device.get('password', "1")
        self._timezone = self.__device.get('timezone', "210")
        self._magic_number = int(self.__device.get('magic_number', "0"))

        # Set up lifecycle flags ---------------------------------------------------------------------------------------
        self.connection = False  # Service variable for check connection to device
        self.__logger = logging.getLogger("zkteck-"+self._ip)
        self.__deviceName = config.get('deviceName', 'deviceName')
        self.__deviceType = config.get('deviceType', 'default')

        # Create device
        self.gateway.add_device(self.__deviceName, {"connector": self},
                                device_type=self.__deviceType)
        
        log.info("Starting Custom connector")

    def get_config(self):
        return self.config

    def get_name(self):
        return self.name

    def is_connected(self):
        return self._is_zkteco_connected()

    def run(self):
        while (True):
            try:
                self._run()
            except Exception as ex:
                logging.error('ZKTec unsupported exception happend: %s', ex)

                traceback.print_exc()
                # Note: for network connection
                try:
                    self._zkteco_connect()
                except:
                    pass

            finally:
                time.sleep(30)

    def _run(self):
        result_dict = {
            'deviceName': self.__deviceName,
            'deviceType': self.__deviceType,
            'attributes': [],
            'telemetry': [],
        }

        self._zkteco_connect()
        
        # Send Attribute
        result_dict['attributes'].append(self._zkteco_get_attribute())

        # Send Telemetry
        attendances = self._zkteco_get_attendance()
        for attendance in attendances:
            self._remove_timezone(attendance)
            if self._should_send_attendance(attendance):
                result_dict['telemetry'].append(self._convert_attendance_to_telemetry(attendance))
                with open(self.__storage_path + '/should.txt', 'w') as f:
                    f.writelines(str(result_dict['telemetry']))
        # Send result to thingsboard
        if self._must_send_to_storage(result_dict) and self._send_to_storage(result_dict):
            with open(self.__storage_path + '/must.txt', 'w') as f:
                f.writelines(str(result_dict['telemetry']))
            self.PACKET_SAVE = result_dict
    def open(self):
        # TODO: maso, 2023: check the biz follow of open
        self.stopped = False
        self.start()

    def close(self):
        self._zkteco_close()
        # TODO: maso, 2023: check if we have to stop main thread too

    def on_attributes_update(self, content):
        # TODO: maso, 2023: I do not know what is it for?
        pass

    def server_side_rpc_handler(self, content):
        try:
            self._server_side_rpc_handler(content, 3)
        except Exception as ex:
            self.__logger.error("ZKTec unsupported exception happend %s", ex)
            traceback.print_exc()

            self.gateway.send_rpc_reply(
                device=content["device"],
                req_id=content["data"]["id"],
                content={"success_sent": "False",
                         "message": "ZKTec unsupported exception happend %s" % ex}
            )

    def _server_side_rpc_handler(self, content, tries_count=3):
        params = content["data"]["params"]
        method_name = content["data"]["method"]
        try:
            # update_user
            if method_name == "update_user":
                return self.update_user(params, content)

            # delete user
            if method_name == "del_user":
                return self.del_user(params, content)

            # update fingerprint
            if method_name == "update_fingerprint":
                return self.update_fingerprint(params)
        except ZKNetworkError as netex:
            self.__logger.error(
                "ZKTec network error detected : %s, %s", netex, traceback.extract_stack)
            if tries_count > 0:
                self._zkteco_connect()
                return self._server_side_rpc_handler(content, tries_count-1)
            raise netex

    ##############################################################################################
    #                                 packets utils
    ##############################################################################################
    PACKET_SAVE = {'attributes': [],
               'telemetry': []}
    
    def _must_send_to_storage(self, result_dict):
        # Check Successful Send
        if not not_equal_packet(result_dict, self.PACKET_SAVE):
            return False
    
        try:
            ATTENDANCE_TELEMETRY_SCHEMA.validate(result_dict)
        except SchemaError as ex:
            self.__logger.error("ZKTec unsupported exception happend %s", ex)
            traceback.print_exc()
            return False
        
        return True
    
    def _should_send_attendance(self, attendance):
        lastdatetime = self.lastdatetime_text_file()
        # TODO: maso, 2023: check last time stamp
        return datetime.timestamp(attendance.timestamp) > lastdatetime and is_device_id(self._magic_number, attendance.user_id)

    def _remove_timezone(self, attendance):
        tz = pytz.FixedOffset(int(self._timezone))

        datetimeOrg = attendance.timestamp
        dateTimeUts = datetime(
            datetimeOrg.year,
            datetimeOrg.month,
            datetimeOrg.day,
            datetimeOrg.hour,
            datetimeOrg.minute,
            datetimeOrg.second,
            tzinfo=tz
        )
        attendance.timestamp = datetime.fromtimestamp(
            datetime.timestamp(dateTimeUts))
        return attendance.timestamp

    def _convert_attendance_to_telemetry(self, attendance):
        attendance_telemetry = {
            "ts": attendance.timestamp.timestamp()*1000,
            "values": {
                "user_id": convert_to_company_id(
                    magic_number=self._magic_number,
                    user_id_device=int(attendance.user_id)
                ),
                "timestamp": str(attendance.timestamp),
                "punch": 'out' if attendance.punch == 2 else 'in',
                "device_name": self.__deviceName
            }
        }
        return attendance_telemetry
    # Main method of thread, must contain an infinite loop and all calls to data receiving/processing functions.

    def get_storage_path(self):
        path_storage = Path(self.__storage_path + '/%s.txt' %
                            self.config.get('deviceName'))
        return path_storage

    ##############################################################################################
    #                             zkteck connection utils
    ##############################################################################################

    def _is_zkteco_connected(self):
        return self.connection and self.connection.is_connect

    def _zkteco_close(self):
        if self._is_zkteco_connected():
            self.connection.disconnect()
            self.connection = None

    def _zkteco_connect(self):
        """connects to the device throu tcp

        raise excpetion if connection fail
        """
        # if self.connection and not self.connection.disconnect():
        #     raise Exception("Fail to disconnect from device. Something bad happend.")

        self.connection = ZK(
            self._ip,
            port=int(self._port),
            timeout=5,
            password=int(self._password),
            force_udp=False,
            ommit_ping=True,
            verbose=False,
            encoding="cp1256"

        )
        if not self.connection.connect():
            raise Exception("Fail to connect to the device")

    ##############################################################################################
    #                                 zkteck util
    ##############################################################################################

    def _zkteco_get_attribute(self):
        try:
            sem.acquire()
            try:
                self.connection.read_sizes()
            except:
                logging.info("Usage Space device Not available")
            try:
                firmware_version = self.connection.get_firmware_version()
            except:
                logging.info("Firmware Version device Not available")
            try:
                serialnumber = self.connection.get_serialnumber()
            except:
                logging.info("Serial Number device Not available")
            try:
                platform = self.connection.get_platform()
            except:
                logging.info("Platform device Not available")
            try:
                device_name = self.connection.get_device_name()
            except:
                logging.info("Device Name Not available")
            try:
                face_version = self.connection.get_face_version()
            except:
                logging.info("Face Version device Not available")
            try:
                fp_version = self.connection.get_fp_version()
            except:
                logging.info("Finter Print Version device Not available")
            try:
                extend_fmt = self.connection.get_extend_fmt()
            except:
                logging.info("Extend FMT device Not available")
            try:
                user_extend_fmt = self.connection.get_user_extend_fmt()
            except:
                logging.info("User Extend FMT device Not available")
            try:
                face_fun_on = self.connection.get_face_fun_on()
            except:
                logging.info("Face Fun On device Not available")
            try:
                compat_old_firmware = self.connection.get_compat_old_firmware(),
            except:
                logging.info("Compat Old Firmware device Not available")
            try:
                network_params = self.connection.get_network_params()
            except:
                logging.info("Network Params device Not available")
            try:
                mac = self.connection.get_mac()
            except:
                logging.info("Mac device Not available")
            try:
                pin_width = self.connection.get_pin_width()
            except:
                logging.info("pin_width device Not available")

            return {
                "Records": self.connection.records,
                "Max Records": self.connection.rec_cap,
                "Users": self.connection.users,
                "Max Users": self.connection.users_cap,
                "Fingers": self.connection.fingers,
                "Max Fingers": self.connection.fingers_cap,
                "Faces": self.connection.faces,
                "Max Faces": self.connection.faces_cap,
                "Firmware Version": firmware_version,
                "Serialnumber": serialnumber,
                "Platform": platform,
                "Device_name": device_name,
                "Face Version": face_version,
                "Finger Print Version": fp_version,
                "Extend Fmt": extend_fmt,
                "User Extend Fmt": user_extend_fmt,
                "Face Fun On": face_fun_on,
                "Compat Old Firmware": compat_old_firmware,
                "Network Params": network_params,
                "Mac": mac,
                "Pin Width": pin_width
            }
        finally:
            sem.release()

    def update_fingerprint(self, params):
        magic_user_id = convert_to_device_id(
            user_id_company=int(params["user_id_change"]),
            magic_number=self._magic_number
        )
        self._zkteco_enroll_user(magic_user_id)


    def update_user(self, params, content):

        if not self._is_zkteco_connected():
            raise Exception("Device is not connected")

        users = self._zkteco_get_users()

        for key, value in params.items():
            # Check user is exist
            exist_user = 0
            for item in users:
                if item.user_id == value["user_id"]:
                    exist_user = item

            # set magic number
            magic_user_id = convert_to_device_id(
                user_id_company=int(value["uid"]),
                magic_number=self._magic_number)

            # user not exist Create user
            if exist_user == 0:
                self._zkteco_set_user(magic_user_id,
                                      value["name"],
                                      value["privilege"],
                                      value["password"],
                                      value["group_id"],
                                      str(magic_user_id),
                                      int(value["card"]))
            else:
                # user is exist delete and create
                # save finger print

                fingers = self._zkteco_get_templates()

                save_fingers = []
                for finger in fingers:
                    if finger.uid == magic_user_id:
                        save_fingers.append(finger)

                self._zkteco_delete_user(user_id=str(magic_user_id))
                self._zkteco_set_user(magic_user_id,
                                      value["name"],
                                      value["privilege"],
                                      value["password"],
                                      value["group_id"],
                                      str(magic_user_id),
                                      int(value["card"])
                                      )
                # add finger print
                self._zkteco_save_user_template(magic_user_id, save_fingers)

            self._gateway_send_rpc_reply(
                device=content["device"],
                req_id=content["data"]["id"],
                content={"success_sent": 'True'}
            )

    def del_user(self, params, content):
        if not self._is_zkteco_connected():
            raise Exception("Device is not connected")

        for key, value in params.items():
            magic_user_id = convert_to_device_id(
                user_id_company=int(value['user_id_delete']),
                magic_number=self._magic_number)

            self._zkteco_delete_user(str(magic_user_id))

            self.gateway.send_rpc_reply(
                device=content["device"],
                req_id=content["data"]["id"],
                content={"success_sent": 'True'}
            )

    def _zkteco_get_users(self):
        sem.acquire()
        try:
            return self.connection.get_users()
        finally:
            sem.release()

    def _zkteco_delete_user(self, user_id):
        sem.acquire()
        try:
            self.connection.delete_user(user_id)
        finally:
            sem.release()

    def _zkteco_set_user(self, *args, **kwargs):
        sem.acquire()
        try:
            self.connection.set_user(*args, **kwargs)
        finally:
            sem.release()

    def _zkteco_get_attendance(self):
        sem.acquire()
        try:
            return self.connection.get_attendance()
        finally:
            sem.release()

    def _zkteco_get_templates(self):
        sem.acquire()
        try:
            return self.connection.get_templates()
        finally:
            sem.release()

    def _zkteco_save_user_template(self, *args, **kwargs):
        sem.acquire()
        try:
            self.connection.save_user_template(*args, **kwargs)
        finally:
            sem.release()
    
    
    def _zkteco_enroll_user(self, *args, **kwargs):
        if not self._is_zkteco_connected():
            raise Exception("Device is not connected")
        sem.acquire()
        try:
            self.connection.enroll_user(*args, **kwargs)
        finally:
            sem.release()




    ##############################################################################################
    #                                 Gateway util
    ##############################################################################################
    
    def _gateway_send_rpc_reply(self, *args, **kwargs):
        self.gateway.send_rpc_reply(*args, **kwargs)
    
    
    def _send_to_storage(self, result_dict):
        if self.gateway.send_to_storage(self.get_name(), result_dict) == Status.SUCCESS:
            init_value = {
                'ts': 0
            }
            latest = reduce(lambda x, y: x if x['ts'] > y['ts'] else y, result_dict['telemetry'], init_value)
            if latest['ts'] == 0:
                return True
            path = self.get_storage_path()
            if not os.path.exists(os.path.dirname(path.absolute())):
                try:
                    os.makedirs(os.path.dirname(path.absolute()))
                except OSError as exc: # Guard against race condition
                    raise
            with open(path, 'w') as f:
                f.write(str(latest['ts']))
            return True
        return False
            
    
    def lastdatetime_text_file(self):
        # Fetch last date time
        try:
            with open(self.get_storage_path(), 'r') as f:
                lines = f.readlines()
                return float(lines[0])
        except:
            return 0