# updated: 2025-05-06 15:32:24
# created: 2025-04-17 17:10:09
# filename: config_parser.py
#--------------------------------------------------------------------------------------------------------------
import os
from json import load
from queue import Queue
from datetime import datetime
from configparser import ConfigParser
from credentials import JSON_DataReaderCredential

#--------------------------------------------------------------------------------------------------------------
class Config_Init(object):

    # Class-level file paths
    CONFIG_PATH = "config/"
    INI_FILENAME = "config/config.ini"
    JSON_FILENAME = "config/config_ini.json"       # Defaults inside this file.

    def __init__(self) -> None:
        # Initiate the log_message_queue
        self.log_message_queue = Queue()
        self.config = ConfigParser()
        self.add_one_message_to_log_message_queue (
            message = self.check_and_create_necessary_folders()
        )
        self.config.read(self.INI_FILENAME)
        self.add_one_message_to_log_message_queue (
            message = f"{self.INI_FILENAME} successfully loaded!"
        )
        self.add_one_message_to_log_message_queue (
            message = self.compare_and_sync()
        )
        self.add_one_message_to_log_message_queue (
            message = self.config_final_prep()
        )
        self.add_one_message_to_log_message_queue (
            message = f"class Config_Init, initiated successfully!"
        )
        self.check_log_message_queue_and_send_log ()

#--------------------------------------------------------------------------------------------------------------
    def write_to_log_file (self, message: str, log_level = "[INFO]", message_type = "[CONFIG PARSER]"):
        """Writes a message to the log file with timestamp, log level, and message type."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]  # Get milliseconds
        formatted_message = f"{timestamp} {log_level}: {message_type} {message}"
        
        with open(self.systemlog_file, 'a') as log_file:
            log_file.write(formatted_message + '\n')

    def add_one_message_to_log_message_queue(self, message, log_level = "[INFO]", message_type = "[CONFIG PARSER]"):
        """Adds a message with a message_type to the log message queue."""
        self.log_message_queue.put((message, log_level, message_type))

    def check_log_message_queue_and_send_log(self):
        """Checks the message queue and sends each message to the log file."""
        if not self.log_message_queue.empty():
            while not self.log_message_queue.empty():
                message, log_level, message_type = self.log_message_queue.get()
                self.write_to_log_file(
                    message, 
                    log_level = log_level,
                    message_type = message_type
                )  # Write to log file
            return "Messages sent to log file."
        else:
            return "No messages in the queue to send."
        
#--------------------------------------------------------------------------------------------------------------      
    def check_and_create_necessary_folders (self):
        # Check and create the necessary folders
        if not os.path.exists(self.CONFIG_PATH):
            os.makedirs(self.CONFIG_PATH)  # Create data folder if it doesn't exist
            message = f"{self.CONFIG_PATH} folder created!"
            reason = "initail creation required"
            self.create_new_config_ini (reason = message)
            return f"{message}, {reason}"
        else:
            return f"{self.CONFIG_PATH} folder in place!"
        
#--------------------------------------------------------------------------------------------------------------
    def get_json_master_default_config (self):
        # Load the JSON master configuration
        with open (self.JSON_FILENAME, 'r') as json_file:
            json_data = load(json_file)
        json_section_count = len(json_data)
        json_key_total = sum(len(section_dict) for section_dict in json_data.values() 
                            if isinstance(section_dict, dict))
        return json_data, json_section_count, json_key_total
    
#--------------------------------------------------------------------------------------------------------------
    def create_new_config_ini (self, reason: str):
        message = "Create a new config.ini file because "
        message += reason
        if os.path.exists(self.INI_FILENAME):
            os.remove(self.INI_FILENAME)
        # Build a new config from JSON data
        new_config = ConfigParser ()
        json_data, json_section_count, json_key_total = self.get_json_master_default_config()
        for section, values in json_data.items():
            # Ensure all values are strings, as configparser requires string values
            new_config[section] = {str(k): str(v) for k, v in values.items()}
        # Write the new INI file to disk
        with open(self.INI_FILENAME, 'w') as ini_file:
            new_config.write(ini_file)
        # Update counts to reflect the new INI state
        self.ini_section_count = json_section_count
        self.ini_key_total = json_key_total
        self.config.read(self.INI_FILENAME)
        return message
#--------------------------------------------------------------------------------------------------------------
    def compare_and_sync (self):
        json_data, json_section_count, json_key_total = self.get_json_master_default_config ()
        ini_section_count = len(self.config.sections())
        ini_key_total = 0
        ini_keys = {}
        # Count keys in each section (ignoring any default values)
        for section in self.config.sections():
            # config._sections[section] holds the keys actually in that section
            if section in self.config._sections:
                section_keys = list(self.config._sections[section].keys())
                ini_keys[section] = section_keys
                ini_key_total += len(section_keys)
        # Compare section counts
        if ini_section_count != json_section_count:
            message = f"Section count mismatch: INI has {ini_section_count} sections, JSON has {json_section_count} sections."
        else:
            message = ""

        # Compare keys in each section and detect mismatches
        for section, json_section_keys in json_data.items ():
            if section not in ini_keys:
                message += f"Missing section in INI file: {section}. "
                break  # Exit after finding the first mismatch

            ini_section_keys = ini_keys.get(section, [])
            json_section_keys = list(json_section_keys.keys())

            # Correct comparison of missing and extra keys
            missing_keys = [key for key in json_section_keys if key not in ini_section_keys]
            extra_keys = [key for key in ini_section_keys if key not in json_section_keys]

            if missing_keys:
                message += f"Missing keys in section [{section}]: {', '.join(missing_keys)}. "
            if extra_keys:
                message += f"Extra keys in section [{section}]: {', '.join(extra_keys)}. "

        if message:
            message += " Recreating the INI file."
            # Remove the old INI file
            if os.path.exists(self.INI_FILENAME):
                os.remove(self.INI_FILENAME)
            # Build a new config from JSON data
            reason = self.create_new_config_ini (reason = message)
            message += reason
        else:
            # No mismatch – no changes made to INI
            message = "INI-file compares with JSON-file."
        # Return the tuple of counts and status message
        return message, (ini_section_count, json_section_count), (ini_key_total, json_key_total)
    
#--------------------------------------------------------------------------------------------------------------
    def config_final_prep (self):
        # Add any final preparations here, if needed
        self.logger_enable = self.config.getboolean('boolean', 'logger_enable')
        data_path = self.config.get('files', 'data_path')
        config_path = self.config.get('files', 'config_path')
        systemlog_file = self.config.get('files', 'systemlog_file')
        self.systemlog_file = f"{data_path}{systemlog_file}"                # This is needed because the config_parser program needs to add to the systemlog_file
        print (f"Location of systemlog_file: {self.systemlog_file}")
        credentials_file = self.config.get('files', 'credentials_file')
        self.credentials_file = f"{config_path}{credentials_file}"
        return f"Configuration files initialized: {self.logger_enable}, {self.systemlog_file} and {self.credentials_file} files!"
    
#--------------------------------------------------------------------------------------------------------------    
    def get_variables_dict (self, category=None):
        insJSONcredentials = JSON_DataReaderCredential(self.credentials_file)

        if category.lower() == "general":
            variables_dict = {
                "util_prt": self.config.getboolean('boolean', 'util_prt'),
                "util_prt0": self.config.getboolean('boolean', 'util_prt0'),
                "paho_enable": self.config.getboolean('boolean', 'paho_enable'),
                "logger_enable": self.config.getboolean('boolean', 'logger_enable'),
                "csv_logging_enable": self.config.getboolean('boolean', 'csv_logging_enable')
            }

        elif category.lower() == "config":
            data_path = self.config.get('files', 'data_path')
            config_path = self.config.get('files', 'config_path')
            variables_dict = {
                "data_path": data_path,
                "logger_level": self.config.get('files', 'logger_level'),
                "users_file": f"{config_path}{self.config.get('files', 'users_file')}",
                "config_file": f"{config_path}{self.config.get('files', 'config_file')}",
                "cameras_file": f"{config_path}{self.config.get('files', 'cameras_file')}",
                "servers_file": f"{config_path}{self.config.get('files', 'servers_file')}",
                "errorlog_file": f"{data_path}{self.config.get('files', 'errorlog_file')}",
                "systemlog_file": f"{data_path}{self.config.get('files', 'systemlog_file')}",
                "credentials_file": f"{config_path}{self.config.get('files', 'credentials_file')}",
                "csv_transaction_file": f"{data_path}{self.config.get('files', 'csv_transaction_file')}",
                "csv_temperature_file": f"{data_path}{self.config.get('files', 'csv_temperature_file')}",
                "user_collections_path": f"{config_path}{self.config.get('files', 'user_collections_path')}"
            }

        elif category.lower() == "mongo":
            variables_dict = {
                "mongo_hostname": insJSONcredentials.credentials.get('mongodb_settings', {}).get('hostname'),
                "mongo_port": insJSONcredentials.credentials.get('mongodb_settings', {}).get('port'),
                "mongo_db_name": insJSONcredentials.credentials.get('mongodb_settings', {}).get('db_name'),
                "mongo_db_username": insJSONcredentials.credentials.get('mongodb_settings', {}).get('db_username'),
                "mongo_db_password": insJSONcredentials.credentials.get('mongodb_settings', {}).get('db_password'),
                "mongo_auth_db": insJSONcredentials.credentials.get('mongodb_settings', {}).get('auth_db'),
                "mongo_admin_username": insJSONcredentials.credentials.get('mongodb_settings', {}).get('admin_username'),
                "mongo_admin_password": insJSONcredentials.credentials.get('mongodb_settings', {}).get('admin_password')
            }

        else:
            self.write_to_log_file (
                message = f"Invalid category request: {category}, use 'general', 'config' or 'mongo'!",
                log_level = "[ERROR]"
            )
            variables_dict = {}

        return variables_dict
    
#--------------------------------------------------------------------------------------------------------------
# Ensure this section runs only if this script is executed directly
if __name__ == "__main__":

    # Example Code for config_parser.py
    insConfigInit = Config_Init()
    

    def print_variables_dict (category = None):
        print (f"<<< ini_variables_dict category >>>: {category}")
        variables_dict = insConfigInit.get_variables_dict (category)
        for key, val in variables_dict.items ():
            print (f"{key}: {val}")

    print_variables_dict (category = "general")
    print_variables_dict (category = "config")
    print_variables_dict (category = "mongo")
    
#--------------------------------------------------------------------------------------------------------------