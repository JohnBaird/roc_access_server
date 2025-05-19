# updated: 2025-04-26 17:15:54
# created: 2024-12-23 13:47:14
# filename: secret_key_handler.py
#-----------------------------------------------------------------------------------------------------------------
import pyotp
from datetime import datetime
from json import load, loads, JSONDecodeError
#-----------------------------------------------------------------------------------------------------------------
class SecretKeys (object):
    def __init__ (
            self,
            logger,
            insJSONconfig
        ) -> None:

        self.logger = logger
        self.insJSONconfig = insJSONconfig

        self.load_secret_keys_file (filename = insJSONconfig.secret_keys_filename)
#-----------------------------------------------------------------------------------------------------------------   
    def load_secret_keys_file (self, filename=None):
        try:
            # Use the provided filename or the default from configuration
            filename = filename or self.insJSONconfig.secret_keys_filename
            
            # Attempt to open and load the JSON file
            with open(filename, 'r') as json_file:
                self.current_keys = load(json_file)
        except FileNotFoundError:
            error_message = f"Secret keys file not found: {filename}"
            if getattr(self.insJSONconfig, "logger_enable", False):
                self.logger.error(error_message, exc_info=True)
            raise
        except JSONDecodeError:
            error_message = f"Invalid JSON format in file: {filename}"
            if getattr(self.insJSONconfig, "logger_enable", False):
                self.logger.error(error_message, exc_info=True)
            raise
        except Exception as e:
            error_message = f"Unexpected error while loading secret keys from file: {filename}"
            if getattr(self.insJSONconfig, "logger_enable", False):
                self.logger.error(error_message, exc_info=True)
            raise
#-----------------------------------------------------------------------------------------------------------------
    def pin_creator (self, emp_id):
        self.load_secret_keys_file (filename = self.insJSONconfig.secret_keys_filename)
        qr_code_format = lambda card_num, TOTP: '{"q":{"c":"' + card_num + '","p":"' + TOTP + '"}}'

        if emp_id not in self.current_keys.keys():
            print(f"Not registered: {emp_id}")
            quit()
        URI = pyotp.utils.build_uri(secret = self.current_keys[emp_id]["secret_key"], name = emp_id, issuer = "ROC", digits = 6)
        x = pyotp.parse_uri(URI)
        print (f"Secret: {x.secret}") if self.insJSONconfig.util_prt else None
        print (f"Issuer: {x.issuer}") if self.insJSONconfig.util_prt0 else None
        print (f"Digits: {x.digits}") if self.insJSONconfig.util_prt0 else None
        print (f"User:   {x.name}") if self.insJSONconfig.util_prt0 else None
        # previous = x.now()
        qr_codes = qr_code_format(x.name, x.now())
        print (f"qr_codes: {qr_codes}") if self.insJSONconfig.util_prt else None
        return qr_codes
#-----------------------------------------------------------------------------------------------------------------
    def otp_creator (self, card_number, timestamp=None):
        try:
            # Load secret keys file
            self.load_secret_keys_file(filename=self.insJSONconfig.secret_keys_filename)
            
            # Check if card_number exists in current_keys
            if card_number not in self.current_keys:
                error_message = f"Card number {card_number} is not registered."
                if getattr(self.insJSONconfig, "logger_enable", False):
                    self.logger.error(error_message)
                return None  # Gracefully handle the missing card number
            
            # Generate URI for the card
            URI = pyotp.utils.build_uri(
                secret = self.current_keys[card_number]["secret_key"],
                name = card_number,
                issuer = "ROC",
                digits = 6
            )

            # Generate OTP
            timestamp = int(datetime.now().timestamp()) if not timestamp else timestamp
            otp = pyotp.TOTP(self.current_keys[card_number]["secret_key"]).at (timestamp)
            # otp = pyotp.TOTP(self.current_keys[card_number]["secret_key"]).now()
            print(f"card_number: {card_number}, OTP: {otp}") if self.insJSONconfig.util_prt0 else None
            return otp
            

        except Exception as e:
            # Handle any unexpected errors
            error_message = f"An error occurred while creating the OTP for card number {card_number}: {e}"
            if getattr(self.insJSONconfig, "logger_enable", False):
                self.logger.error (error_message, exc_info = True)
            return None
#-----------------------------------------------------------------------------------------------------------------
    def is_valid_qr_code_dict (self, qr_code):
        try:
            # Parse the input string as JSON
            parsed = loads(qr_code)
            # Validate structure and keys
            return isinstance(parsed, dict) and parsed.keys() == {"q"} and parsed["q"].keys() == {"c", "p"}
        except JSONDecodeError as e:
            log_message = f"is_valid_qr_code_dict: {e}, {qr_code}"
            if self.insJSONconfig.logger_enable:
                self.logger.error(log_message, exc_info=True)
            return False
#-----------------------------------------------------------------------------------------------------------------
    def validate_otp (
            self, 
            card_number, 
            one_time_pin, 
            dtt = None
        ):
        
        try:
            # Load the secret keys file
            self.load_secret_keys_file(filename=self.insJSONconfig.secret_keys_filename)

            # Get the current time if not provided
            dtt = dtt if dtt is not None else datetime.now ()
            
            # Retrieve the secret key for the card number
            secret_key = self.current_keys.get(card_number, {}).get('secret_key')
            if not secret_key:
                error_message = f"Card number {card_number} is not registered or has no secret key."
                if getattr(self.insJSONconfig, "logger_enable", False):
                    self.logger.error(error_message)
                return False  # Validation fails due to missing card
            
            # Validate the OTP
            totp = pyotp.TOTP(secret_key)
            validate = totp.verify (one_time_pin, for_time=dtt)
            return validate

        except Exception as e:
            # Handle unexpected errors
            error_message = f"An error occurred while validating the OTP for card number {card_number}: {e}"
            if getattr (self.insJSONconfig, "logger_enable", False):
                self.logger.error(error_message, exc_info=True)
            return False
#-----------------------------------------------------------------------------------------------------------------
    def validate_qr_code (self, qr_dict, dtt=None):
        self.load_secret_keys_file (filename = self.insJSONconfig.secret_keys_filename)

        validate = False
        dtt = dtt if dtt is not None else datetime.now()
        if self.is_valid_qr_code_dict (qr_code = qr_dict):
            parsed_qr_dict = loads(qr_dict)
            if "q" in parsed_qr_dict and "c" in parsed_qr_dict["q"] and "p" in parsed_qr_dict["q"]:
                card_number = parsed_qr_dict["q"]["c"]
                # pin_number = parsed_qr_dict["q"]["p"]
                # print (f"pin_number: {pin_number}, {type(pin_number)}")
                secret_key = self.current_keys.get(card_number, {}).get('secret_key')
                validate_TOTP = lambda secret_key, TOTP, for_time: pyotp.TOTP(secret_key).verify(TOTP, for_time)
                if validate_TOTP (self.current_keys[parsed_qr_dict["q"]["c"]]["secret_key"], parsed_qr_dict["q"]["p"], dtt):
                    validate = True
        return validate
#-----------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    print (f"Test Program for secret_key_handler.py")
    # Example usage
    from config import JSON_Config
    logger = None
    insJSONconfig = JSON_Config ()
    insSecKey = SecretKeys (logger, insJSONconfig)
    emp_ids = tuple (insSecKey.current_keys.keys())
    for emp_id in emp_ids:

        qr_dict = insSecKey.pin_creator (emp_id) # <----------Create PIN
        if insSecKey.validate_qr_code (qr_dict = qr_dict, dtt = datetime.now()):
            print (f"qr_dict_emp_id: {emp_id}, pin: Validated")
        else:
            print (f"qr_dict_emp_id: {emp_id}, pin: Failed")

        otp = insSecKey.otp_creator (card_number = emp_id) # <----------Create otp
        if insSecKey.validate_otp (card_number = emp_id, one_time_pin = otp):
            print (f"OTP_emp_id: {emp_id}, pin: Validated")
        else:
            print (f"OTP_emp_id: {emp_id}, pin: Failed")
#-----------------------------------------------------------------------------------------------------------------
