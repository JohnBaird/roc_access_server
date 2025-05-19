# updated: 2025-04-23 15:29:55
# created: 2025-04-07 19:57:50
# filename: servers.py
#--------------------------------------------------------------------------------------------------------------
from json import load, JSONDecodeError

class Servers:
    def __init__ (
            self, 
            insLogger, 
            filename = "config/servers.json"
        ) -> None:
        
        self.insLogger = insLogger
        self.data = self.load_servers(filename)
        self.report_on_serialNumber_duplicates()

    def load_servers(self, filename):
        try:
            with open(filename, 'r') as f:
                data = load(f)
                if not isinstance(data, list):
                    self.insLogger.log_error(
                        msg=f"[Servers--load_servers ERROR] Expected a list in {filename}, but got {type(data).__name__}"
                    )
                    return []
                self.insLogger.log_info(
                    msg=f"[Servers--load_servers] Successfully loaded configuration from {filename}"
                )
                return data

        except FileNotFoundError:
            self.insLogger.log_error(
                msg=f"[Servers--load_servers ERROR] The file {filename} was not found."
            )
        except JSONDecodeError as e:
            self.insLogger.log_error(
                msg=f"[Servers--load_servers ERROR] JSON decode error in {filename}: {e}"
            )
        except Exception as e:
            self.insLogger.log_error(
                msg=f"[Servers--load_servers ERROR] Unexpected error reading {filename}: {e}"
            )

        return []


    def check_duplicate_serial_numbers(self):
        serial_map = {}
        duplicates = {}

        for srv in self.data:
            serial = srv.get("serialNumber")
            name = srv.get("serverName", "Unnamed")
            if serial in serial_map:
                serial_map[serial].append(name)
                duplicates[serial] = serial_map[serial]
            else:
                serial_map[serial] = [name]

        return duplicates

    def report_on_serialNumber_duplicates(self):
        try:
            duplicates = self.check_duplicate_serial_numbers()

            if duplicates:
                self.insLogger.log_error("[Servers--report_on_serialNumber_duplicates] Duplicate serialNumbers found:")
                for serial, names in duplicates.items():
                    self.insLogger.log_error(
                        msg=f"[Servers--report_on_serialNumber_duplicates] cameraId: {serial} is used by: {', '.join(names)}"
                    )
            else:
                self.insLogger.log_info(
                    msg="[Servers--report_on_serialNumber_duplicates] Validation successful: servers.json contains only unique serialNumbers."
                )

        except Exception as e:
            self.insLogger.log_error(
                msg=f"[Servers--report_on_serialNumber_duplicates ERROR] Exception occurred: {str(e)}"
            )

    def query_get_servers_serial_numbers_list(self):
        serials = set()
        for srv in self.data:
            if srv.get("type") == "roc" and srv.get("enable", False):
                serial = srv.get("serialNumber")
                if serial:
                    serials.add(serial)
        return list(serials)

    def query_get_qr_code_servers_serial_numbers_list(self):
        serials = set()
        for srv in self.data:
            if srv.get("type") == "qr" and srv.get("enable", False):
                serial = srv.get("serialNumber")
                if serial:
                    serials.add(serial)
        return list(serials)

    def query_get_servers_serial_numbers_dict(self):
        serial_dict = {}
        for srv in self.data:
            if srv.get("type") == "roc" and srv.get("enable", False):
                name = srv.get("serverName")
                serial = srv.get("serialNumber")
                if name and serial:
                    serial_dict[name] = serial
        return serial_dict

    def query_get_qr_code_servers_serial_numbers_dict(self):
        serial_dict = {}
        for srv in self.data:
            if srv.get("type") == "qr" and srv.get("enable", False):
                name = srv.get("serverName")
                serial = srv.get("serialNumber")
                if name and serial:
                    serial_dict[name] = serial
        return serial_dict

    def query_hostname_by_serialNumber(self, serialNumber: str):
        for srv in self.data:
            if srv.get("serialNumber") == serialNumber:
                if srv.get("enable", False):
                    hostname = srv.get("hostname")
                    self.insLogger.log_info(f"[SERVERS] Hostname for serialNumber {serialNumber}: {hostname}")
                    return hostname
                else:
                    self.insLogger.log_info(f"[SERVERS] Server with serialNumber {serialNumber} is disabled.")
                    return None
        self.insLogger.log_error(f"[SERVERS] No server found with serialNumber {serialNumber}.")
        return None

#--------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":

    from config import JSON_Config
    insJSONconfig = JSON_Config (
            program_version = f"Testing users.py",
            program_updated = f"Testing users.py",
            file_path_config = "config/config.json",
            file_path_credentials = "config/.credentials.json"
        )
    from logger import CustomLogger
    custom_logger = CustomLogger(
        insJSONconfig,
        max_bytes=10485760,
        backup_count=5
    )
    custom_logger.exclude_debug_entries(r".*Lock \d+ acquired on queue\.lock")
    insLogger = custom_logger  # ✅ correct assignment
    insLogger.info("users test_log started!")    # This log entry will be logged

    insServers = Servers(
        insLogger = insLogger
    )

    server_serial_numbers_list = insServers.query_get_servers_serial_numbers_list()

    qr_code_servers_serial_numbers_list = insServers.query_get_qr_code_servers_serial_numbers_list()

    hostname = insServers.query_hostname_by_serialNumber("83544762879823")
#--------------------------------------------------------------------------------------------------------------