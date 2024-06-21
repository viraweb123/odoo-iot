import threading
import traceback
import cups  
from threading import Thread
from thingsboard_gateway.connectors.connector import Connector, log
import time
import os
import logging
from collections import Counter
import sys
import base64
import tempfile

sem = threading.Semaphore(1)

PACKET_SAVE ={'attributes': [],
                'telemetry': []}


def equal_packet(packet_send, packet_save):
    if packet_save["telemetry"] == packet_send["telemetry"] and packet_save["attributes"] == packet_send["attributes"]:
        return True
    else:
        return False
      
class CUPSPro(Connector, Thread): 
    # TODO : IPPError, HTTPEttor, check try except
    
    def __init__(self, gateway, config, connector_type):
        super().__init__()
        self.statistics = {'MessagesReceived': 0,
                           'MessagesSent': 0}
        self.gateway = gateway  # Reference to TB Gateway
        self.connector_type = connector_type  # Use For Convertor
        self.config = config  # sii.json Contents

        # Extract main sections from configuration ---------------------------------------------------------------------
        self.__prefix = config.get('prefix', 'prefix')
        self.__deviceName = config.get('deviceName', 'deviceName')
        self.__deviceType = config.get('deviceType', 'default')
        
        # XXX: maso, 2023: rais error if prefix is not set
        # Set up lifecycle flags ---------------------------------------------------------------------------------------
        self.connection = False  # Service variable for check connection to device
        self.__logger = logging.getLogger("cups-"+self.__deviceName)
        
        # Create device
        self.connection = cups.Connection()
        self.printers = self.connection.getPrinters()
                
        for key, config in self.printers.items():
            self.gateway.add_device(self.__prefix + key, {"connector": self},
                                    device_type=self.__deviceType)
 
    def connect_device(self):
        """connects to the device throu tcp
        
        raise excpetion if connection fail
        """
        try:
            self.connection = cups.Connection()
            self.printers = self.connection.getPrinters()
                
        except (cups.IPPError) as e:
            pass
           
    def open(self): 
        self.stopped = False
        self.start()

    def get_name(self):
        return self.name

    def is_connected(self):
        return self.connection 
    
    def find_jobs(self):
        # Find jobs
        dict_jobs_counter = {}
        job_completed = self.connection.getJobs(which_jobs='completed')
        job_not_completed = self.connection.getJobs(which_jobs='not-completed')
        job_all = self.connection.getJobs(which_jobs='all')

        # Completed Jobs
        result_job_completed= []
        for job in job_completed:
            string = self.connection.getJobAttributes(job)['job-printer-uri']
            printer_name_for_select_job = list(string.split("/"))[-1]
            result_job_completed.append(printer_name_for_select_job)
        dict_count_job_completed = Counter(result_job_completed)

        # Not_Completed Jobs
        result_job_not_completed= []
        for job in job_not_completed:
            string = self.connection.getJobAttributes(job)['job-printer-uri']
            printer_name_for_select_job = list(string.split("/"))[-1]
            result_job_not_completed.append(printer_name_for_select_job)
        dict_count_job_not_completed = Counter(result_job_not_completed)

        # All Jobs
        result_job_all= []
        for job in job_all:
            string = self.connection.getJobAttributes(job)['job-printer-uri']
            printer_name_for_select_job = list(string.split("/"))[-1]
            result_job_all.append(printer_name_for_select_job)
        dict_count_job_all = Counter(result_job_all)

        # Add Counter jobs
        dict_jobs_counter["Completed_jobs"] = dict_count_job_completed
        dict_jobs_counter["not_completed_jobs"] = dict_count_job_not_completed
        dict_jobs_counter["all_jobs"] = dict_count_job_all
        
        return dict_jobs_counter
     
    # Main method of thread, must contain an infinite loop and all calls to data receiving/processing functions.
    def run(self):   
        
        while (True):
            try:
                if not self.is_connected():
                    self.connect_device()
                    
                # Find jobs
                dict_count_job_all = self.find_jobs() 
                
                for key, config in self.printers.items():
                    self.result_dict = {
                        'deviceName': self.__prefix + key,
                        'deviceType': self.__deviceType,
                        'attributes': [],
                        'telemetry': [],
                    }
                    
                    # Send attribute 
                    for attribute_key in ['printer-is-shared', 'printer-state', 'printer-state-message', 'printer-state-reasons', 'printer-type',
                                          'printer-uri-supported', 'printer-location', 'printer-info', 'device-uri', 'printer-make-and-model']:
                        self.result_dict['attributes'].append({
                            attribute_key: config[attribute_key]
                        })
                        
                    # Send telemetry
                    for key_counter , value_counter in dict_count_job_all.items():
                        self.result_dict['telemetry'].append({
                        key_counter: value_counter[key]
                    })

                    if not equal_packet(self.result_dict,PACKET_SAVE):
                        # Send result to thingsboard
                        self.gateway.send_to_storage(self.get_name(), self.result_dict)
                        PACKET_SAVE["attributes"] = self.result_dict["attributes"]
                        PACKET_SAVE["telemetry"] = self.result_dict["telemetry"]
                        
            except:
                logging.error("Printer Not Connected")
                
            
            time.sleep(30)
    
    def close(self):
        #printer_names = self.connection.printers.keys()
        #for printer_name in printer_names:    
        #        self.connection.disablePrinter(printer_name)
        #signal.signal(signal.SIGINT, self.signal_handler)
        #signal.signal(signal.SIGINT, self.stop())
        pass
        
    def on_attributes_update(self, content):
        pass
    
    def print_file(self, printer_name , printer_file): 
        printid = self.connection.printFile(printer_name, printer_file ,'' , {})
        
    def server_side_rpc_handler(self, content):
        sem.acquire()
        try:
            self._server_side_rpc_handler(content, 3)
        except Exception as ex :
            self.__logger.error("Cups unsupported exception happend %s", ex)
            traceback.print_exc()
            
            self.gateway.send_rpc_reply(
                device= content["device"], 
                req_id= content["data"]["id"],
                content = {"success_sent":"False" , "message" :"Cups unsupported exception happend %s" % ex }
            )
        finally: 
            sem.release()
            time.sleep(0.25)

    def _server_side_rpc_handler(self, content, tries_count=3):
        params = content["data"]["params"]
        method_name = content["data"]["method"]
        
        # printer_file is encode string so first decode string
        try:
            if method_name == "print_file":
                # create temporary directory
                temp = tempfile.NamedTemporaryFile(suffix=params["suffix_file_name"])
                
                try:
                    coded_string = params["content"]
                    base64_decode = base64.b64decode(coded_string)
                    text_file = open(temp.name, "wb")
                    n = text_file.write(base64_decode)
                    self.print_file(content["device"].replace(self.__prefix, ""), temp.name)
                    #content["device"].replace(self.__prefix, "")
                finally:
                    temp.close()
    
                
        except Exception as ex :
            self.__logger.error("Cups unsupported exception happend : %s, %s", ex, traceback.extract_stack)
            if tries_count > 0:
                self.connect_device()
                return self._server_side_rpc_handler(content, tries_count-1)
            raise ex
            
