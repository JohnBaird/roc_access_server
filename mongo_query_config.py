# updated: 2025-05-08 16:13:38
# created: 2025-05-05 03:36:05
# filename: mongo_query_config.py
#--------------------------------------------------------------------------------------------------------------
from pymongo import MongoClient, errors
from bson.objectid import ObjectId
from argparse import ArgumentParser

#--------------------------------------------------------------------------------------------------------------
class MongoQueryConfig:
    def __init__(
        self,
        insLogger=None,
        ini_mongo_variables_dict=None
    ):
        self.insLogger = insLogger

        try:
            host = ini_mongo_variables_dict["mongo_hostname"]
            port = ini_mongo_variables_dict["mongo_port"]
            database = ini_mongo_variables_dict["mongo_db_name"]

            self.client = MongoClient(
                host = host,
                port = int(port),
                username = ini_mongo_variables_dict["mongo_db_username"],
                password = ini_mongo_variables_dict["mongo_db_password"],
                authSource = ini_mongo_variables_dict["mongo_auth_db"]
            )

            self.client.admin.command("ping")
            self.db = self.client[database]
            self.insLogger.log_info(msg=f"[MongoQueryConfig--__init__] Connected to MongoDB at {host}:{port} -> DB: {database}")

        except Exception as e:
            self.insLogger.log_error(msg=f"[MongoQueryConfig--__init__ ERROR] Connection failed: {e}")
            raise

#--------------------------------------------------------------------------------------------------------------
    def query_config_general_settings(self):
        try:
            cfg_doc = self.db["config"].find_one({})
            if not cfg_doc:
                self.insLogger.log_error(msg="[MongoQueryConfig--query_config_general_settings] No config document found")
                return None

            gs = cfg_doc.get("general_settings")
            if not gs:
                self.insLogger.log_error(msg="[MongoQueryConfig--query_config_general_settings] 'general_settings' missing")
                return None

            self.insLogger.log_info(msg=f"[MongoQueryConfig--query_config_general_settings] general_settings fetched: {', '.join(gs.keys())}")
            return gs

        except Exception as e:
            self.insLogger.log_error(msg=f"[MongoQueryConfig--query_config_general_settings ERROR] {e}")
            return None

#--------------------------------------------------------------------------------------------------------------
    def query_config_access_settings(self):
        try:
            cfg_doc = self.db["config"].find_one({})
            if not cfg_doc:
                self.insLogger.log_error(msg="[MongoQueryConfig--query_config_access_settings] No config document found")
                return None

            acc = cfg_doc.get("access_settings")
            if not acc:
                self.insLogger.log_error(msg="[MongoQueryConfig--query_config_access_settings] 'access_settings' block missing")
                return None

            for k, v in acc.items():
                setattr(self, k, v)

            self.insLogger.log_info(msg="[MongoQueryConfig--query_config_access_settings] access_settings loaded – keys: " + ", ".join(acc.keys()))
            return acc

        except Exception as e:
            self.insLogger.log_error(msg=f"[MongoQueryConfig--query_config_access_settings ERROR] {e}")
            return None

#--------------------------------------------------------------------------------------------------------------
    def query_config_mqtt_settings(self):
        try:
            cfg_doc = self.db["config"].find_one({})
            if not cfg_doc:
                self.insLogger.log_error(msg="[MongoQueryConfig--query_config_mqtt_settings] No config document found")
                return None

            mqtt = cfg_doc.get("mqtt_settings")
            if not mqtt:
                self.insLogger.log_error(msg="[MongoQueryConfig--query_config_mqtt_settings] 'mqtt_settings' block missing")
                return None

            for key, value in mqtt.items():
                setattr(self, key, value)

            self.insLogger.log_info(msg="[MongoQueryConfig--query_config_mqtt_settings] mqtt_settings loaded – keys: " + ", ".join(mqtt.keys()))
            return mqtt

        except Exception as e:
            self.insLogger.log_error(msg=f"[MongoQueryConfig--query_config_mqtt_settings ERROR] {e}")
            return None

#--------------------------------------------------------------------------------------------------------------
    def query_get_reader_serial_numbers_dict(self, status: bool):
        try:
            cameras_collection = self.db["cameras"]
            result = {}

            for doc in cameras_collection.find({"enable": status}):
                reader_name = doc.get("readerName")
                reader_serial = doc.get("readerSerial")
                if reader_name and reader_serial:
                    result[reader_name] = reader_serial

            self.insLogger.log_info(
                msg=f"[MongoQueryConfig--query_get_reader_serial_numbers_dict] Reader Serial Dictionary (enable={status}):"
            )
            for name, serial in result.items():
                self.insLogger.log_info(
                    msg=f"[MongoQueryConfig--query_get_reader_serial_numbers_dict] {name}: {serial}"
                )

            return result

        except Exception as e:
            self.insLogger.log_error(
                msg=f"[MongoQueryConfig--query_get_reader_serial_numbers_dict ERROR] Failed to query reader serial numbers (enable={status}): {e}"
            )
            return {}
#--------------------------------------------------------------------------------------------------------------
    def query_get_servers_serial_numbers_dict(self, status: bool):
        servers_collection = self.db["servers"]
        result = {}

        try:
            query_filter = {"type": "roc", "enable": status}

            for doc in servers_collection.find(query_filter):
                server_name = doc.get("serverName")
                serial_number = doc.get("serialNumber")
                if server_name and serial_number:
                    result[server_name] = serial_number

            self.insLogger.log_info(
                msg=f"[MongoQueryConfig--query_get_servers_serial_numbers_dict] ROC Server Serial Dictionary (enable={status}):"
            )
            for name, serial in result.items():
                self.insLogger.log_info(
                    msg=f"[MongoQueryConfig--query_get_servers_serial_numbers_dict] {name}: {serial}"
                )

            return result

        except Exception as e:
            self.insLogger.log_error(
                msg=f"[MongoQueryConfig--query_get_servers_serial_numbers_dict ERROR] Failed to query ROC server serial numbers (enable={status}): {e}"
            )
            return {}
#--------------------------------------------------------------------------------------------------------------
    def query_get_qr_code_servers_serial_numbers_dict(self, status: bool):
        servers_collection = self.db["servers"]
        result = {}

        try:
            query_filter = {"type": "qr", "enable": status}

            for doc in servers_collection.find(query_filter):
                server_name = doc.get("serverName")
                serial_number = doc.get("serialNumber")
                if server_name and serial_number:
                    result[server_name] = serial_number

            self.insLogger.log_info(
                msg=f"[MongoQueryConfig--query_get_qr_code_servers_serial_numbers_dict] QR Code Server Serial Dictionary (enable={status}):"
            )
            for name, serial in result.items():
                self.insLogger.log_info(
                    msg=f"[MongoQueryConfig--query_get_qr_code_servers_serial_numbers_dict] {name}: {serial}"
                )

            return result

        except Exception as e:
            self.insLogger.log_error(
                msg=f"[MongoQueryConfig--query_get_qr_code_servers_serial_numbers_dict ERROR] Failed to query QR Code server serial numbers (enable={status}): {e}"
            )
            return {}

#--------------------------------------------------------------------------------------------------------------
    def query_config_mqtt_subscribe_test_clients(self, status: bool):
        try:
            cfg_doc = self.db["config"].find_one({})
            if not cfg_doc:
                self.insLogger.log_error(
                    msg=f"[MongoQueryConfig--query_config_mqtt_subscribe_test_clients] No config document found"
                )
                return {}

            mqtt_clients = cfg_doc.get("mqtt_subscribe_test_clients")
            if not mqtt_clients:
                self.insLogger.log_info(
                    msg=f"[MongoQueryConfig--query_config_mqtt_subscribe_test_clients] Block 'mqtt_subscribe_test_clients' missing"
                )
                return {}

            if mqtt_clients.get("enable", False) != status:
                self.insLogger.log_info(
                    msg=f"[MongoQueryConfig--query_config_mqtt_subscribe_test_clients] Block present but enable != {status}"
                )
                return {}

            result = {k: v for k, v in mqtt_clients.items() if k != "enable"}

            self.insLogger.log_info(
                msg=f"[MongoQueryConfig--query_config_mqtt_subscribe_test_clients] Client list (enable={status}): {result}"
            )
            return result

        except Exception as e:
            self.insLogger.log_error(
                msg=f"[MongoQueryConfig--query_config_mqtt_subscribe_test_clients ERROR] {e}"
            )
            return {}

#--------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    from logger import CustomLogger
    from config_parser import Config_Init

    parser = ArgumentParser(description="Simple MongoDB Query Tool for Config")
    parser.add_argument("--general_settings", action="store_true", help="Fetch general_settings block")
    parser.add_argument("--access_settings", action="store_true", help="Fetch access_settings block")
    parser.add_argument("--mqtt_settings", action="store_true", help="Fetch mqtt_settings block")
    parser.add_argument("--reader_serial_numbers", action="store_true", help="Query reader serial numbers from cameras")
    parser.add_argument("--servers_serial_numbers", action="store_true", help="Query ROC server serial numbers")
    parser.add_argument("--qr_code_servers_serial_numbers", action="store_true", help="Query QR Code server serial numbers")
    parser.add_argument("--mqtt_subscribe_test_clients", action="store_true", help="Fetch mqtt_subscribe_test_clients block if enabled")
    args = parser.parse_args()

    custom_logger = CustomLogger(
        backup_count=5,
        max_bytes=10485760,
        logfile="config/config_query_log.log",
        logger_level="INFO",
        util_prt=False,
        util_prt0=True
    )
    custom_logger.exclude_debug_entries(r".*Lock \\d+ acquired on queue\\.lock")
    custom_logger.log_info(msg=f"[MongoQueryConfig] Starting Mongo query tool")

    insConfigInit = Config_Init()
    mq = MongoQueryConfig(
        insLogger=custom_logger,
        ini_mongo_variables_dict=insConfigInit.get_variables_dict(category="mongo")
    )

    if args.general_settings:
        print(mq.query_config_general_settings())
    elif args.access_settings:
        print(mq.query_config_access_settings())
    elif args.mqtt_settings:
        print(mq.query_config_mqtt_settings())
    elif args.reader_serial_numbers:
        print(mq.query_get_reader_serial_numbers_dict(status=True))
    elif args.servers_serial_numbers:
        print(mq.query_get_servers_serial_numbers_dict(status=True))
    elif args.qr_code_servers_serial_numbers:
        print(mq.query_get_qr_code_servers_serial_numbers_dict(status=True))
    elif args.mqtt_subscribe_test_clients:
        print(mq.query_config_mqtt_subscribe_test_clients(status=True))
    else:
        print("No query option provided. Use --general_settings, --access_settings, or --mqtt_settings.")

#--------------------------------------------------------------------------------------------------------------
""" 
# Query general_settings
python3 mongo_query_config.py --general_settings

# Query access_settings
python3 mongo_query_config.py --access_settings

# Query mqtt_settings
python3 mongo_query_config.py --mqtt_settings 

# Query reader_serial_numbers
python3 mongo_query_config.py --reader_serial_numbers

# Query ROC servers_serial_numbers
python3 mongo_query_config.py --servers_serial_numbers

# Query qr_code_servers_serial_numbers
python3 mongo_query_config.py --qr_code_servers_serial_numbers

# Query mqtt_subscribe_test_clients
python3 mongo_query_config.py --mqtt_subscribe_test_clients

"""
#--------------------------------------------------------------------------------------------------------------