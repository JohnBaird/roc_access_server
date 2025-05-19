# updated: 2025-04-23 15:49:34
# created: 2024-09-26 15:19:41
# filename: config.py
#--------------------------------------------------------------------------------------------------------------
from json import load, JSONDecodeError
#--------------------------------------------------------------------------------------------------------------
class Config (object):
    def __init__ (
            self, 
            insLogger = None, 
            filename = "config/config.json"
        ) -> None:
        
        self.insLogger = insLogger
        # self.data = self.load_config(filename)
#--------------------------------------------------------------------------------------------------------------
    def load_config(self, filename):
        try:
            with open(filename, 'r') as f:
                data = load(f)
                if not isinstance(data, dict):
                    self.insLogger.log_error(
                        msg=f"[Config--load_config ERROR] Expected a dict in {filename}, but got {type(data).__name__}"
                    )
                    return {}
                self.insLogger.log_info(
                    msg=f"[Config--load_config] Successfully loaded configuration from {filename}"
                )
                return data

        except FileNotFoundError:
            self.insLogger.log_error(
                msg=f"[Config--load_config ERROR] File not found: {filename}"
            )
        except JSONDecodeError as e:
            self.insLogger.log_error(
                msg=f"[Config--load_config ERROR] JSON decode error in {filename}: {e}"
            )
        except Exception as e:
            self.insLogger.log_error(
                msg=f"[Config--load_config ERROR] Unexpected error reading {filename}: {e}"
            )

        return {}

#--------------------------------------------------------------------------------------------------------------

#--------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":

    from config import JSON_Config
    insJSONconfig = JSON_Config (
            program_version = f"Testing config.py",
            program_updated = f"Testing config.py",
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
    insLogger.info("config test_log started!")    # This log entry will be logged

    insConfig = Config (
        insLogger = insLogger
    )

    # Query by faceId for user_name (full name)
#--------------------------------------------------------------------------------------------------------------