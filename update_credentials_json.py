# updated: 2025-05-12 15:17:19
# created: 2025-05-12 15:05:25
# filename: update_credentials_json.py
#--------------------------------------------------------------------------------------------------------------
import json
import argparse
from pathlib import Path
from logger import CustomLogger

#--------------------------------------------------------------------------------------------------------------
class CredentialUpdater:
    def __init__(self, insLogger, data_path="config"):
        self.insLogger = insLogger
        self.data_path = Path(data_path)
        self.credentials_file = self.data_path / ".credentials.json"

#--------------------------------------------------------------------------------------------------------------
    def load_json(self, file_path):
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            return data
        except Exception as e:
            self.insLogger.log_error(msg=f"[CredentialUpdater--load_json] Failed to load {file_path}: {e}")
            return None

#--------------------------------------------------------------------------------------------------------------
    def save_json(self, file_path, data):
        try:
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
            self.insLogger.log_info(msg=f"[CredentialUpdater--save_json] Updated: {file_path}")
        except Exception as e:
            self.insLogger.log_error(msg=f"[CredentialUpdater--save_json] Failed to write {file_path}: {e}")

#--------------------------------------------------------------------------------------------------------------
    def update_server_credentials(self, server_name, update_file_id):
        self.insLogger.log_info(msg=f"[CredentialUpdater--update_server_credentials] Updating '{server_name}' with ID '{update_file_id}'")

        source_file = self.data_path / f"{update_file_id}.json"
        credentials_data = self.load_json(self.credentials_file)
        update_data = self.load_json(source_file)

        if credentials_data is None or update_data is None:
            self.insLogger.log_error(msg="[CredentialUpdater--update_server_credentials] Aborting: Failed to load data.")
            return

        try:
            if "roc_api_settings" not in credentials_data:
                credentials_data["roc_api_settings"] = {}

            credentials_data["roc_api_settings"][server_name] = update_data
            self.save_json(self.credentials_file, credentials_data)
        except Exception as e:
            self.insLogger.log_error(msg=f"[CredentialUpdater--update_server_credentials] Exception: {e}")

#--------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update .credentials.json with a specific API key config")
    parser.add_argument("--server", required=True, help="Server name key in .credentials.json (e.g., server_rocdemo1)")
    parser.add_argument("--id", required=True, help="ID of the source JSON file (e.g., 682099ebb304310014b0ff78)")
    args = parser.parse_args()

    custom_logger = CustomLogger(
        backup_count=5,
        max_bytes=10485760,
        logfile="config/roc_rest_api.log",
        logger_level="INFO",
        util_prt=False,
        util_prt0=True
    )
    custom_logger.exclude_debug_entries(r".*Lock \\d+ acquired on queue\\.lock")
    custom_logger.log_info(msg=f"[CredentialUpdater--main] Starting update for server '{args.server}' from ID '{args.id}'")

    insUpdater = CredentialUpdater(insLogger=custom_logger, data_path="config")
    insUpdater.update_server_credentials(server_name=args.server, update_file_id=args.id)
#--------------------------------------------------------------------------------------------------------------
"""
python3 update_credentials_json.py --server server_rocdemo1 --id 682099ebb304310014b0ff78
python3 update_credentials_json.py --server server_rocdemo2 --id 682117247422c100145398d0
"""