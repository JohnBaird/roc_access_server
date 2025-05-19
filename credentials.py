# updated: 2025-04-13 15:54:41
# created: 2024-06-15 12:45:00
# filename: credentials.py
# access .credentials.json
#--------------------------------------------------------------------------------------------------------------
import os
from json import load
#--------------------------------------------------------------------------------------------------------------
class JSON_DataReaderCredential ():
    def __init__ (
            self,
            file_path_credentials
        ) -> None:

        self.credentials = self.load_and_update_config (file_path_credentials)
#--------------------------------------------------------------------------------------------------------------
    def load_and_update_config (self, file_path):
        with open(file_path, 'r') as file:
            data = load (file)
        return data
#--------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    # Example usage
    from config import JSON_Config
    insJSONconfig = JSON_Config(
        program_version="Testing users.py",
        program_updated="Testing users.py",
        file_path_config="config/config.json",
        file_path_credentials="config/.credentials.json"
    )

    from logger import CustomLogger
    custom_logger = CustomLogger(
        insJSONconfig,
        max_bytes=10485760,
        backup_count=5
    )
    custom_logger.exclude_debug_entries(r".*Lock \d+ acquired on queue\.lock")
    insLogger = custom_logger  # ✅ Correct assignment
    insLogger.log_info("[STARTUP] users test_log started!")

    import os
    file_path = os.environ.get('FILE_PATH_CREDENTIALS')  # add, del or edit env profiles: ~$ nano .bash_profile
    file_path = os.path.expanduser(file_path)

    from credentials import JSON_DataReaderCredential
    insJSONcredentials = JSON_DataReaderCredential(
        insJSONconfig,
        file_path
    )

    insLogger.log_info("[TEST] Program starting examples from new_credentials.py")

    mqtt_user_name = insJSONcredentials.credentials.get('mqtt_settings', {}).get('mqtt_username', 'Default: mqtt_user')
    insLogger.log_info(f"[CREDENTIALS] MQTT Username: {mqtt_user_name}")

    user_name = insJSONcredentials.credentials.get('user_info', {}).get('user_name', 'Default: username')
    insLogger.log_info(f"[CREDENTIALS] User Name: {user_name}")

#--------------------------------------------------------------------------------------------------------------
