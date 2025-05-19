# updated: 2025-04-27 19:16:58
# created: 2025-04-27 16:52:00
# filename: csv_writer.py
#--------------------------------------------------------------------------------------------------------------
import os
import csv
from typing import Union
from dataclasses import dataclass, fields
#--------------------------------------------------------------------------------------------------------------
@dataclass
class TransactionHeader:
    _iD: str
    dateTime: str
    transactionType: str
    idNumber: str
    UniqueId: str
    fullName: str
    serialSource: str

@dataclass
class TemperatureHeader:
    _iD: str
    dateTime: str
    serialSource: str
    ipAddress: str
    hostName: str
    sensorName: str
    tempValue: float
    
#--------------------------------------------------------------------------------------------------------------
class CSVwriter(object):
    def __init__ (
            self, 
            insLogger, 
            header: Union[str, None] = None, 
            filename: str = "default_log.csv"
        ) -> None:

        self.insLogger = insLogger
        self.filename = filename

        # Initialize header based on type (TransactionHeader or TemperatureHeader)
        if header == "transactionHeader":
            self.header = [field.name for field in fields(TransactionHeader)]
        elif header == "temperatureHeader":
            self.header = [field.name for field in fields(TemperatureHeader)]
        else:
            self.header = []

        insLogger.log_info(msg=f"[CSVwriter--__init__] csv_transaction_file: {filename}")

        # Write the header only if the file doesn't exist or is empty
        if not os.path.isfile(self.filename) or os.stat(self.filename).st_size == 0:
            with open(self.filename, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(self.header)

#--------------------------------------------------------------
    def write_transaction_to_csv_file(self, transaction: TransactionHeader):
        self.insLogger.log_debug(
            msg=f"[CSVwriter--write_transaction_to_csv_file] Data Entry: {transaction}"
        )

        try:
            with open(self.filename, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(transaction.__dict__.values())  # Extract values from dataclass

            self.insLogger.log_info(
                msg=f"[CSVwriter--write_transaction_to_csv_file] Data has been appended to '{self.filename}'."
            )

        except Exception as e:
            self.insLogger.log_error(
                msg=f"[CSVwriter--write_transaction_to_csv_file ERROR] Failed to write to '{self.filename}': {e}"
            )

#--------------------------------------------------------------------------------------------------------------
    def write_temperature_to_csv_file(self, temperature: TemperatureHeader):
        self.insLogger.log_debug(
            msg=f"[CSVwriter--write_temperature_to_csv_file] Data Entry: {temperature}"
        )

        try:
            with open(self.filename, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(temperature.__dict__.values())  # Extract values from dataclass

            self.insLogger.log_info(
                msg=f"[CSVwriter--write_temperature_to_csv_file] Data has been appended to '{self.filename}'."
            )

        except Exception as e:
            self.insLogger.log_error(
                msg=f"[CSVwriter--write_temperature_to_csv_file ERROR] Failed to write to '{self.filename}': {e}"
            )

#--------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"CSVwriter Test Program!")

    from config_parser import Config_Init
    insConfigInit = Config_Init()
    ini_general_variables_dict = insConfigInit.get_variables_dict (category="general")  # from config.ini file
    ini_config_variables_dict = insConfigInit.get_variables_dict (category="config")    # from config.ini file
    
    from logger import CustomLogger
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

    # Example usage with dataclasses
    insCSVtransaction = CSVwriter(
        insLogger,
        header="transactionHeader",
        filename = ini_config_variables_dict["csv_transaction_file"]   # derived from config.ini file (config_parser.py)
    )

    # Creating an instance of TransactionHeader
    transaction_data = TransactionHeader(
        _iD='933c8e4aa6ed4cbc8fc6b090',
        dateTime='2024/12/18 10:19:40',
        transactionType='RFE_Access',
        idNumber='777',
        UniqueId='666',
        fullName='Push Button',
        serialSource='251096701259753'
    )
    insCSVtransaction.write_transaction_to_csv_file(transaction_data)

    # Example usage with TemperatureHeader
    insCSVtemperature = CSVwriter(
        insLogger, 
        header="temperatureHeader",
        filename = ini_config_variables_dict["csv_temperature_file"]   # derived from config.ini file (config_parser.py)
        
    )
    
    # Creating an instance of TemperatureHeader
    temperature_data = TemperatureHeader(
        _iD='933c8e4aa6ed4cbc8fc6b090',
        dateTime='2024/12/18 10:19:40',
        serialSource='251096701259753',
        hostName='testHostname',
        ipAddress='192.168.1.10',
        sensorName='Sensor_1',
        tempValue=23.5
    )
    insCSVtemperature.write_temperature_to_csv_file(temperature_data)
