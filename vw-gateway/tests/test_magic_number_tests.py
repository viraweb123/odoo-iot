import zktec_connector
import unittest
from unittest.mock import MagicMock
import sys
import os
from thingsboard_gateway.gateway.constant_enums import DownlinkMessageType, Status
from datetime import datetime

from zk import attendance

sys.path.append(os.path.abspath(
    '/home/sanaz/viraweb123/odoo-iot/vw-gateway/extensions/attendence/zktec'))


class Object(object):
    pass


class TestStringMethods(unittest.TestCase):

    def test_convert_to_device_id(self):
        data = [
            (1, 31745, 62),
            (1, 0x3C01, 30),
            (1, 0x201,  1),
            (1, 513,  1),
            # Magic number is default
            (513, 513, 0),
            (4095, 4095, 0x0),
        ]
        for user_id, device_id, magic_number in data:
            self.assertEqual(zktec_connector.convert_to_device_id(magic_number, user_id),
                             device_id)
            self.assertEqual(zktec_connector.convert_to_company_id(magic_number, device_id),
                             user_id)

    def test_convert_to_device_id_invalid(self):
        ids = [
            2500,
            6000,
            2049,
        ]
        magic_number = 0x7c00
        for id in ids:
            self.assertRaises(
                Exception, zktec_connector.convert_to_device_id, magic_number, id)

    def test_convert_to_device_id_invalid_magic_number(self):
        id = 0x01
        magic_number = 0x8c00
        self.assertRaises(
            Exception, zktec_connector.convert_to_device_id, magic_number, id)

    def test_send_to_storage(self):
        config = Object()
        device = Object()
        gateway = Object()
        connector_type = Object()

        device.get = MagicMock(return_value='1')
        gateway.send_to_storage = MagicMock(return_value=Status.SUCCESS)
        gateway.add_device = MagicMock(return_value=True)

        def side_effect_func(val, *args, **kwargs):
            if val == 'device':
                return device
            return 'test'
        config.get = MagicMock(side_effect=side_effect_func)

        connction = zktec_connector.ZktecPro(gateway, config, connector_type)
        self.assertIsNotNone(connction)

        result_dict = {
            'telemetry': [{
                "ts": 1,
                "values": {
                    "user_id": 3,
                    "timestamp":  "2023-10-4 10:01:00",
                    "punch": "out",
                    "device_name":  "test2"}
            }, {
                "ts": 2,
                "values": {
                    "user_id": 3,
                    "timestamp":  "2023-10-4 10:02:00",
                    "punch": "out",
                    "device_name":  "test2"}
            }, {
                "ts": 3,
                "values": {
                    "user_id": 3,
                    "timestamp":  "2023-10-4 10:03:00",
                    "punch": "out",
                    "device_name":  "test2"}
            }]
        }
        path = connction.get_storage_path()
        path.unlink(missing_ok=True)

        connction._send_to_storage(result_dict)
        self.assertTrue(path.is_file())

        self.assertEqual(3, connction.lastdatetime_text_file())
        path.unlink(missing_ok=True)

    def test_lastdatetime_text_file(self):
        config = Object()
        device = Object()
        gateway = Object()
        connector_type = Object()

        device.get = MagicMock(return_value='1')
        gateway.send_to_storage = MagicMock(return_value=Status.SUCCESS)
        gateway.add_device = MagicMock(return_value=True)

        def side_effect_func(val, *args, **kwargs):
            if val == 'device':
                return device
            return 'test'
        config.get = MagicMock(side_effect=side_effect_func)

        connction = zktec_connector.ZktecPro(gateway, config, connector_type)
        self.assertIsNotNone(connction)

        path = connction.get_storage_path()
        path.unlink(missing_ok=True)
        self.assertEqual(0, connction.lastdatetime_text_file())
        path.unlink(missing_ok=True)

    def test_run_single(self):
        config = Object()
        device = Object()
        gateway = Object()
        connector_type = Object()

        device.get = MagicMock(return_value='1')
        gateway.send_to_storage = MagicMock(return_value=Status.SUCCESS)
        gateway.add_device = MagicMock(return_value=True)

        def side_effect_func(val, *args, **kwargs):
            if val == 'device':
                return device
            return 'test'
        config.get = MagicMock(side_effect=side_effect_func)

        connction = zktec_connector.ZktecPro(gateway, config, connector_type)
        self.assertIsNotNone(connction)

        connction._zkteco_connect = MagicMock(return_value=True)
        connction._zkteco_get_attribute = MagicMock(return_value={
            "ZKTec Error": False,
            "Records": 100,
            "Max Records": 1000,
            "Users": 10,
            "Max Users": 1000,
            "Fingers": 20,
            "max_fingers": 2000,
            "Faces": 10,
            "Max Faces": 1000,
            "Firmware Version": "version",
            "Serialnumber": "1234558",
            "Platform": "platform",
            "Device_name": "device_name",
            "Face Version": "face_version",
            "Finger Print Version": "fp_version",
            "Extend Fmt": "extend_fmt",
            "User Extend Fmt": "user_extend_fmt",
            "Face Fun On": "face_fun_on",
            "Compat Old Firmware": "compat_old_firmware",
            "Network Params": "network_params",
            "Mac": "mac",
            "Pin Width": "pin_width"
        })
        connction._zkteco_get_attendance = MagicMock(return_value=[])

        connction._run()
        self.assertEqual(gateway.send_to_storage.call_count, 1)

        connction._run()
        self.assertEqual(gateway.send_to_storage.call_count, 1)

    def test_run_single_with_telemetry(self):
        config = Object()
        device = Object()
        gateway = Object()
        connector_type = Object()

        device.get = MagicMock(return_value='0')
        gateway.send_to_storage = MagicMock(return_value=Status.SUCCESS)
        gateway.add_device = MagicMock(return_value=Status.SUCCESS)

        def side_effect_func(val, *args, **kwargs):
            if val == 'device':
                return device
            if val == 'magic_number':
                return 3
            return 'test'
        config.get = MagicMock(side_effect=side_effect_func)

        connction = zktec_connector.ZktecPro(gateway, config, connector_type)
        self.assertIsNotNone(connction)

        connction._zkteco_connect = MagicMock(return_value=True)
        connction._zkteco_get_attribute = MagicMock(return_value={
            "ZKTec Error": False,
            "Records": 100,
            "Max Records": 1000,
            "Users": 10,
            "Max Users": 1000,
            "Fingers": 20,
            "max_fingers": 2000,
            "Faces": 10,
            "Max Faces": 1000,
            "Firmware Version": "version",
            "Serialnumber": "1234558",
            "Platform": "platform",
            "Device_name": "device_name",
            "Face Version": "face_version",
            "Finger Print Version": "fp_version",
            "Extend Fmt": "extend_fmt",
            "User Extend Fmt": "user_extend_fmt",
            "Face Fun On": "face_fun_on",
            "Compat Old Firmware": "compat_old_firmware",
            "Network Params": "network_params",
            "Mac": "mac",
            "Pin Width": "pin_width"
        })
        connction._zkteco_get_attendance = MagicMock(return_value=[
            attendance.Attendance(user_id=1, timestamp=datetime(
                2022, 1, 1, 8, 0, 1), status=1, punch=0, uid=1),
            attendance.Attendance(user_id=1, timestamp=datetime(
                2022, 1, 1, 9, 0, 1), status=1, punch=1, uid=1),
            attendance.Attendance(user_id=1, timestamp=datetime(
                2022, 1, 1, 10, 0, 1), status=1, punch=0, uid=1),
            attendance.Attendance(user_id=1, timestamp=datetime(
                2022, 1, 1, 11, 0, 1), status=1, punch=1, uid=1),
        ])

        connction._run()
        self.assertEqual(gateway.send_to_storage.call_count, 1)

        connction._run()
        self.assertEqual(gateway.send_to_storage.call_count, 1)

    def test_run_telemetry_with_magic_number(self):
        config = Object()
        device = Object()
        gateway = Object()
        connector_type = Object()

        def side_effect_func_device(val, *args, **kwargs):
            if val == 'magic_number':
                return '1'
            return '0'
        device.get = MagicMock(side_effect=side_effect_func_device)
        gateway.send_to_storage = MagicMock(return_value=Status.SUCCESS)
        gateway.add_device = MagicMock(return_value=Status.SUCCESS)

        def side_effect_func(val, *args, **kwargs):
            if val == 'device':
                return device
            if val == 'magic_number':
                return 1
            return 'test'
        config.get = MagicMock(side_effect=side_effect_func)

        connector = zktec_connector.ZktecPro(gateway, config, connector_type)
        self.assertIsNotNone(connector)

        attendances = [
            attendance.Attendance(user_id=530, timestamp=datetime(
                2022, 1, 1, 8, 0, 1), status=1, punch=0,  uid=530),
            attendance.Attendance(user_id=530, timestamp=datetime(
                2022, 1, 1, 9, 0, 1), status=1, punch=1,  uid=530),
            attendance.Attendance(user_id=530, timestamp=datetime(
                2022, 1, 1, 10, 0, 1), status=1, punch=0, uid=530),
            attendance.Attendance(user_id=530, timestamp=datetime(
                2022, 1, 1, 11, 0, 1), status=1, punch=1, uid=530),
        ]
        conveted_attendance = connector._convert_attendance_to_telemetry(
            attendances[0], "ZMM220_TFT")
        self.assertEqual(conveted_attendance['values']['user_id'], 18)

if __name__ == '__main__':
    unittest.main()
