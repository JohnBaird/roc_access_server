# updated: 2025-06-25 17:10:48
# created: 2025-06-25 17:10:09
# filename: mongo_update_id_numbers.py
# --------------------------------------------------------------------------------------------------------------
from time import sleep
from bson import ObjectId
from pymongo import MongoClient, UpdateOne

# --------------------------------------------------------------------------------------------------------------
class MongoIdNumberUpdater:
    def __init__(self, insLogger, host="localhost"):
        self.insLogger = insLogger
        self.class_name = "MongoIdNumberUpdater"

        try:
            self.client = MongoClient(
                host=host,
                port=27017,
                username="admin",
                password="rf123",
                authSource="admin"
            )

            self.client.admin.command("ping")  # Force actual connection
            self.db = self.client["rww"]
            self.collection = self.db["watchlistedfaces"]

            if self.client.address:
                conn_host, conn_port = self.client.address
                self.insLogger.log_info(
                    msg=f"[{self.class_name}--__init__] Connected to MongoDB at {conn_host}:{conn_port}"
                )
            else:
                self.insLogger.log_warning(
                    msg=f"[{self.class_name}--__init__] MongoClient created, but no server address available yet."
                )

        except Exception as e:
            self.insLogger.log_error(
                msg=f"[{self.class_name}--__init__] MongoDB connection failed: {e}"
            )
            self.collection = None

        self.default_idnumbers = [
            {"type": "Employee ID", "value": "x"},
            {"type": "Badge ID", "value": "x"},
            {"type": "PIN Number", "value": "x"},
            {"type": "Access Zones", "value": "x"},
            {"type": "Access Groups", "value": "x"},
            {"type": "Verif Ident", "value": "false"}
        ]

    # ----------------------------------------------------------------------------------------------------------
    def get_documents_to_update(self, overwrite=False):
        method = "get_documents_to_update"

        if overwrite:
            query = {}  # Match all documents
        else:
            query = {
                "$or": [
                    {"idNumbers": {"$exists": False}},
                    {"idNumbers": {"$eq": []}},
                    {"idNumbers.value": None},
                    {"idNumbers.value": ""},
                    {"internalId": {"$exists": False}},
                    {"internalId": None},
                    {"internalId": ""}
                ]
            }

        try:
            docs = list(self.collection.find(query, {"_id": 1, "internalId": 1, "idNumbers": 1}))
            self.insLogger.log_info(
                msg=f"[{self.class_name}--{method}] Found {len(docs)} documents to update."
            )
            return docs
        except Exception as e:
            self.insLogger.log_error(
                msg=f"[{self.class_name}--{method}] Error during query: {e}"
            )
            return []

    # ----------------------------------------------------------------------------------------------------------
    def update_documents_in_batches(self, batch_size=50, delay_seconds=2, dry_run=True, overwrite=True):
        method = "update_documents_in_batches"
        docs_to_update = self.get_documents_to_update(overwrite=overwrite)
        total = len(docs_to_update)

        for i in range(0, total, batch_size):
            batch = docs_to_update[i:i + batch_size]
            updates = []
            ids_in_batch = []

            for doc in batch:
                _id = doc["_id"]
                current_internal_id = doc.get("internalId")

                has_existing_value = current_internal_id is not None and str(current_internal_id).strip() != ""
                should_update_internal_id = overwrite or not has_existing_value

                if overwrite:
                    idnumbers_source = self.default_idnumbers
                else:
                    existing = doc.get("idNumbers")
                    if existing:
                        idnumbers_source = [
                            {
                                "type": entry.get("type"),
                                "value": (
                                    "false" if entry.get("type") == "Verif Ident"
                                    else "x" if entry.get("value") in [None, ""] else entry.get("value")
                                )
                            }
                            for entry in existing
                        ]
                    else:
                        idnumbers_source = self.default_idnumbers

                update_fields = {"idNumbers": idnumbers_source}

                if should_update_internal_id:
                    generated_internal_id = str(ObjectId()).upper()
                    update_fields["internalId"] = generated_internal_id
                else:
                    generated_internal_id = current_internal_id  # For logging only

                updates.append(
                    UpdateOne(
                        {"_id": _id},
                        {"$set": update_fields}
                    )
                )
                ids_in_batch.append((_id, generated_internal_id))

                self.insLogger.log_info(
                    msg=f"[{self.class_name}--{method}] Prepared update for _id={_id} with internalId={generated_internal_id} (dry_run={dry_run})"
                )

            if not updates:
                self.insLogger.log_info(
                    msg=f"[{self.class_name}--{method}] No updates prepared for batch {i // batch_size + 1} (all skipped)"
                )
                continue

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
            msg=f"[{self.class_name}--{method}] Completed all batches. Total: {total}. Dry run: {dry_run}. Overwrite: {overwrite}"
        )

# --------------------------------------------------------------------------------------------------------------
# Example usage
import os
from logger import CustomLogger  # Replace with your actual logger path

LOG_PATH = "logs/updater.log"
if os.path.exists(LOG_PATH):
    os.remove(LOG_PATH)

if __name__ == "__main__":
    custom_logger = CustomLogger(
        backup_count=5,
        max_bytes=10485760,
        logfile=LOG_PATH,
        logger_level="INFO",
        util_prt=False,
        util_prt0=False
    )

    custom_logger.exclude_debug_entries(r".*Lock \\d+ acquired on queue\\.lock")
    custom_logger.log_info(msg=f"[MONGO UPDATER] Starting update process")

    insUpdater = MongoIdNumberUpdater(
        insLogger=custom_logger,
        # host="192.168.1.104"
    )

    # insUpdater.preview_documents_missing_internal_id(limit=10)
    insUpdater.update_documents_in_batches(
        dry_run=False,
        overwrite=False
    )
    
#--------------------------------------------------------------------------------------------------------------