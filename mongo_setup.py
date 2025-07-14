# updated: 2025-06-25 17:12:46
# created: 2025-05-05 15:17:49
# filename: mongo_setup.py
#--------------------------------------------------------------------------------------------------------------
import os
import shutil
import argparse
from pathlib import Path
from bson import ObjectId
from csv import DictReader
from json import load, dump
from datetime import datetime
from logger import CustomLogger
from dataclasses import dataclass
from pymongo import MongoClient, errors
#--------------------------------------------------------------------------------------------------------------
@dataclass
class WatchlistedFaceCSV:       # users.json
    firstname: str              # firstName
    lastname: str               # lastName
    internal_id: str            # _id
    employee_id: str            # employeeId
    badge_id: str               # cardNumbers
    pin_number: str             # pinNumber
    access_zones: str           # accessZones
    customer_id: str            # customerId
    media_id: str               # faceId
#--------------------------------------------------------------------------------------------------------------
class MongoSetupTool:
    def __init__(
        self, 
        mongo_uri, 
        admin_user, 
        admin_password, 
        insLogger=None
    ):

        self.insLogger = insLogger
        self.class_name = "MongoSetupTool"
        self.mongo_uri = mongo_uri
        self.admin_user = admin_user
        self.admin_password = admin_password
        self.client = self._connect()
        self.insCameras = self._load_cameras()
        self.insServers = self._load_servers()
        self.insUsers = self._load_users()
#--------------------------------------------------------------------------------------------------------------
    def _connect(self):
        return MongoClient(
            self.mongo_uri,
            username=self.admin_user,
            password=self.admin_password,
            authSource="admin",
            authMechanism="SCRAM-SHA-1"
        )

    def add_database_user(self, db, new_user, new_password, roles):
        db_admin = self.client["admin"]
        role_list = [{"role": role.strip(), "db": db} for role in roles.split(",")]
        try:
            result = db_admin.command("usersInfo", new_user)
            if result.get("users"):
                db_admin.command("updateUser", new_user, roles=role_list)
                self.insLogger.log_info(msg=f"[MongoSetupTool--add_database_user] Updated roles for existing user '{new_user}' in DB '{db}'")
            else:
                db_admin.command("createUser", new_user, pwd=new_password, roles=role_list)
                self.insLogger.log_info(msg=f"[MongoSetupTool--add_database_user] Created new user '{new_user}' for DB '{db}'")
        except Exception as e:
            self.insLogger.log_error(msg=f"[MongoSetupTool--add_database_user] Failed to create/update user: {e}")

    def get_user_info(self, username="admin"):
        try:
            db_admin = self.client["admin"]
            user_info = db_admin.command("usersInfo", username)
            users = user_info.get("users", [])
            if users:
                self.insLogger.log_info(msg=f"[MongoSetupTool--get_user_info] Found {len(users)} user(s) named '{username}':")
                for user in users:
                    self.insLogger.log_info(msg=f"[MongoSetupTool--get_user_info] Username: {user.get('user')}, DB: {user.get('db')}, Roles: {user.get('roles')}")
            else:
                self.insLogger.log_info(msg=f"[MongoSetupTool--get_user_info] No user found with username '{username}'")
        except Exception as e:
            self.insLogger.log_error(msg=f"[MongoSetupTool--get_user_info] Failed to retrieve user info: {e}")

    def create_database(self, db_name):
        try:
            self.client[db_name].command("ping")
            self.insLogger.log_info(msg=f"[MongoSetupTool--create_database] Database '{db_name}' is accessible or created.")
        except Exception as e:
            self.insLogger.log_error(msg=f"[MongoSetupTool--create_database] Could not create/access database '{db_name}': {e}")

    def create_collections(self, db_name, collections):
        db = self.client[db_name]
        try:
            existing = db.list_collection_names()
            for coll in collections.split(","):
                coll = coll.strip()
                if coll in existing:
                    self.insLogger.log_info(msg=f"[MongoSetupTool--create_collections] Collection '{coll}' already exists in '{db_name}'")
                else:
                    db.create_collection(coll)
                    self.insLogger.log_info(msg=f"[MongoSetupTool--create_collections] Created collection '{coll}' in '{db_name}'")
        except Exception as e:
            self.insLogger.log_error(msg=f"[MongoSetupTool--create_collections] Failed to create collections: {e}")

    def initialize_db_with_dummy_doc(self, db_name):
        db = self.client[db_name]
        existing = db.list_collection_names()
        if not existing:
            db["__meta"].insert_one({"initialized": True})
            self.insLogger.log_info(msg=f"[MongoSetupTool--initialize_db_with_dummy_doc] Inserted dummy doc in '__meta' to make '{db_name}' visible.")
        else:
            self.insLogger.log_info(msg=f"[MongoSetupTool--initialize_db_with_dummy_doc] Database '{db_name}' already has collections: {existing}")

    def _load_cameras(self):
        try:
            with open("config/cameras.json", "r") as f:
                cameras = __import__("json").load(f)
            self.insLogger.log_info(msg=f"[MongoSetupTool--_load_cameras] Loaded {len(cameras)} cameras from file.")
            return cameras
        except Exception as e:
            self.insLogger.log_error(msg=f"[MongoSetupTool--_load_cameras] Failed to load cameras.json: {e}")
            return []

    def _load_servers(self):
        try:
            with open("config/servers.json", "r") as f:
                servers = __import__("json").load(f)
            self.insLogger.log_info(msg=f"[MongoSetupTool--_load_servers] Loaded {len(servers)} servers from file.")
            return servers
        except Exception as e:
            self.insLogger.log_error(msg=f"[MongoSetupTool--_load_servers] Failed to load servers.json: {e}")
            return []

    def _load_users(self):
        try:
            with open("config/users.json", "r") as f:
                users = __import__("json").load(f)
            self.insLogger.log_info(msg=f"[MongoSetupTool--_load_users] Loaded {len(users)} users from file.")
            return users
        except Exception as e:
            self.insLogger.log_error(msg=f"[MongoSetupTool--_load_users] Failed to load users.json: {e}")
            return []

    def load_config_to_mongo_and_files(self, db_name, config_path="config/config.json", backup_folder="config/config_backup/"):
        db = self.client[db_name]
        collection = db["config"]

        try:
            collection.drop()
            self.insLogger.log_info(msg=f"[MongoSetupTool--load_config_to_mongo_and_files] Dropped 'config' collection from '{db_name}'")

            os.makedirs(backup_folder, exist_ok=True)

            with open(config_path, "r") as f:
                config_data = __import__("json").load(f)

            if not isinstance(config_data, dict):
                self.insLogger.log_error(msg="[MongoSetupTool--load_config_to_mongo_and_files] config.json is not a valid dictionary.")
                return

            config_data["_id"] = ObjectId()
            collection.insert_one(config_data)
            self.insLogger.log_info(msg=f"[MongoSetupTool--load_config_to_mongo_and_files] Inserted config document into '{db_name}.config'")

            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_file = os.path.join(backup_folder, f"config-{timestamp}.json")

            config_data["_id"] = str(config_data["_id"])
            with open(backup_file, "w") as f:
                dump(config_data, f, indent=4)

            self.insLogger.log_info(msg=f"[MongoSetupTool--load_config_to_mongo_and_files] Saved backup to {backup_file}")

            backups = sorted(
                [f for f in os.listdir(backup_folder) if f.startswith("config-") and f.endswith(".json")],
                reverse=True
            )
            for old_file in backups[3:]:
                os.remove(os.path.join(backup_folder, old_file))
                self.insLogger.log_info(msg=f"[MongoSetupTool--load_config_to_mongo_and_files] Removed old backup: {old_file}")

        except Exception as e:
            self.insLogger.log_error(msg=f"[MongoSetupTool--load_config_to_mongo_and_files] Failed to load and backup config: {e}")

    def load_cameras_to_mongo_and_files(self, db_name, output_folder):
        db = self.client[db_name]
        collection = db["cameras"]

        try:
            collection.drop()
            self.insLogger.log_info(msg=f"[MongoSetupTool--load_cameras_to_mongo_and_files] Dropped 'cameras' collection from '{db_name}'")

            os.makedirs(output_folder, exist_ok=True)

            if not isinstance(self.insCameras, list):
                self.insLogger.log_error(msg="[MongoSetupTool--load_cameras_to_mongo_and_files] cameras.json must be a list")
                return

            for idx, camera_data in enumerate(self.insCameras):
                if not isinstance(camera_data, dict):
                    self.insLogger.log_warning(msg=f"[MongoSetupTool--load_cameras_to_mongo_and_files] Skipping non-dict entry at index {idx}")
                    continue

                camera_data["_id"] = ObjectId()
                collection.insert_one(camera_data)

                out_file = os.path.join(output_folder, f"camera_{idx+1:03}.json")
                camera_copy = dict(camera_data)
                camera_copy["_id"] = str(camera_copy["_id"])
                with open(out_file, "w") as f:
                    dump(camera_copy, f, indent=4)

                self.insLogger.log_info(msg=f"[MongoSetupTool--load_cameras_to_mongo_and_files] Inserted and saved camera_{idx+1:03}")

        except Exception as e:
            self.insLogger.log_error(msg=f"[MongoSetupTool--load_cameras_to_mongo_and_files] Failed to load cameras: {e}")

    def load_servers_to_mongo_and_files(self, db_name, output_folder):
        db = self.client[db_name]
        collection = db["servers"]

        try:
            collection.drop()
            self.insLogger.log_info(msg=f"[MongoSetupTool--load_servers_to_mongo_and_files] Dropped 'servers' collection from '{db_name}'")

            os.makedirs(output_folder, exist_ok=True)

            if not isinstance(self.insServers, list):
                self.insLogger.log_error(msg="[MongoSetupTool--load_servers_to_mongo_and_files] servers.json must be a list")
                return

            for idx, server_data in enumerate(self.insServers):
                if not isinstance(server_data, dict):
                    self.insLogger.log_warning(msg=f"[MongoSetupTool--load_servers_to_mongo_and_files] Skipping non-dict entry at index {idx}")
                    continue

                try:
                    server_data["_id"] = ObjectId()
                    collection.insert_one(server_data)

                    out_file = os.path.join(output_folder, f"server_{idx+1:03}.json")
                    server_copy = dict(server_data)
                    server_copy["_id"] = str(server_copy["_id"])
                    with open(out_file, "w") as f:
                        dump(server_copy, f, indent=4)

                    self.insLogger.log_info(msg=f"[MongoSetupTool--load_servers_to_mongo_and_files] Inserted and saved server_{idx+1:03}")

                except Exception as e:
                    self.insLogger.log_error(msg=f"[MongoSetupTool--load_servers_to_mongo_and_files] Failed insert at index {idx}: {e}")

        except Exception as e:
            self.insLogger.log_error(msg=f"[MongoSetupTool--load_servers_to_mongo_and_files] Failed to load servers: {e}")

    def load_users_to_mongo_and_files(self, db_name, output_folder):
        db = self.client[db_name]
        collection = db["users"]

        try:
            collection.drop()
            self.insLogger.log_info(msg=f"[MongoSetupTool--load_users_to_mongo_and_files] Dropped 'users' collection from '{db_name}'")
        except Exception as e:
            self.insLogger.log_error(msg=f"[MongoSetupTool--load_users_to_mongo_and_files] Could not drop collection: {e}")
            return

        try:
            os.makedirs(output_folder, exist_ok=True)
        except Exception as e:
            self.insLogger.log_error(msg=f"[MongoSetupTool--load_users_to_mongo_and_files] Failed to create output folder '{output_folder}': {e}")
            return

        if not isinstance(self.insUsers, list):
            self.insLogger.log_error(msg="[MongoSetupTool--load_users_to_mongo_and_files] users.json must be a list")
            return

        for idx, user_data in enumerate(self.insUsers):
            try:
                if not isinstance(user_data, dict):
                    self.insLogger.log_warning(msg=f"[MongoSetupTool--load_users_to_mongo_and_files] Skipping index {idx}: not a dictionary")
                    continue

                user_data["_id"] = ObjectId()
                collection.insert_one(user_data)

                out_file = os.path.join(output_folder, f"user_{idx+1:03}.json")
                user_copy = dict(user_data)
                user_copy["_id"] = str(user_copy["_id"])
                with open(out_file, "w") as f:
                    dump(user_copy, f, indent=4)

                self.insLogger.log_info(msg=f"[MongoSetupTool--load_users_to_mongo_and_files] Inserted and saved user_{idx+1:03}")

            except Exception as e:
                self.insLogger.log_error(msg=f"[MongoSetupTool--load_users_to_mongo_and_files] Failed to insert/save user_{idx+1:03}: {e}")

    def query_list_all_cameras(self, db_name, status=True):
        db = self.client[db_name]
        cameras_collection = db["cameras"]

        try:
            all_cameras = list(cameras_collection.find({"enable": status}))
            self.insLogger.log_info(msg=f"[MongoSetupTool--query_list_all_cameras] Total cameras found (enable={status}): {len(all_cameras)}")

            for cam in all_cameras:
                name = cam.get("probeFaceCameraName", "Unnamed")
                ip = cam.get("cameraIp", "Unknown IP")
                self.insLogger.log_info(msg=f"[MongoSetupTool--query_list_all_cameras] - {name} @ {ip}")

        except Exception as e:
            self.insLogger.log_error(msg=f"[MongoSetupTool--query_list_all_cameras] Failed to list cameras (enable={status}): {e}")

    def query_list_all_servers(self, db_name, status=True):
        db = self.client[db_name]
        servers_collection = db["servers"]

        try:
            query_filter = {"enable": status}
            all_servers = list(servers_collection.find(query_filter))

            self.insLogger.log_info(msg=f"[MongoSetupTool--query_list_all_servers] Total servers found (enable={status}): {len(all_servers)}")

            for srv in all_servers:
                name = srv.get("serverName", "Unnamed")
                ip = srv.get("hostname", "Unknown IP")
                srv_type = srv.get("type", "unknown").upper()
                self.insLogger.log_info(msg=f"[MongoSetupTool--query_list_all_servers] [{srv_type}] {name} @ {ip}")

        except Exception as e:
            self.insLogger.log_error(msg=f"[MongoSetupTool--query_list_all_servers] Server list query failed (enable={status}): {e}")

    def query_list_all_users(self, db_name, status=True):
        db = self.client[db_name]
        users_collection = db["users"]

        try:
            all_users = list(users_collection.find({"enable": status}))
            self.insLogger.log_info(msg=f"[MongoSetupTool--query_list_all_users] Total users found (enable={status}): {len(all_users)}")

            for user in all_users:
                name = f"{user.get('firstName', '')} {user.get('lastName', '')}".strip()
                face_id = user.get("faceId", "N/A")
                employee_id = user.get("employeeId", "N/A")
                self.insLogger.log_info(msg=f"[MongoSetupTool--query_list_all_users] - {name} | faceId: {face_id} | employeeId: {employee_id}")

        except Exception as e:
            self.insLogger.log_error(msg=f"[MongoSetupTool--query_list_all_users] Failed to list users (enable={status}): {e}")
    
    def close(self):
        self.client.close()

#--------------------------------------------------------------------------------------------------------------
    def load_users_from_csv(self, csv_path: str, json_path: str = "config/users.json"):
        method = "load_users_from_csv"
        csv_path = Path(csv_path)
        json_path = Path(json_path)
        user_backup_dir = Path("users_backup")
        user_backup_dir.mkdir(parents=True, exist_ok=True)

        if not csv_path.exists():
            self.insLogger.log_error(
                msg=f"[{self.class_name}--{method}] CSV file not found: {csv_path}"
            )
            return

        output_users = []
        try:
            with csv_path.open("r", newline='', encoding='utf-8') as f:
                reader = DictReader(f)
                for idx, row in enumerate(reader, start=1):
                    entry = WatchlistedFaceCSV(**row)
                    user = {
                        "_id": entry.internal_id,
                        "enable": True,
                        "firstName": entry.firstname,
                        "lastName": entry.lastname,
                        "faceId": entry.media_id,
                        "customerId": entry.customer_id,
                        "employeeId": entry.employee_id,
                        "cardNumbers": [entry.badge_id],
                        "pinNumber": entry.pin_number,
                        "accessZones": [int(z) for z in entry.access_zones.split(",") if z.strip()],
                        "current_access_zone": 0,
                        "free_movement": True,
                        "verifIdent": False,
                        "userGroups": {
                            "group1": "default",
                            "group2": "user"
                        }
                    }

                    output_users.append(user)

                    # Write individual user file
                    user_file = user_backup_dir / f"user_{idx:03}.json"
                    with user_file.open("w", encoding="utf-8") as uf:
                        dump(user, uf, indent=4)

        except Exception as e:
            self.insLogger.log_error(
                msg=f"[{self.class_name}--{method}] Failed while reading CSV: {e}"
            )
            return

        if not isinstance(output_users, list):
            self.insLogger.log_error(
                msg=f"[{self.class_name}--load_users_to_mongo_and_files] users.json must be a list"
            )
            return

        try:
            json_path.parent.mkdir(parents=True, exist_ok=True)
            with json_path.open("w", encoding='utf-8') as jf:
                dump(output_users, jf, indent=4)
        except Exception as e:
            self.insLogger.log_error(
                msg=f"[{self.class_name}--{method}] Failed writing users.json: {e}"
            )
            return

        self.insLogger.log_info(
            msg=f"[{self.class_name}--{method}] Loaded {len(output_users)} users from CSV"
        )
        self.insLogger.log_info(
            msg=f"[{self.class_name}--{method}] users.json written to {json_path}"
        )
        self.insLogger.log_info(
            msg=f"[{self.class_name}--{method}] Individual files saved to {user_backup_dir}/"
        )

#--------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="MongoDB Setup Tool (safe for updates)")
    parser.add_argument("--mongo_uri", default="mongodb://localhost:27017", help="Mongo URI")
    parser.add_argument("--admin_user", required=True, help="Admin username")
    parser.add_argument("--admin_password", required=True, help="Admin password")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # add_user
    p_user = subparsers.add_parser("add_user", help="Create or update user")
    p_user.add_argument("--db", required=True)
    p_user.add_argument("--new_user", required=True)
    p_user.add_argument("--new_password", required=True)
    p_user.add_argument("--roles", required=True, help="Comma-separated roles (e.g., readWrite,dbAdmin)")

    # Subcommand: get_user_info
    p_get_usr = subparsers.add_parser("get_user_info", help="Display info for a MongoDB user")
    p_get_usr.add_argument("--username", default="admin", help="MongoDB username to query (default: admin)")


    # create_db
    p_db = subparsers.add_parser("create_db", help="Ensure DB exists")
    p_db.add_argument("--db", required=True)

    # create_collections
    p_coll = subparsers.add_parser("create_collections", help="Create collections if they do not exist")
    p_coll.add_argument("--db", required=True)
    p_coll.add_argument("--collections", required=True, help="Comma-separated list (e.g., users,cameras,config)")

    # initialize dummy document
    p_init = subparsers.add_parser("init_db", help="Insert dummy doc to force DB visibility")
    p_init.add_argument("--db", required=True)

    # Subcommand: load_config
    p_load_cfg = subparsers.add_parser("load_config", help="Load config.json into MongoDB and create backup")
    p_load_cfg.add_argument("--db", required=True, help="Target database")
    p_load_cfg.add_argument("--config_path", default="config/config.json", help="Path to config.json")
    p_load_cfg.add_argument("--backup_folder", default="config/config_backup/", help="Folder to store backup copies")

    # Subcommand: load_cameras
    p_load_cam = subparsers.add_parser("load_cameras", help="Load cameras to MongoDB and save individual backups")
    p_load_cam.add_argument("--db", required=True)
    p_load_cam.add_argument("--output_folder", default="config/cameras_backup", help="Output folder for backups")

    # Subcommand: list_cameras_by_status
    p_list_cams = subparsers.add_parser("list_cameras_by_status", help="List cameras with 'enable' status True/False")
    p_list_cams.add_argument("--db", required=True, help="Target database")
    p_list_cams.add_argument("--status", choices=["true", "false"], required=True, help="Enable status to filter cameras")

    # Subcommand: load_servers
    p_load_srv = subparsers.add_parser("load_servers", help="Load servers to MongoDB and save individual backups")
    p_load_srv.add_argument("--db", required=True)
    p_load_srv.add_argument("--output_folder", default="config/servers_backup", help="Output folder for backups")

    # Subcommand: list_servers_by_status
    p_list_srvs = subparsers.add_parser("list_servers_by_status", help="List servers with 'enable' status True/False")
    p_list_srvs.add_argument("--db", required=True, help="Target database")
    p_list_srvs.add_argument("--status", choices=["true", "false"], required=True, help="Enable status to filter servers")

    # Subcommand: load_users
    p_load_usr = subparsers.add_parser("load_users", help="Load users to MongoDB and save individual backups")
    p_load_usr.add_argument("--db", required=True)
    p_load_usr.add_argument("--output_folder", default="config/users_backup", help="Output folder for backups")

    # Subcommand: list_users_by_status
    p_list_users = subparsers.add_parser("list_users_by_status", help="List users with 'enable' status True/False")
    p_list_users.add_argument("--db", required=True, help="Target database")
    p_list_users.add_argument("--status", choices=["true", "false"], required=True, help="Enable status to filter users")

    # Subcommand: load_users_from_csv
    p_load_csv = subparsers.add_parser("load_users_from_csv", help="Generate users.json and per-user backups from CSV")
    p_load_csv.add_argument("--csv", required=True, help="Path to input CSV file")
    p_load_csv.add_argument("--json", default="config/users.json", help="Path to output users.json file")


    args = parser.parse_args()

    custom_logger = CustomLogger(
        backup_count = 5,
        max_bytes = 10485760,
        logfile = "config/config_log.log",
        logger_level = "INFO",
        util_prt = False,
        util_prt0 = True
    )
    custom_logger.exclude_debug_entries(r".*Lock \d+ acquired on queue\.lock")
    custom_logger.debug("Lock 548462840704 acquired on queue.lock")
    custom_logger.log_info(f"[MONGO SETUP] ")   # insert tthe function as hand

    tool = MongoSetupTool(
        args.mongo_uri, 
        args.admin_user, 
        args.admin_password, 
        insLogger = custom_logger               # ✅ correct assignment
    )

    try:
        if args.command == "add_user":
            tool.add_database_user(args.db, args.new_user, args.new_password, args.roles)

        elif args.command == "get_user_info":
            tool.get_user_info(args.username)

        elif args.command == "create_db":
            tool.create_database(args.db)

        elif args.command == "create_collections":
            tool.create_collections(args.db, args.collections)

        elif args.command == "init_db":
            tool.initialize_db_with_dummy_doc(args.db)

        elif args.command == "load_config":
            tool.load_config_to_mongo_and_files(args.db, args.config_path, args.backup_folder)

        elif args.command == "load_cameras":
            tool.load_cameras_to_mongo_and_files(args.db, args.output_folder)

        elif args.command == "list_cameras_by_status":
            enable_flag = True if args.status.lower() == "true" else False
            tool.query_list_all_cameras(args.db, enable_flag)

        elif args.command == "load_servers":
            tool.load_servers_to_mongo_and_files(args.db, args.output_folder)

        elif args.command == "list_servers_by_status":
            enable_flag = True if args.status.lower() == "true" else False
            tool.query_list_all_servers(args.db, enable_flag)

        elif args.command == "load_users":
            tool.load_users_to_mongo_and_files(args.db, args.output_folder)

        elif args.command == "list_users_by_status":
            enable_flag = True if args.status.lower() == "true" else False
            tool.query_list_all_users(args.db, enable_flag)

        elif args.command == "load_users_from_csv":
            tool.load_users_from_csv(args.csv, args.json)


    finally:
        tool.close()

#--------------------------------------------------------------------------------------------------------------
""" 
1. Create:  add_user
python3 mongo_setup.py \
    --admin_user admin \
    --admin_password rf123 \
    add_user \
    --db accessDB2 \
    --new_user accadmin2 \
    --new_password 'mdb123!' \
    --roles readWrite,dbAdmin 

#--------------------------------------------------------------------------------------------------------------
2. Get:  get_user_info
python3 mongo_setup.py \
    --admin_user admin \
    --admin_password rf123 \
    get_user_info \
    --username accadmin2

#--------------------------------------------------------------------------------------------------------------
3. Create:  create_db
python3 mongo_setup.py \
    --admin_user admin \
    --admin_password rf123 \
    create_db \
    --db accessDB2 

#--------------------------------------------------------------------------------------------------------------
4. Init:  init_db
python3 mongo_setup.py \
    --admin_user admin \
    --admin_password rf123 \
    init_db \
    --db accessDB2

#--------------------------------------------------------------------------------------------------------------
5. Create:  create_collections
python3 mongo_setup.py \
    --admin_user admin \
    --admin_password rf123 \
    create_collections \
    --db accessDB2 \
    --collections users,cameras,servers,config

#--------------------------------------------------------------------------------------------------------------
6. Report:  list_servers_by_status
python3 mongo_setup.py \
    --admin_user admin \
    --admin_password rf123 \
    list_servers_by_status \
    --db accessDB2 \
    --status true

#--------------------------------------------------------------------------------------------------------------
7. Load:  load_config
python3 mongo_setup.py \
    --admin_user admin \
    --admin_password rf123 \
    load_config \
    --db accessDB2

#--------------------------------------------------------------------------------------------------------------
8. Load:  load_cameras
python3 mongo_setup.py \
    --admin_user admin \
    --admin_password rf123 \
    load_cameras \
    --db accessDB2 \
    --output_folder config/cameras_backup/

#--------------------------------------------------------------------------------------------------------------
9. Report:  list_cameras_by_status
python3 mongo_setup.py \
    --admin_user admin \
    --admin_password rf123 \
    list_cameras_by_status \
    --db accessDB2 \
    --status true

#--------------------------------------------------------------------------------------------------------------
10. Load:  load_servers
python3 mongo_setup.py \
    --admin_user admin \
    --admin_password rf123 \
    load_servers \
    --db accessDB2 \
    --output_folder config/servers_backup/

#--------------------------------------------------------------------------------------------------------------
11. Load:  load_users
python3 mongo_setup.py \
    --admin_user admin \
    --admin_password rf123 \
    load_users \
    --db accessDB2 \
    --output_folder config/users_backup/

#--------------------------------------------------------------------------------------------------------------
12. Report:  list_users_by_status
python3 mongo_setup.py \
    --admin_user admin \
    --admin_password rf123 \
    list_users_by_status \
    --db accessDB2 \
    --status true

#--------------------------------------------------------------------------------------------------------------
13. Load:  load_users_from_csv
python3 mongo_setup.py \
    --admin_user admin \
    --admin_password rf123 \
    load_users_from_csv \
    --csv exports/watchlist_export_test-bolo-01.csv \
    --json config/users.json
#--------------------------------------------------------------------------------------------------------------
"""
