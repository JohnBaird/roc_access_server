# updated: 2025-05-16 12:48:08
# created: 2025-05-11 13:19:24
# filename: roc_api_keys.py
#--------------------------------------------------------------------------------------------------------------
from json import load
from pathlib import Path

#--------------------------------------------------------------------------------------------------------------
class ROC_Api:
    def __init__(self, insLogger, rocServer="rocdemo1", file_path="config/.credentials.json"):
        self.insLogger = insLogger
        self.file_path = file_path
        self.rocServer = rocServer
        self.serverIp = None
        self.api_key = None
        self.api_secret = None
        self.user_access_id = None
        self._load_keys()

#--------------------------------------------------------------------------------------------------------------
    def _load_keys(self):
        try:
            file = Path(self.file_path)
            if not file.exists():
                self.insLogger.log_error(msg=f"[ROC_Api--_load_keys] Credential file not found: {self.file_path}")
                return

            with file.open("r") as f:
                data = load(f)

            api_entries = data.get("roc_api_settings", [])
            if not isinstance(api_entries, list):
                self.insLogger.log_error(msg="[ROC_Api--_load_keys] 'roc_api_settings' is not a list")
                return

            match = None
            for entry in api_entries:
                if entry.get("rocServer") == self.rocServer:
                    match = entry
                    break

            if match:
                if not match.get("enabled", False):
                    self.insLogger.log_warning(
                        msg=f"[ROC_Api--_load_keys] API key for {self.rocServer} is disabled"
                    )
                    return

                self.rocServer = match.get("rocServer")
                self.serverIp = match.get("serverIp")
                self.api_key = match.get("idkey")
                self.api_secret = match.get("secretkey")
                self.user_access_id = match.get("_userAccessId")

                self.insLogger.log_info(
                    msg=(f"[ROC_Api--_load_keys] Loaded credentials for {self.rocServer} | "
                        f"UserAccessId: {self.user_access_id}")
                )
            else:
                self.insLogger.log_error(
                    msg=f"[ROC_Api--_load_keys] No credentials found for server: {self.rocServer}"
                )

        except Exception as e:
            self.insLogger.log_error(
                msg=f"[ROC_Api--_load_keys ERROR] Exception while loading credentials: {str(e)}"
            )

#--------------------------------------------------------------------------------------------------------------
    def get_credentials(self):
        """Return rocServer, IP, API key, secret, and user access ID as a tuple."""
        if self.api_key and self.api_secret and self.user_access_id:
            return self.rocServer, self.serverIp, self.api_key, self.api_secret, self.user_access_id
        else:
            self.insLogger.log_warning(
                msg=f"[ROC_Api--get_credentials] Credentials not fully loaded for {self.rocServer}"
            )
            return None, None, None, None, None

#--------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    from logger import CustomLogger

    custom_logger = CustomLogger(
        backup_count=5,
        max_bytes=10485760,
        logfile="logs/roc_rest_api.log",
        logger_level="INFO",
        util_prt=False,
        util_prt0=False
    )
    custom_logger.exclude_debug_entries(r".*Lock \d+ acquired on queue\.lock")

    # List of rocServers to load from .credentials.json
    rocServers = ["rocdemo1", "rocdemo2"]

    for rocServer in rocServers:
        insApi = ROC_Api(insLogger=custom_logger, rocServer=rocServer)

        rocServer, serverIp, api_key, api_secret, user_access_id = insApi.get_credentials()

        print(f"\n[{rocServer}] rocServer: {rocServer}")
        print(f"[{rocServer}] serverIp: {serverIp}")
        print(f"[{rocServer}] api_key: {api_key}")
        print(f"[{rocServer}] api_secret: {api_secret}")
        print(f"[{rocServer}] user_access_id: {user_access_id}")

#--------------------------------------------------------------------------------------------------------------









# from json import load
# from pathlib import Path
# #--------------------------------------------------------------------------------------------------------------
# class ROC_Api:
#     def __init__(self, insLogger, server_name="server_121", file_path="config/.roc_api_keys.json"):
#         self.insLogger = insLogger
#         self.server_name = server_name
#         self.file_path = file_path
#         self.rocServer = None
#         self.ip_address = None
#         self.api_key = None
#         self.api_secret = None
#         self.user_access_id = None
#         self._load_keys()

# #--------------------------------------------------------------------------------------------------------------
#     def _load_keys(self):
#         try:
#             file = Path(self.file_path)
#             if not file.exists():
#                 self.insLogger.log_error(msg=f"[ROC_Api--_load_keys] API key file not found: {self.file_path}")
#                 return

#             with file.open("r") as f:
#                 data = load(f)

#             api_section = data.get("roc_watch_api_keys", {})
#             server_key = f"api_keys-{self.server_name}"
#             server_data = api_section.get(server_key)

#             if server_data:
#                 if not server_data.get("enabled", False):
#                     self.insLogger.log_warning(
#                         msg=f"[ROC_Api--_load_keys] API key for {self.server_name} is disabled"
#                     )
#                     return

#                 self.rocServer = server_data.get("rocServer")
#                 self.ip_address = server_data.get("ip_address")
#                 self.api_key = server_data.get("idkey")
#                 self.api_secret = server_data.get("secretkey")
#                 self.user_access_id = server_data.get("_userAccessId")

#                 self.insLogger.log_info(
#                     msg=(
#                         f"[ROC_Api--_load_keys] Loaded credentials for {self.server_name} | "
#                         f"UserAccessId: {self.user_access_id}"
#                     )
#                 )
#             else:
#                 self.insLogger.log_error(
#                     msg=f"[ROC_Api--_load_keys] No credentials found for server: {self.server_name}"
#                 )
#         except Exception as e:
#             self.insLogger.log_error(
#                 msg=f"[ROC_Api--_load_keys ERROR] Exception while loading API keys: {str(e)}"
#             )

# #--------------------------------------------------------------------------------------------------------------
#     def get_credentials(self):
#         """Return API key, secret, and user access ID as a tuple."""
#         if self.api_key and self.api_secret and self.user_access_id:
#             return self.rocServer, self.ip_address, self.api_key, self.api_secret, self.user_access_id
#         else:
#             self.insLogger.log_warning(
#                 msg=f"[ROC_Api--get_credentials] Credentials not fully loaded for {self.server_name}"
#             )
#             return None, None, None, None, None

# #--------------------------------------------------------------------------------------------------------------
#     def refresh_keys(self):
#         """Reload the keys from file."""
#         self.insLogger.log_info(
#             msg=f"[ROC_Api--refresh_keys] Refreshing API credentials for {self.server_name}"
#         )
#         self._load_keys()

# #--------------------------------------------------------------------------------------------------------------
# # === Example Usage ===
# if __name__ == "__main__":
#     from logger import CustomLogger

#     custom_logger = CustomLogger(
#         backup_count = 5,
#         max_bytes = 10485760,
#         logfile = "config/roc_rest_api.log",
#         logger_level = "INFO",
#         util_prt = False,
#         util_prt0 = False
#     )
#     custom_logger.exclude_debug_entries(r".*Lock \d+ acquired on queue\.lock")
#     custom_logger.debug("Lock 548462840704 acquired on queue.lock")
#     custom_logger.log_info(f"[ROC API] ")   # insert tthe function as hand

#     # Create both API instances
#     insApiRoc_121 = ROC_Api(
#         insLogger = custom_logger,  # ✅ correct assignment
#         server_name="server_121"
#     )
#     insApiRoc_133 = ROC_Api(
#         insLogger = custom_logger,  # ✅ correct assignment
#         server_name="server_133"
#     )

#     # Output for verification (optional)
#     print(f"[121] rocServer: {insApiRoc_121.rocServer}")
#     print(f"[121] ip_address: {insApiRoc_121.ip_address}")
#     print(f"[121] api_key: {insApiRoc_121.api_key}")
#     print(f"[121] api_secret: {insApiRoc_121.api_secret}")
#     print(f"[121] user_access_id: {insApiRoc_121.user_access_id}")

#     print(f"[133] rocServer: {insApiRoc_133.rocServer}")
#     print(f"[133] ip_address: {insApiRoc_133.ip_address}")
#     print(f"[133] api_key: {insApiRoc_133.api_key}")
#     print(f"[133] api_secret: {insApiRoc_133.api_secret}")
#     print(f"[133] user_access_id: {insApiRoc_121.user_access_id}")

#     insApiRoc_121.refresh_keys()
#     rocServer, ip_address, api_key, api_secret, user_access_id = insApiRoc_121.get_credentials()
#     print (f"ROC_121-credentials:")
#     print (f"rocServer={rocServer}")
#     print (f"ip_address={ip_address}")
#     print (f"api_key={api_key}")
#     print (f"api_secret={api_secret}")
#     print (f"user_access_id={user_access_id}")

#     insApiRoc_133.refresh_keys()
#     rocServer, ip_address, api_key, api_secret, user_access_id = insApiRoc_133.get_credentials()
#     print (f"ROC_133-credentials:")
#     print (f"rocServer={rocServer}")
#     print (f"ip_address={ip_address}")
#     print (f"api_key={api_key}")
#     print (f"api_secret={api_secret}")
#     print (f"user_access_id={user_access_id}")

# #--------------------------------------------------------------------------------------------------------------