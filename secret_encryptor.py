# updated: 2025-05-12 16:01:38
# created: 2025-05-12 00:33:01
# filename: secret_encryptor.py
#--------------------------------------------------------------------------------------------------------------
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from base64 import urlsafe_b64encode, urlsafe_b64decode
from hashlib import sha256


class SecretEncryptor:
    def __init__(self, encryption_key: str):
        self.aes_key = sha256(encryption_key.encode()).digest()

    def _pad(self, s: str) -> str:
        pad_len = 16 - (len(s) % 16)
        return s + chr(pad_len) * pad_len

    def _unpad(self, s: str) -> str:
        pad_len = ord(s[-1])
        return s[:-pad_len]

    def encrypt(self, secret: str) -> str:
        iv = get_random_bytes(16)
        cipher = AES.new(self.aes_key, AES.MODE_CBC, iv)
        padded_secret = self._pad(secret)
        encrypted = cipher.encrypt(padded_secret.encode())
        return urlsafe_b64encode(iv + encrypted).decode()

    def decrypt(self, encrypted_token: str) -> str:
        raw = urlsafe_b64decode(encrypted_token)
        iv = raw[:16]
        ciphertext = raw[16:]
        cipher = AES.new(self.aes_key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(ciphertext).decode()
        return self._unpad(decrypted)


# Test it
if __name__ == "__main__":
    secret = "RVfhY9GoWuSsNUmigX3903A0uRL00B7vi7w00rKqXSZ3OEPIrjmHXE65yWMylLJxJ"
    password = "rf123"  # can be anything you choose

    encryptor = SecretEncryptor(password)

    encrypted = encryptor.encrypt(secret)
    print("Encrypted:", encrypted)

    decrypted = encryptor.decrypt(encrypted)
    print("Decrypted:", decrypted)

#--------------------------------------------------------------------------------------------------------------
"""
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from base64 import urlsafe_b64encode, urlsafe_b64decode
from hashlib import sha256

#--------------------------------------------------------------------------------------------------------------
class xSecretEncryptor:
    def __init__(self, encryption_key: str):
        # Initialize the encryptor with a user-supplied encryption key.
        # The key is hashed with SHA-256 to derive a secure 32-byte AES key.
        self.aes_key = sha256(encryption_key.encode()).digest()

#--------------------------------------------------------------------------------------------------------------
    def _pad(self, s: str) -> str:
        pad_len = 16 - (len(s) % 16)
        return s + chr(pad_len) * pad_len

    def _unpad(self, s: str) -> str:
        pad_len = ord(s[-1])
        return s[:-pad_len]

    def encrypt(self, secret: str) -> str:
        # Encrypts the given secret string using AES-256-CBC.
        # Returns a URL-safe base64 encoded string (includes IV).
        iv = get_random_bytes(16)
        cipher = AES.new(self.aes_key, AES.MODE_CBC, iv)
        padded_secret = self._pad(secret)
        encrypted = cipher.encrypt(padded_secret.encode())
        token = urlsafe_b64encode(iv + encrypted).decode()
        return token

    def decrypt(self, encrypted_token: str) -> str:
        # Decrypts a base64 encoded token (created by this class).
        # Returns the original plaintext secret.
        raw = urlsafe_b64decode(encrypted_token)
        iv = raw[:16]
        ciphertext = raw[16:]
        cipher = AES.new(self.aes_key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(ciphertext).decode()
        return self._unpad(decrypted)

#--------------------------------------------------------------------------------------------------------------
if __name__ == "__xmain__":
    secret = "RVfhY9GoWuSsNUmigX3903A0uRL00B7vi7w00rKqXSZ3OEPIrjmHXE65yWMylLJxJ"
    encryption_passphrase = "rf123"

    insEncryptor = SecretEncryptor(encryption_passphrase)

    encrypted = insEncryptor.encrypt(secret)
    print("Encrypted:", encrypted)

    decrypted = insEncryptor.decrypt(encrypted)
    print("Decrypted:", decrypted)

#--------------------------------------------------------------------------------------------------------------
"""