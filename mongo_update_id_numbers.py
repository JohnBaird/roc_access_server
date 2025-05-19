# updated: 2025-05-15 16:13:20
# created: 2025-05-15 13:24:05
# filename: mongo_update_id_numbers.py
#--------------------------------------------------------------------------------------------------------------
from time import sleep
from bson import ObjectId
from pymongo import MongoClient, UpdateOne

#--------------------------------------------------------------------------------------------------------------
class MongoIdNumberUpdater:
    def __init__(
            self, 
            insLogger
        ):

        self.insLogger = insLogger
        self.class_name = "MongoIdNumberUpdater"

        try:
            self.client = MongoClient(
                host="192.168.1.133",
                port=27017,
                username="admin",
                password="rf123",
                authSource="admin"
            )
            self.db = self.client["rww"]
            self.collection = self.db["watchlistedfaces"]

            host, port = self.client.address
            self.insLogger.log_info(
                msg=f"[{self.class_name}--__init__] Connected to MongoDB at {host}:{port}"
            )

        except Exception as e:
            self.insLogger.log_error(
                msg=f"[{self.class_name}--__init__] MongoDB connection failed: {e}"
            )
            self.collection = None

        self.default_idnumbers = [
            {"type": "Employee ID", "value": None},
            {"type": "Badge ID", "value": None},
            {"type": "PIN Number", "value": None},
            {"type": "Access Zones", "value": None}
        ]

#--------------------------------------------------------------------------------------------------------------
    def get_documents_to_update(self):
        method = "get_documents_to_update"
        query = {
            "$or": [
                {"idNumbers": {"$exists": False}},
                {"idNumbers": {"$eq": []}},
                {"internalId": {"$exists": False}},
                {"internalId": None}
            ]
        }

        try:
            docs = list(self.collection.find(query, {"_id": 1}))
            self.insLogger.log_info(
                msg=f"[{self.class_name}--{method}] Found {len(docs)} documents to update."
            )
            return docs
        except Exception as e:
            self.insLogger.log_error(
                msg=f"[{self.class_name}--{method}] Error during query: {e}"
            )
            return []

#--------------------------------------------------------------------------------------------------------------
    def preview_documents_missing_internal_id(self, limit=10):
        method = "preview_documents_missing_internal_id"
        query = {
            "$or": [
                {"idNumbers": {"$exists": False}},
                {"idNumbers": {"$eq": []}},
                {"internalId": {"$exists": False}},
                {"internalId": None}
            ]
        }

        try:
            docs = self.collection.find(query, {"_id": 1, "internalId": 1}).limit(limit)
            count = self.collection.count_documents(query)
            self.insLogger.log_info(
                msg=f"[{self.class_name}--{method}] Previewing {limit} of {count} documents needing internalId update:"
            )
            for doc in docs:
                self.insLogger.log_info(
                    msg=f"[{self.class_name}--{method}] _id={doc['_id']}, current internalId={doc.get('internalId')}"
                )
        except Exception as e:
            self.insLogger.log_error(
                msg=f"[{self.class_name}--{method}] Error during preview: {e}"
            )

#--------------------------------------------------------------------------------------------------------------
    def update_documents_in_batches(self, batch_size=50, delay_seconds=2, dry_run=True):
        method = "update_documents_in_batches"
        docs_to_update = self.get_documents_to_update()
        total = len(docs_to_update)

        for i in range(0, total, batch_size):
            batch = docs_to_update[i:i + batch_size]
            updates = []
            ids_in_batch = []

            for doc in batch:
                _id = doc["_id"]
                generated_internal_id = str(ObjectId()).upper()

                updates.append(
                    UpdateOne(
                        {"_id": _id},
                        {
                            "$set": {
                                "idNumbers": self.default_idnumbers,
                                "internalId": generated_internal_id
                            }
                        }
                    )
                )
                ids_in_batch.append((_id, generated_internal_id))

                self.insLogger.log_info(
                    msg=f"[{self.class_name}--{method}] Prepared update for _id={_id} with internalId={generated_internal_id} (dry_run={dry_run})"
                )

            if not dry_run:
                try:
                    result = self.collection.bulk_write(updates)
                    self.insLogger.log_info(
                        msg=f"[{self.class_name}--{method}] Batch {i // batch_size + 1}: matched={result.matched_count}, modified={result.modified_count}"
                    )
                    if result.modified_count > 0:
                        for _id, internal_id in ids_in_batch:
                            self.insLogger.log_info(
                                msg=f"[{self.class_name}--{method}] Updated _id={_id}, internalId={internal_id}"
                            )
                except Exception as e:
                    self.insLogger.log_error(
                        msg=f"[{self.class_name}--{method}] Batch write failed: {e}"
                    )
                sleep(delay_seconds)
            else:
                for _id, internal_id in ids_in_batch:
                    self.insLogger.log_info(
                        msg=f"[{self.class_name}--{method}] Would update _id={_id}, internalId={internal_id} (dry run)"
                    )
                self.insLogger.log_info(
                    msg=f"[{self.class_name}--{method}] Skipped update for batch {i // batch_size + 1} (dry run)"
                )

        self.insLogger.log_info(
            msg=f"[{self.class_name}--{method}] Completed all batches. Total: {total}. Dry run: {dry_run}"
        )

#--------------------------------------------------------------------------------------------------------------
# Example usage:
import os
LOG_PATH = "config/updater.log"

# Delete existing log file if it exists
if os.path.exists(LOG_PATH):
    os.remove(LOG_PATH)

from logger import CustomLogger  # Replace with your actual logger path

if __name__ == "__main__":
    custom_logger = CustomLogger(
        backup_count=5,
        max_bytes=10485760,
        logfile=LOG_PATH,
        logger_level="INFO",
        util_prt=False,
        util_prt0=False
    )

    custom_logger.exclude_debug_entries(r".*Lock \d+ acquired on queue\.lock")
    custom_logger.debug("Lock 548462840704 acquired on queue.lock")
    custom_logger.log_info(msg=f"[MONGO UPDATER] Starting update process")

    insUpdater = MongoIdNumberUpdater(insLogger=custom_logger)
    # insUpdater.preview_documents_missing_internal_id(limit=10)  # See what will be touched
    insUpdater.update_documents_in_batches(dry_run=False)  # Set to False when ready
#--------------------------------------------------------------------------------------------------------------