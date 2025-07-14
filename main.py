# updated: 2025-06-25 18:05:33
# created: 2024-06-13 14:30:00
# filename: main.py

#--------------------------------------------------------------------------------------------------------------
from time import sleep
from queue import Queue
from datetime import datetime
from logger import CustomLogger
from csv_writer import CSVwriter
from timers import ServiceTimers
from mqtt_client import MqttBroker
from machine_info import MachineInfo
from config_parser import Config_Init
from config_update import ConfigUpdate
from mqtt_out_queue import MQTToutQueue
from mongo_query_config import MongoQueryConfig
from mongo_query_general import MongoQueryGeneral       # on the fly db-queries and db-actions

#--------------------------------------------------------------------------------------------------------------
class Main (object):
    def __init__ (
            self,
            dtt = datetime.now ()
        )-> None:

        program_version = f"ROC-Access-Server V1.1.16"
        program_updated = "2025-06-25 18:05:33"

        insConfigInit = Config_Init()
        ini_general_variables_dict = insConfigInit.get_variables_dict (category="general")  # from config.ini file
        ini_config_variables_dict = insConfigInit.get_variables_dict (category="config")    # from config.ini file

        logger_enable = ini_general_variables_dict["logger_enable"]
        if logger_enable:
            custom_logger = CustomLogger(
                backup_count = 5,
                max_bytes = 10485760,
                logfile = ini_config_variables_dict["systemlog_file"],                     # from config.ini file
                logger_level = ini_config_variables_dict["logger_level"],                  # from config.ini file
                util_prt = ini_general_variables_dict["util_prt"],
                util_prt0 = ini_general_variables_dict["util_prt0"]
            )
            custom_logger.exclude_debug_entries(r".*Lock \d+ acquired on queue\.lock")
            custom_logger.debug("Lock 548462840704 acquired on queue.lock")
            custom_logger.log_info(f"[SYSTEM] ROC Access Server started!")
            insLogger = custom_logger  # ✅ correct assignment
        else:
            insLogger = None  # make sure any code that uses it checks if logger is not None

        csv_logging_enable = ini_general_variables_dict["csv_logging_enable"]
        if csv_logging_enable:
            insCSVtemperature = CSVwriter (
                insLogger,
                header = "temperatureHeader",
                filename = ini_config_variables_dict["csv_temperature_file"]   # derived from config.ini file (config_parser.py)
            )
        else:
            insCSVtemperature = None

        insMachineInfo = MachineInfo (
            insLogger,
            program_version,
            program_updated,
            util_prt = ini_general_variables_dict["util_prt"],
            util_prt0 = ini_general_variables_dict["util_prt0"]
        )

        # MONGO DATABASE
        insMongoConfig =  MongoQueryConfig(
            insLogger=custom_logger,
            ini_mongo_variables_dict=insConfigInit.get_variables_dict(category="mongo") # from config.ini file
        )

        general_settings_dict = insMongoConfig.query_config_general_settings() # derived from mongo database config
        self.gen_datim_format = general_settings_dict.get("datim_format")


        insMongoGeneral = MongoQueryGeneral(
            insLogger=custom_logger,
            ini_mongo_variables_dict = insConfigInit.get_variables_dict(category="mongo")
        )

        q = Queue ()

        insMQTTbroker = MqttBroker (
            q,
            insLogger,
            insMongoConfig,
            insMachineInfo,
            util_prt = ini_general_variables_dict["util_prt"],
            util_prt0 = ini_general_variables_dict["util_prt0"]
        )
        self.insMQTTbroker = insMQTTbroker

        insMQTToutQueue = MQTToutQueue (
            q,
            insLogger,
            insMQTTbroker,
            insMongoConfig,
            insMongoGeneral,
            insCSVtemperature,
            data_path = ini_config_variables_dict["data_path"],             # from config.ini file
            filename = ini_config_variables_dict["csv_transaction_file"],   # derived from config.ini file (config_parser.py)
            own_serial_number = insMachineInfo.get_own_serial_number(),
            csv_logging_enable = csv_logging_enable,
            util_prt = ini_general_variables_dict["util_prt"],
            util_prt0 = ini_general_variables_dict["util_prt0"]
        )
        self.insMQTToutQueue = insMQTToutQueue

        insTimers = ServiceTimers (
            dtt,
            insLogger,
            insMQTTbroker,
            insMongoConfig,
            insMachineInfo,
            insCSVtemperature,
            util_prt = ini_general_variables_dict["util_prt"],
            util_prt0 = ini_general_variables_dict["util_prt0"]
        )

        ConfigUpdate (
            insMachineInfo,
            filename = ini_config_variables_dict["config_file"]     # from config.ini file
        )

        self.main_loop (
            dtt, 
            insLogger,
            insTimers,
            insMachineInfo,
            util_prt = ini_general_variables_dict["util_prt"],
            util_prt0 = ini_general_variables_dict["util_prt0"]
        )
#--------------------------------------------------------------------------------------------------------------
    def main_loop (
            self, 
            dtt, 
            insLogger,
            insTimers,
            insMachineInfo,
            util_prt = False,
            util_prt0 = False
        ):

        dtts = dtt.strftime (self.gen_datim_format)

        client_id = insMachineInfo.get_client_id ()  
        mac_address = insMachineInfo.get_mac_address ()
        hostname, ip_address = insMachineInfo.get_ip_address ()
        unique_client_id = insMachineInfo.get_unique_client_id ()
        own_serial_number = insMachineInfo.get_own_serial_number ()
        
        if util_prt:
            print (f"Current dtts: {dtts}")
            print (f"client_id: {client_id}")
            print (f"hostname: {hostname}")
            print (f"ip_address: {ip_address}")
            print (f"mac_address: {mac_address}")
            print (f"own_serial_number: {own_serial_number}")
            print (f"unique_client_id: {unique_client_id}")
            print (f"program_version: {insMachineInfo.program_version}")
            print (f"program_updated: {insMachineInfo.program_updated}")

        # Always log key startup info
        insLogger.log_info(msg=f"[Main--main_loop] System Startup: client_id: {client_id}")
        insLogger.log_info(msg=f"[Main--main_loop] System Startup: hostname: {hostname}")
        insLogger.log_info(msg=f"[Main--main_loop] System Startup: ip_address: {ip_address}")
        insLogger.log_info(msg=f"[Main--main_loop] System Startup: mac_address: {mac_address}")
        insLogger.log_info(msg=f"[Main--main_loop] System Startup: own_serial_number: {own_serial_number}")
        insLogger.log_info(msg=f"[Main--main_loop] System Startup: unique_client_id: {unique_client_id}")
        insLogger.log_info(msg=f"[Main--main_loop] System Startup: program_version: {insMachineInfo.program_version}")
        insLogger.log_info(msg=f"[Main--main_loop] System Startup: program_updated: {insMachineInfo.program_updated}")

        try:
            while True:
                dtt = datetime.now()
                insTimers.service_timer_ticks(dtt)
                self.insMQTToutQueue.service_out_queue(dtt)
                sleep(0.0001)

        except KeyboardInterrupt:
            # Graceful shutdown message
            insLogger.log_info("Keyboard Ctrl-C detected. Disconnecting MQTT...")

            self.insMQTTbroker.client.disconnect()
            self.insMQTTbroker.client.loop_stop()

        # Final exit message with timestamp
        dtts = dtt.strftime(self.gen_datim_format)
        insLogger.log_info(
            msg = f"[Main--main_loop] Keyboard Program Stopped at: {dtts}"
        )

#--------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":

    Main (
        dtt = datetime.now ()
    )

#--------------------------------------------------------------------------------------------------------------
