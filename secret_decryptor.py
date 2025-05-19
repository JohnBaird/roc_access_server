# updated: 2025-05-12 16:37:34
# created: 2025-05-12 15:38:12
# filename: secret_decryptor.py
#--------------------------------------------------------------------------------------------------------------
import json
from pathlib import Path
from secret_encryptor import SecretEncryptor
from logger import CustomLogger

class CredentialDecryptor:
    def __init__(self, insLogger, credentials_file_path="config/.credentials.json"):
        self.insLogger = insLogger
        self.credentials_path = Path(credentials_file_path)
        self.data = self._load_credentials()
        self.encryptor = None

    def _load_credentials(self):
        try:
            with open(self.credentials_path, "r") as f:
                data = json.load(f)
            self.insLogger.log_info(msg=f"[CredentialDecryptor--_load_credentials] Loaded {self.credentials_path}")
            return data
        except Exception as e:
            self.insLogger.log_error(msg=f"[CredentialDecryptor--_load_credentials] Failed to load credentials: {e}")
            return None

    def setup_encryptor(self):
        try:
            password = self.data["mongodb_settings"]["admin_password"]
            self.encryptor = SecretEncryptor(password)
            self.insLogger.log_info(msg="[CredentialDecryptor--setup_encryptor] Encryptor initialized")
        except Exception as e:
            self.insLogger.log_error(msg=f"[CredentialDecryptor--setup_encryptor] Failed to set up encryptor: {e}")

    def get_decrypted_secretkey(self, server_name):
        if not self.data or not self.encryptor:
            self.insLogger.log_error(msg="[CredentialDecryptor--get_decrypted_secretkey] Missing config or encryptor")
            return None

        api_settings = self.data.get("roc_api_settings", {})
        config = api_settings.get(server_name)
        if config and config.get("enabled") and config.get("secretkey"):
            try:
                decrypted = self.encryptor.decrypt(config["secretkey"])
                self.insLogger.log_info(
                    msg=f"[CredentialDecryptor--get_decrypted_secretkey] Decrypted secretkey for {server_name}"
                )
                return decrypted
            except Exception as e:
                self.insLogger.log_error(
                    msg=f"[CredentialDecryptor--get_decrypted_secretkey] Failed to decrypt {server_name}: {e}"
                )
                return None
        else:
            self.insLogger.log_warning(
                msg=f"[CredentialDecryptor--get_decrypted_secretkey] Server {server_name} not enabled or missing secretkey"
            )
            return None

    def encrypt_and_replace_sha256_keys(self):
        if not self.data or not self.encryptor:
            self.insLogger.log_error(msg="[CredentialDecryptor--encrypt_and_replace_sha256_keys] Missing config or encryptor")
            return

        updated = False
        for server_name, config in self.data.get("roc_api_settings", {}).items():
            secret = config.get("secretkey")
            if secret and len(secret) == 64 and all(c in "0123456789abcdef" for c in secret):
                try:
                    decrypted_guess = self._guess_original_secret_from_known_map(secret)
                    if decrypted_guess:
                        encrypted = self.encryptor.encrypt(decrypted_guess)
                        config["secretkey"] = encrypted
                        updated = True
                        self.insLogger.log_info(msg=f"[CredentialDecryptor--encrypt_and_replace_sha256_keys] Replaced SHA-256 with encrypted value for {server_name}")
                except Exception as e:
                    self.insLogger.log_error(msg=f"[CredentialDecryptor--encrypt_and_replace_sha256_keys] Error processing {server_name}: {e}")

        if updated:
            try:
                with open(self.credentials_path, "w") as f:
                    json.dump(self.data, f, indent=2)
                self.insLogger.log_info(msg=f"[CredentialDecryptor--encrypt_and_replace_sha256_keys] Saved updated file to {self.credentials_path}")
            except Exception as e:
                self.insLogger.log_error(msg=f"[CredentialDecryptor--encrypt_and_replace_sha256_keys] Failed to write updated credentials: {e}")

    def _guess_original_secret_from_known_map(self, sha256_hash):
        # This is a placeholder. In practice you'd use a secure lookup or pass in a known map.
        known = {
            # "d73c52c56208f026622dd60707df9f5d419c28df84e486e540f30c72bb51b6d3": "1rph1wPszzpnBwLZwi8ldN3SCIoytHWbioKQbLKpyfb62AfweHfTfDcw47GCEbh91C"
            "1a5507d9c9b1f6708df74a8c964d5f40a0a5b81afecb96408eb933524d51ff92": "RVfhY9GoWuSsNUmigX3903A0uRL00B7vi7w00rKqXSZ3OEPIrjmHXE65yWMylLJxJ"
        }
        return known.get(sha256_hash)

if __name__ == "__main__":
    custom_logger = CustomLogger(
        backup_count=5,
        max_bytes=10485760,
        logfile="config/roc_rest_api.log",
        logger_level="INFO",
        util_prt=False,
        util_prt0=True
    )
    custom_logger.exclude_debug_entries(r".*Lock \\d+ acquired on queue\\.lock")

    insDecryptor = CredentialDecryptor(insLogger=custom_logger)
    insDecryptor.setup_encryptor()
    insDecryptor.encrypt_and_replace_sha256_keys()
    decrypted_key = insDecryptor.get_decrypted_secretkey("server_rocdemo2")
    print("Decrypted secretkey:", decrypted_key)

#--------------------------------------------------------------------------------------------------------------