# updated: 2025-06-25 18:00:16
# created: 2025-06-25 17:09:56
# filename: mongo_user_sync.py

#--------------------------------------------------------------------------------------------------------------
import argparse
import os
from pymongo import MongoClient
from bson import ObjectId
from logger import CustomLogger  # Replace with your actual logger path

#--------------------------------------------------------------------------------------------------------------
LOG_PATH = "logs/updater.log"

# Delete existing log file if it exists
if os.path.exists(LOG_PATH):
    os.remove(LOG_PATH)

#--------------------------------------------------------------------------------------------------------------
class MongoUserSync:
    def __init__(self, insLogger, host="localhost", port=27017):
        self.insLogger = insLogger
        self.client = MongoClient(
            host=host,
            port=port,
            username="admin",
            password="rf123",
            authSource="admin"
        )
        self.source_col = self.client["rww"]["watchlistedfaces"]
        self.target_col = self.client["accessDB2"]["users"]

    def get_id_number_value(self, id_numbers, key):
        for item in id_numbers:
            if item.get("type") == key:
                return item.get("value")
        return None

    def transform_document(self, src_doc):
        if not hasattr(self, 'card_counter'):
            self.card_counter = 1

        id_numbers = src_doc.get("idNumbers", [])

        def parse_list(value):
            if value is None or str(value).strip().lower() == "x":
                return [7, 8, 9, 10]
            if isinstance(value, str):
                try:
                    return [int(v.strip()) for v in value.split(",") if v.strip().isdigit()]
                except:
                    return [7, 8, 9, 10]
            return value if isinstance(value, list) else [7, 8, 9, 10]


        def parse_verif(value):
            return str(value).lower() == "true"

        def parse_card(value):
            if value is None:
                return []
            return [value] if value else []

        def parse_groups(value):
            return {"group1": value} if value else {}

        # Badge ID logic with "x" replacement
        card_value = self.get_id_number_value(id_numbers, "Badge ID")
        if isinstance(card_value, str) and card_value.strip().lower() == "x":
            card_value = str(self.card_counter)
            self.card_counter += 1

        return {
            "_id": src_doc["_id"],
            "enable": src_doc.get("enabled", True),
            "firstName": src_doc.get("firstname", "").strip(),
            "lastName": src_doc.get("lastname", "").strip(),
            "faceId": src_doc.get("internalId"),
            "customerId": src_doc.get("identityData", {}).get("customerId"),
            "employeeId": self.get_id_number_value(id_numbers, "Employee ID"),
            "cardNumbers": parse_card(card_value),
            "pinNumber": self.get_id_number_value(id_numbers, "PIN Number"),
            "accessZones": parse_list(self.get_id_number_value(id_numbers, "Access Zones")),
            "verifIdent": parse_verif(self.get_id_number_value(id_numbers, "Verif Ident")),
            "userGroups": parse_groups(self.get_id_number_value(id_numbers, "Access Groups")),
            "current_access_zone": 0,
            "free_movement": True
        }

#--------------------------------------------------------------------------------------------------------------
    def option1_recreate_users(self):
        self.target_col.delete_many({})
        count = 0
        for src_doc in self.source_col.find():
            tgt_doc = self.transform_document(src_doc)
            try:
                self.target_col.insert_one(tgt_doc)
            except Exception as e:
                self.insLogger.log_error(msg=f"[MongoUserSync--option1_recreate_users] Failed to insert _id={tgt_doc.get('_id')}, error={str(e)}")
                continue
            count += 1
        self.insLogger.log_info(msg=f"[MongoUserSync--option1_recreate_users] Inserted {count} transformed users into accessDB2.users")

#--------------------------------------------------------------------------------------------------------------
    def option2_update_changed_users(self):
        method = "option2_update_changed_users"
        update_count = 0
        for src_doc in self.source_col.find():
            tgt_doc_new = self.transform_document(src_doc)
            tgt_doc_old = self.target_col.find_one({"_id": tgt_doc_new["_id"]})
            if tgt_doc_old:
                update_fields = {}
                for key, new_val in tgt_doc_new.items():
                    old_val = tgt_doc_old.get(key)
                    if old_val != new_val:
                        update_fields[key] = new_val

                if update_fields:
                    _id = tgt_doc_new['_id']
                    internal_id = tgt_doc_new.get('faceId')
                    self.insLogger.log_info(
                        msg=f"[MongoUserSync--{method}] Would update _id={_id}, internalId={internal_id}"
                    )
                    self.target_col.update_one({"_id": tgt_doc_new["_id"]}, {"$set": update_fields})
                    update_count += 1
                    self.insLogger.log_info(msg=f"[MongoUserSync--option2_update_changed_users] Updated _id: {tgt_doc_new['_id']}, fields: {list(update_fields.keys())}")

        self.insLogger.log_info(msg=f"[MongoUserSync--option2_update_changed_users] Total updated documents: {update_count}")

#--------------------------------------------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Sync watchlistedfaces to users collection")
    parser.add_argument("--option", choices=["option1", "option2"], required=True, help="Choose sync option")
    args = parser.parse_args()

    custom_logger = CustomLogger(
        backup_count=5,
        max_bytes=10485760,
        logfile=LOG_PATH,
        logger_level="INFO",
        util_prt=False,
        util_prt0=False
    )

    custom_logger.exclude_debug_entries(r".*Lock \\d+ acquired on queue\\.lock")
    custom_logger.debug("Lock 548462840704 acquired on queue.lock")
    custom_logger.log_info(msg=f"[MONGO UPDATER] Starting update process")

    syncer = MongoUserSync(insLogger=custom_logger)

    if args.option == "option1":
        syncer.option1_recreate_users()
    elif args.option == "option2":
        syncer.option2_update_changed_users()

#--------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    main()

#--------------------------------------------------------------------------------------------------------------
"""
Example Usage:
source ./venv/bin/activate
python3 mongo_user_sync.py --option option1
python3 mongo_user_sync.py --option option2
"""

#--------------------------------------------------------------------------------------------------------------