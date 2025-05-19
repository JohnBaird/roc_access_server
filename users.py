# updated: 2025-04-23 15:25:02
# created: 2025-04-01 16:06:54
# filename: users.py
#--------------------------------------------------------------------------------------------------------------
from json import load, JSONDecodeError

class Users:
    def __init__(
            self, 
            insLogger, 
            filename="config/users.json"
        ) -> None:
        
        self.insLogger = insLogger
        self.data = self.load_users(filename)

        self.report_on_faceId_duplicates()
        self.report_on_employeeId_duplicates()
        self.report_on_cardNumber_duplicates()
        self.report_on_pin_number_duplicates()

    def load_users(self, filename):
        try:
            with open(filename, 'r') as f:
                data = load(f)
                if not isinstance(data, list):
                    self.insLogger.log_error(
                        msg=f"[Users--load_users ERROR] Expected a list in {filename}, but got {type(data).__name__}"
                    )
                    return []
                self.insLogger.log_info(
                    msg=f"[Users--load_users] Successfully loaded configuration from {filename}"
                )
                return data

        except FileNotFoundError:
            self.insLogger.log_error(
                msg=f"[Users--load_users ERROR] The file {filename} was not found."
            )
        except JSONDecodeError as e:
            self.insLogger.log_error(
                msg=f"[Users--load_users ERROR] JSON decode error in {filename}: {e}"
            )
        except Exception as e:
            self.insLogger.log_error(
                msg=f"[Users--load_users ERROR] Unexpected error reading {filename}: {e}"
            )

        return []

    
    def query_user_by_card_number(self, cardNumber: str):
        try:
            for user in self.data:
                if cardNumber in user.get("cardNumbers", []):
                    fullName = f"{user.get('firstName', '')} {user.get('lastName', '')}".strip()
                    self.insLogger.log_info(f"[USERS] Match by cardNumber: {cardNumber} → {fullName}")
                    return fullName
            self.insLogger.log_error(f"[USERS] No user found with cardNumber: {cardNumber}")
        except Exception as e:
            self.insLogger.log_error(f"[USERS ERROR] query_user_by_card_number failed: {e}")
        return None

    def query_user_by_pinNumber(self, pinNumber: str):
        try:
            for user in self.data:
                if user.get("pinNumber") == pinNumber:
                    fullName = f"{user.get('firstName', '')} {user.get('lastName', '')}".strip()
                    self.insLogger.log_info(f"[USERS] Match by pinNumber: {pinNumber} → {fullName}")
                    return fullName
            self.insLogger.log_error(f"[USERS] No user found with pinNumber: {pinNumber}")
        except Exception as e:
            self.insLogger.log_error(f"[USERS ERROR] query_user_by_pinNumber failed: {e}")
        return None

    def query_cards_by_faceId(self, faceId: str):
        try:
            for user in self.data:
                if user.get("faceId") == faceId:
                    cardNumbers = user.get("cardNumbers", [])
                    self.insLogger.log_info(f"[USERS] Cards for faceId {faceId}: {cardNumbers}")
                    return cardNumbers
            self.insLogger.log_error(f"[USERS] No cards found for faceId: {faceId}")
        except Exception as e:
            self.insLogger.log_error(f"[USERS ERROR] query_cards_by_faceId failed: {e}")
        return None

    def query_pin_by_card_number(self, card_number: str):
        try:
            for user in self.data:
                if card_number in user.get("cardNumbers", []):
                    pin = user.get("pinNumber")
                    self.insLogger.log_info(f"[USERS] PIN for card {card_number}: {pin}")
                    return pin
            self.insLogger.log_error(f"[USERS] No PIN found for cardNumber: {card_number}")
        except Exception as e:
            self.insLogger.log_error(f"[USERS ERROR] query_pin_by_card_number failed: {e}")
        return None
    
    def query_user_by_faceId(self, faceId: str):
        try:
            for user in self.data:
                if user.get("faceId") == faceId:
                    fullName = f"{user.get('firstName', '')} {user.get('lastName', '')}"
                    self.insLogger.log_info(f"[USERS] Match by faceId: {faceId} → {fullName}")
                    return fullName
        except Exception as e:
            self.insLogger.log_error(f"[USERS] Error in query_user_by_faceId: {e}")
        return None
    
    def query_pin_by_faceId(self, faceId: str):
        try:
            for user in self.data:
                if user.get("faceId") == faceId:
                    pin = user.get("pinNumber")
                    self.insLogger.log_info(f"[USERS] PIN found for faceId {faceId}: {pin}")
                    return pin
        except Exception as e:
            self.insLogger.log_error(f"[USERS] Error in query_pin_by_faceId: {e}")
        return None

    def check_duplicate_watchlisted_face_ids(self):
        face_id_map = {}
        duplicates = {}

        for user in self.data:
            face_id = user.get("faceId")
            full_name = f"{user.get('firstName', '')} {user.get('lastName', '')}"
            if face_id in face_id_map:
                face_id_map[face_id].append(full_name)
                duplicates[face_id] = face_id_map[face_id]
            else:
                face_id_map[face_id] = [full_name]

        return duplicates
    
    def check_duplicate_employeeId(self):
        employee_map = {}
        duplicates = {}

        for user in self.data:
            empl_id = user.get("employeeId")
            full_name = f"{user.get('firstName', '')} {user.get('lastName', '')}"
            if empl_id in employee_map:
                employee_map[empl_id].append(full_name)
                duplicates[empl_id] = employee_map[empl_id]
            else:
                employee_map[empl_id] = [full_name]

        return duplicates

    def check_duplicate_card_numbers(self):
        card_map = {}
        duplicates = {}

        for user in self.data:
            full_name = f"{user.get('firstName', '')} {user.get('lastName', '')}"
            for card in user.get("cardNumbers", []):
                if card in card_map:
                    card_map[card].append(full_name)
                    duplicates[card] = card_map[card]
                else:
                    card_map[card] = [full_name]

        return duplicates

    def check_duplicate_pin_numbers(self):
        pin_map = {}
        duplicates = {}

        for user in self.data:
            pin = user.get("pinNumber")
            full_name = f"{user.get('firstName', '')} {user.get('lastName', '')}"
            if pin in pin_map:
                pin_map[pin].append(full_name)
                duplicates[pin] = pin_map[pin]
            else:
                pin_map[pin] = [full_name]

        return duplicates
#---------------------------------------------------------------------------------------------------------------
    def report_on_faceId_duplicates(self):
        try:
            duplicates = self.check_duplicate_watchlisted_face_ids()

            if duplicates:
                self.insLogger.log_error(msg="[Users--report_on_faceId_duplicates] Duplicate faceIds found:")
                for face_id, users in duplicates.items():
                    self.insLogger.log_error(
                        msg=f"[Users--report_on_faceId_duplicates] Face ID {face_id} is used by: {', '.join(users)}"
                    )
            else:
                self.insLogger.log_info(
                    msg="[Users--report_on_faceId_duplicates] Validation successful: users.json contains only unique faceIds."
                )

        except Exception as e:
            self.insLogger.log_error(
                msg=f"[Users--report_on_faceId_duplicates ERROR] Exception occurred during faceId validation: {str(e)}"
            )

#---------------------------------------------------------------------------------------------------------------
    def report_on_employeeId_duplicates(self):
        try:
            duplicates = self.check_duplicate_employeeId()

            if duplicates:
                self.insLogger.log_error(msg="[Users--report_on_employeeId_duplicates] Duplicate employeeIds found:")
                for empl_id, users in duplicates.items():
                    self.insLogger.log_error(
                        msg=f"[Users--report_on_employeeId_duplicates] Employee ID {empl_id} is used by: {', '.join(users)}"
                    )
            else:
                self.insLogger.log_info(
                    msg="[Users--report_on_employeeId_duplicates] Validation successful: users.json contains only unique employeeIds."
                )

        except Exception as e:
            self.insLogger.log_error(
                msg=f"[Users--report_on_employeeId_duplicates ERROR] Exception occurred while checking employeeId duplicates: {e}"
            )


# --------------------------------------------------------------------------------------------------------------
    def report_on_cardNumber_duplicates(self):
        try:
            duplicates = self.check_duplicate_card_numbers()

            if duplicates:
                self.insLogger.log_error(msg="[Users--report_on_cardNumber_duplicates] Duplicate cardNumbers found:")
                for card, users in duplicates.items():
                    self.insLogger.log_error(
                        msg=f"[Users--report_on_cardNumber_duplicates] Card {card} is used by: {', '.join(users)}"
                    )
            else:
                self.insLogger.log_info(
                    msg="[Users--report_on_cardNumber_duplicates] Validation successful: users.json contains only unique cardNumbers."
                )

        except Exception as e:
            self.insLogger.log_error(
                msg=f"[Users--report_on_cardNumber_duplicates ERROR] Exception occurred while checking cardNumber duplicates: {e}"
            )

# --------------------------------------------------------------------------------------------------------------
    def report_on_pin_number_duplicates(self):
        try:
            duplicates = self.check_duplicate_pin_numbers()

            if duplicates:
                self.insLogger.log_error(
                    msg="[Users--report_on_pin_number_duplicates] Duplicate pinNumbers found:"
                )
                for pin, users in duplicates.items():
                    self.insLogger.log_error(
                        msg=f"[Users--report_on_pin_number_duplicates] PIN {pin} is used by: {', '.join(users)}"
                    )
            else:
                self.insLogger.log_info(
                    msg="[Users--report_on_pin_number_duplicates] Validation successful: users.json contains only unique pin_numbers."
                )

        except Exception as e:
            self.insLogger.log_error(
                msg=f"[Users--report_on_pin_number_duplicates ERROR] Exception occurred while checking pinNumber duplicates: {e}"
            )

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

    insUsers = Users (
        insLogger = insLogger
    )

    # Query by faceId for user_name (full name)
    user_name = insUsers.query_user_by_faceId(
        faceId = "c76139e5bbedb049ddb23b89b79e4d3147771707"
    )

    pin = insUsers.query_pin_by_faceId(
        faceId="c76139e5bbedb049ddb23b89b79e4d3147771707"
    )
#--------------------------------------------------------------------------------------------------------------