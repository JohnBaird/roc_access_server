# updated: 2025-05-06 16:13:20
# created: 2025-05-05 13:45:18
# filename: mongo_query_general.py
#--------------------------------------------------------------------------------------------------------------
from pymongo import MongoClient, errors
from bson.objectid import ObjectId
from argparse import ArgumentParser
#--------------------------------------------------------------------------------------------------------------
class MongoQueryGeneral:
    def __init__(
        self,
        insLogger = None,
        ini_mongo_variables_dict = None
    ):
        self.insLogger = insLogger

        """
        ChatGPT:  Do not remove the following print statements, to be removed after testing is complete.
        print (f"mongo_hostname: {ini_mongo_variables_dict['mongo_hostname']}")
        print (f"mongo_port: {ini_mongo_variables_dict['mongo_port']}")
        print (f"mongo_db_name: {ini_mongo_variables_dict['mongo_db_name']}")
        print (f"mongo_db_username: {ini_mongo_variables_dict['mongo_db_username']}")
        print (f"mongo_db_password: {ini_mongo_variables_dict['mongo_db_password']}")
        print (f"mongo_auth_db: {ini_mongo_variables_dict['mongo_auth_db']}")
        print (f"mongo_admin_username: {ini_mongo_variables_dict['mongo_admin_username']}")
        print (f"mongo_admin_password: {ini_mongo_variables_dict['mongo_admin_password']}")
        """

        try:
            host = ini_mongo_variables_dict["mongo_hostname"]
            port = ini_mongo_variables_dict["mongo_port"]
            database = ini_mongo_variables_dict["mongo_db_name"]

            self.client = MongoClient(
                host = host,
                port = int(port),
                username = ini_mongo_variables_dict["mongo_db_username"],
                password = ini_mongo_variables_dict["mongo_db_password"],
                authSource = ini_mongo_variables_dict["mongo_auth_db"]
            )

            self.client.admin.command("ping")
            self.db = self.client[database]
            self.ensure_indexes()
            self.insLogger.log_info(msg=f"[MongoQueryGeneral--__init__] Connected to MongoDB at {host}:{port} -> DB: {database}")

        except Exception as e:
            self.insLogger.log_error(msg=f"[MongoQueryGeneral--__init__ ERROR] Connection failed: {e}")
            raise

#--------------------------------------------------------------------------------------------------------------
    def ensure_indexes(self):
        try:
            self.db["users"].create_index("faceId", unique=True)
            self.db["users"].create_index("cardNumbers", unique=True)
            self.db["cameras"].create_index("cameraId", unique=True)
            self.db["servers"].create_index("serialNumber", unique=True)
            self.insLogger.log_info(msg="[MongoQueryGeneral--ensure_indexes] Indexes created successfully.")
        except Exception as e:
            self.insLogger.log_error(msg=f"[MongoQueryGeneral--ensure_indexes ERROR] Failed to create indexes: {e}")

#--------------------------------------------------------------------------------------------------------------
    def query_user_by_faceId(self, faceId: str):
        users_collection = self.db["users"]

        try:
            user_doc = users_collection.find_one({
                "faceId": faceId,
                "enable": True
            })

            if user_doc:
                full_name = f"{user_doc.get('firstName', '')} {user_doc.get('lastName', '')}".strip()
                self.insLogger.log_info(
                    msg=f"[MongoQueryGeneral--query_user_by_faceId] User found with faceId: {faceId} | Name: {full_name}"
                )
                return full_name

            self.insLogger.log_error(
                msg=f"[MongoQueryGeneral--query_user_by_faceId NOT FOUND] No enabled user found with faceId: {faceId}"
            )
            return None

        except Exception as e:
            self.insLogger.log_error(
                msg=f"[MongoQueryGeneral--query_user_by_faceId ERROR] Failed to query faceId {faceId}: {e}"
            )
            return None

#--------------------------------------------------------------------------------------------------------------
    def query_user_by_card_number(self, cardNumber: str):
        users_collection = self.db["users"]

        try:
            user_doc = users_collection.find_one({
                "cardNumbers": cardNumber,
                "enable": True
            })

            if user_doc:
                full_name = f"{user_doc.get('firstName', '')} {user_doc.get('lastName', '')}".strip()
                self.insLogger.log_info(
                    msg=f"[MongoQueryGeneral--query_user_by_card_number] User found: {full_name} | cardNumber: {cardNumber}"
                )
                return full_name

            self.insLogger.log_error(
                msg=f"[MongoQueryGeneral--query_user_by_card_number NOT FOUND] No enabled user found with cardNumber: {cardNumber}"
            )
            return None

        except Exception as e:
            self.insLogger.log_error(
                msg=f"[MongoQueryGeneral--query_user_by_card_number ERROR] Failed to query cardNumber {cardNumber}: {e}"
            )
            return None

#--------------------------------------------------------------------------------------------------------------
    def query_access_zone_info_by_card_number(self, cardNumber):
        users_collection = self.db["users"]

        try:
            user_doc = users_collection.find_one({"cardNumbers": cardNumber})

            if user_doc:
                access_info = (
                    {"accessZones": user_doc.get("accessZones", [])},
                    {"current_access_zone": user_doc.get("current_access_zone")},
                    {"free_movement": user_doc.get("free_movement")}
                )
                self.insLogger.log_info(
                    msg=f"[MongoQueryGeneral--query_access_zone_info_by_card_number] Access info for cardNumber {cardNumber}: {access_info}"
                )
                return access_info

            self.insLogger.log_error(
                msg=f"[MongoQueryGeneral--query_access_zone_info_by_card_number NOT FOUND] No user found with cardNumber: {cardNumber}"
            )
            return (
                {"accessZones": []},
                {"current_access_zone": None},
                {"free_movement": None}
            )

        except Exception as e:
            self.insLogger.log_error(
                msg=f"[MongoQueryGeneral--query_access_zone_info_by_card_number ERROR] Failed to query access zone info for cardNumber {cardNumber}: {e}"
            )
            return (
                {"accessZones": []},
                {"current_access_zone": None},
                {"free_movement": None}
            )

#--------------------------------------------------------------------------------------------------------------
    def query_access_zone_info_by_cameraId(self, cameraId):
        cameras_collection = self.db["cameras"]

        try:
            camera_doc = cameras_collection.find_one({"cameraId": cameraId})

            if camera_doc:
                access_info = {
                    "fromZone": camera_doc.get("fromZone"),
                    "toZone": camera_doc.get("toZone"),
                    "updateZone": camera_doc.get("updateZone", False)
                }
                self.insLogger.log_info(
                    msg=f"[MongoQueryGeneral--query_access_zone_info_by_cameraId] Zone info for cameraId {cameraId}: {access_info}"
                )
                return access_info

            self.insLogger.log_error(
                msg=f"[MongoQueryGeneral--query_access_zone_info_by_cameraId NOT FOUND] No camera found with cameraId: {cameraId}"
            )
            return {
                "fromZone": None,
                "toZone": None,
                "updateZone": False
            }

        except Exception as e:
            self.insLogger.log_error(
                msg=f"[MongoQueryGeneral--query_access_zone_info_by_cameraId ERROR] Failed to query camera access zones for cameraId {cameraId}: {e}"
            )
            return {
                "fromZone": None,
                "toZone": None,
                "updateZone": False
            }

#--------------------------------------------------------------------------------------------------------------
    def query_watchlistIds_by_cameraId(self, cameraId: str):
        cameras_collection = self.db["cameras"]

        try:
            camera_doc = cameras_collection.find_one({
                "cameraId": cameraId,
                "enable": True
            })

            if camera_doc:
                watchlist_dict = camera_doc.get("watchlistIds", {})
                watchlist_ids = [(name, wl_id) for name, wl_id in watchlist_dict.items()]
                self.insLogger.log_info(
                    msg=f"[MongoQueryGeneral--query_watchlistIds_by_cameraId] cameraId: {cameraId}, watchlistIds: {watchlist_ids}"
                )
                return watchlist_ids

            else:
                self.insLogger.log_error(
                    msg=f"[MongoQueryGeneral--query_watchlistIds_by_cameraId NOT FOUND] cameraId: {cameraId} — camera not found or disabled"
                )
                return None

        except Exception as e:
            self.insLogger.log_error(
                msg=f"[MongoQueryGeneral--query_watchlistIds_by_cameraId ERROR] cameraId: {cameraId} — query failed: {e}"
            )
            return None

#--------------------------------------------------------------------------------------------------------------
    def query_reader_serial_by_cameraId(self, cameraId: str):
        cameras_collection = self.db["cameras"]

        try:
            camera_doc = cameras_collection.find_one({
                "cameraId": cameraId,
                "enable": True
            })

            if camera_doc:
                reader_serial = camera_doc.get("readerSerial")
                self.insLogger.log_info(
                    msg=f"[MongoQueryGeneral--query_reader_serial_by_cameraId] cameraId: {cameraId}, readerSerial: {reader_serial}"
                )
                return reader_serial
            else:
                self.insLogger.log_error(
                    msg=f"[MongoQueryGeneral--query_reader_serial_by_cameraId NOT FOUND] cameraId: {cameraId} — camera not found or disabled"
                )
                return None

        except Exception as e:
            self.insLogger.log_error(
                msg=f"[MongoQueryGeneral--query_reader_serial_by_cameraId ERROR] cameraId: {cameraId} — query failed: {e}"
            )
            return None

#--------------------------------------------------------------------------------------------------------------
    def query_verifIdent_by_cameraId(self, cameraId: str):
        cameras_collection = self.db["cameras"]

        try:
            # Only return info from enabled cameras
            camera_doc = cameras_collection.find_one({
                "cameraId": cameraId,
                "enable": True
            })

            if camera_doc:
                camera_verif_ident = camera_doc.get("verifIdent", False)
                mode = "Verify" if camera_verif_ident else "Ident"
                self.insLogger.log_info(
                    msg=f"[MongoQueryGeneral--query_verifIdent_by_cameraId] cameraId: {cameraId}, cameraVerifIdent: {camera_verif_ident} ({mode} mode)"
                )
                return camera_verif_ident
            else:
                self.insLogger.log_error(
                    msg=f"[MongoQueryGeneral--query_verifIdent_by_cameraId NOT FOUND] cameraId: {cameraId} — camera not found or disabled"
                )
                return None

        except Exception as e:
            self.insLogger.log_error(
                msg=f"[MongoQueryGeneral--query_verifIdent_by_cameraId ERROR] cameraId: {cameraId} — verifIdent query failed: {e}"
            )
            return None

#--------------------------------------------------------------------------------------------------------------
    def query_user_by_pinNumber(self, pinNumber: str):
        users_collection = self.db["users"]

        try:
            user_doc = users_collection.find_one({
                "pinNumber": pinNumber,
                "enable": True
            })

            if user_doc:
                full_name = f"{user_doc.get('firstName', '')} {user_doc.get('lastName', '')}".strip()
                self.insLogger.log_info(
                    msg=f"[MongoQueryGeneral--query_user_by_pinNumber] User found: {full_name} for PIN: {pinNumber}"
                )
                return full_name

            self.insLogger.log_error(
                msg=f"[MongoQueryGeneral--query_user_by_pinNumber NOT FOUND] No enabled user found with pinNumber: {pinNumber}"
            )
            return None

        except Exception as e:
            self.insLogger.log_error(
                msg=f"[MongoQueryGeneral--query_user_by_pinNumber ERROR] Failed to query user by pinNumber {pinNumber}: {e}"
            )
            return None

#--------------------------------------------------------------------------------------------------------------
    def get_user_document_by_faceId(self, faceId: str):
        try:
            user_doc = self.db["users"].find_one({
                "faceId": faceId,
                "enable": True
            })

            if user_doc:
                return user_doc
            else:
                self.insLogger.log_error(
                    msg=f"[MongoQueryGeneral--get_user_document_by_faceId NOT FOUND] No user found with faceId: {faceId}"
                )
                return None
        except Exception as e:
            self.insLogger.log_error(
                msg=f"[MongoQueryGeneral--get_user_document_by_faceId ERROR] {e}"
            )
            return None

#--------------------------------------------------------------------------------------------------------------
    def query_cards_by_faceId(self, faceId):
        user_doc = self.get_user_document_by_faceId(faceId)
        return user_doc.get("cardNumbers") if user_doc else None

#--------------------------------------------------------------------------------------------------------------
    def query_pin_by_faceId(self, faceId):
        user_doc = self.get_user_document_by_faceId(faceId)
        return user_doc.get("pinNumber") if user_doc else None

#--------------------------------------------------------------------------------------------------------------
    def query_verifIdent_by_faceId(self, faceId):
        user_doc = self.get_user_document_by_faceId(faceId)
        return user_doc.get("verifIdent") if user_doc else None

#--------------------------------------------------------------------------------------------------------------
    def get_user_document_by_card_number(self, cardNumber: str):
        try:
            user_doc = self.db["users"].find_one({
                "cardNumbers": cardNumber,
                "enable": True
            })

            if user_doc:
                return user_doc
            else:
                self.insLogger.log_error(
                    msg=f"[MongoQueryGeneral--get_user_document_by_card_number NOT FOUND] No user found with cardNumber: {cardNumber}"
                )
                return None
        except Exception as e:
            self.insLogger.log_error(
                msg=f"[MongoQueryGeneral--get_user_document_by_card_number ERROR] {e}"
            )
            return None

#--------------------------------------------------------------------------------------------------------------
    def query_verifIdent_by_card_number(self, cardNumber):
        user_doc = self.get_user_document_by_card_number(cardNumber)
        return user_doc.get("verifIdent") if user_doc else None

#--------------------------------------------------------------------------------------------------------------
    def update_access_zone_info_by_card_number(
            self, 
            cardNumber: str, 
            currentAccessZone: int
        ):
        users_collection = self.db["users"]

        try:
            user_doc = users_collection.find_one({"cardNumbers": cardNumber})

            if not user_doc:
                self.insLogger.log_error(f"[MongoQueryGeneral--update_access_zone_info_by_card_number NOT FOUND] No user found with card number: {cardNumber}")
                return False

            access_zones = user_doc.get("accessZones", [])
            if currentAccessZone not in access_zones:
                self.insLogger.log_error(
                    f"[MongoQueryGeneral--update_access_zone_info_by_card_number UPDATE] Zone {currentAccessZone} not allowed for user with card {cardNumber}. Allowed zones: {access_zones}"
                )
                return False

            update_fields = {
                "current_access_zone": currentAccessZone,
                "free_movement": False
            }

            result = users_collection.update_one(
                {"_id": user_doc["_id"]},
                {"$set": update_fields}
            )

            if result.modified_count > 0:
                self.insLogger.log_info(
                    f"[MongoQueryGeneral--update_access_zone_info_by_card_number ZONE UPDATE] Updated user (card: {cardNumber}) to current_access_zone={currentAccessZone}, free_movement=False"
                )
                return True
            else:
                self.insLogger.log_info(
                    f"[MongoQueryGeneral--update_access_zone_info_by_card_number ZONE UPDATE] No update needed for user with card: {cardNumber} (already set)"
                )
                return False

        except Exception as e:
            self.insLogger.log_error(f"[MongoQueryGeneral--update_access_zone_info_by_card_number MONGO ERROR] Failed to update zone for card {cardNumber}: {e}")
            return False

#--------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    from logger import CustomLogger
    from config_parser import Config_Init

    parser = ArgumentParser(description="Simple MongoDB Query Tool")

    # Common identifiers
    parser.add_argument("--faceId", help="User faceId")
    parser.add_argument("--cardNumber", help="User card number")
    parser.add_argument("--pinNumber", help="User PIN number")
    parser.add_argument("--cameraId", help="Camera ID")
    parser.add_argument("--zone", type=int, help="Zone number (used with update_access_zone_info_by_card_number)")

    # Explicit action selector
    parser.add_argument("--action", required=True, choices=[
        "get_user_by_faceId",
        "get_user_by_card",
        "get_user_by_pin",
        "get_access_zone_by_card",
        "get_access_zone_by_camera",
        "get_watchlist_by_camera",
        "get_reader_serial_by_camera",
        "get_verifIdent_by_camera",
        "get_cards_by_faceId",
        "get_pin_by_faceId",
        "get_verifIdent_by_faceId",
        "get_verifIdent_by_card",
        "update_zone_by_card"
    ], help="Action to perform")

    args = parser.parse_args()

    custom_logger = CustomLogger(
        backup_count = 5,
        max_bytes = 10485760,
        logfile = "config/query_general_log.log",
        logger_level = "INFO",
        util_prt = False,
        util_prt0 = True
    )
    custom_logger.exclude_debug_entries(r".*Lock \d+ acquired on queue\\.lock")
    custom_logger.log_info(msg=f"[MongoQueryGeneral] Starting Mongo query tool")

    insConfigInit = Config_Init()
    mq = MongoQueryGeneral(
        insLogger=custom_logger,
        ini_mongo_variables_dict = insConfigInit.get_variables_dict(category="mongo")
    )

    action = args.action

    if action == "get_user_by_faceId" and args.faceId:
        print(mq.query_user_by_faceId(args.faceId))

    elif action == "get_user_by_card" and args.cardNumber:
        print(mq.query_user_by_card_number(args.cardNumber))

    elif action == "get_user_by_pin" and args.pinNumber:
        print(mq.query_user_by_pinNumber(args.pinNumber))

    elif action == "get_access_zone_by_card" and args.cardNumber:
        print(mq.query_access_zone_info_by_card_number(args.cardNumber))

    elif action == "get_access_zone_by_camera" and args.cameraId:
        print(mq.query_access_zone_info_by_cameraId(args.cameraId))

    elif action == "get_watchlist_by_camera" and args.cameraId:
        print(mq.query_watchlistIds_by_cameraId(args.cameraId))

    elif action == "get_reader_serial_by_camera" and args.cameraId:
        print(mq.query_reader_serial_by_cameraId(args.cameraId))

    elif action == "get_verifIdent_by_camera" and args.cameraId:
        print(mq.query_verifIdent_by_cameraId(args.cameraId))

    elif action == "get_cards_by_faceId" and args.faceId:
        print(mq.query_cards_by_faceId(args.faceId))

    elif action == "get_pin_by_faceId" and args.faceId:
        print(mq.query_pin_by_faceId(args.faceId))

    elif action == "get_verifIdent_by_faceId" and args.faceId:
        print(mq.query_verifIdent_by_faceId(args.faceId))

    elif action == "get_verifIdent_by_card" and args.cardNumber:
        print(mq.query_verifIdent_by_card_number(args.cardNumber))

    elif action == "update_zone_by_card" and args.cardNumber and args.zone is not None:
        print(mq.update_access_zone_info_by_card_number(args.cardNumber, args.zone))

    else:
        print("Invalid combination of arguments. Use --help for details.")

#--------------------------------------------------------------------------------------------------------------
""" 
1. Query user by faceId
python3 mongo_query_general.py --faceId c76139e5bbedb049ddb23b89b79e4d3147771707 --action get_user_by_faceId 

2. Query user by cardNumber
python3 mongo_query_general.py --cardNumber 27515 --action get_user_by_card

3. Query user by pinNumber
python3 mongo_query_general.py --pinNumber 12345 --action get_user_by_pin

4. Get access zone info by cardNumber
python3 mongo_query_general.py --cardNumber 27515 --action get_access_zone_by_card

5. Get access zone info by cameraId
python3 mongo_query_general.py --cameraId {03a02f94-78a6-4f52-a01c-6aae751953eb} --action get_access_zone_by_camera

6. Get watchlistIds by cameraId
python3 mongo_query_general.py --cameraId {3b4e1aec-df23-44c8-be70-db708dd2ca2f} --action get_watchlist_by_camera

7. Get readerSerial by cameraId
python3 mongo_query_general.py --cameraId {3b4e1aec-df23-44c8-be70-db708dd2ca2f} --action get_reader_serial_by_camera

8. Get verifIdent (Verify/Ident mode) by cameraId
python3 mongo_query_general.py --cameraId {3b4e1aec-df23-44c8-be70-db708dd2ca2f} --action get_verifIdent_by_camera

9. Get card numbers by faceId
python3 mongo_query_general.py --faceId c76139e5bbedb049ddb23b89b79e4d3147771707 --action get_cards_by_faceId

10. Get PIN by faceId
python3 mongo_query_general.py --faceId c76139e5bbedb049ddb23b89b79e4d3147771707 --action get_pin_by_faceId

11. Get verifIdent by faceId
python3 mongo_query_general.py --faceId c76139e5bbedb049ddb23b89b79e4d3147771707 --action get_verifIdent_by_faceId

12. Get verifIdent by cardNumber
python3 mongo_query_general.py --cardNumber 27515 --action get_verifIdent_by_card

13. Update current_access_zone by cardNumber
python3 mongo_query_general.py --cardNumber 27515 --zone 2 --action update_zone_by_card

"""
#--------------------------------------------------------------------------------------------------------------