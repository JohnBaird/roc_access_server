# updated: 2025-04-23 15:27:25
# created: 2025-04-07 19:56:05
# filename: cameras.py
#--------------------------------------------------------------------------------------------------------------
from json import load, JSONDecodeError
#--------------------------------------------------------------------------------------------------------------
class Cameras:
    def __init__ (
            self, 
            insLogger, 
            filename = "config/cameras.json"
        ) -> None:
        
        self.insLogger = insLogger
        self.data = self.load_cameras(filename)
        self.report_on_cameraId_duplicates()

    def load_cameras(self, filename):
        try:
            with open(filename, 'r') as f:
                data = load(f)
                if not isinstance(data, list):
                    self.insLogger.log_error(
                        msg=f"[Cameras--load_cameras ERROR] Expected a list in {filename}, but got {type(data).__name__}"
                    )
                    return []
                self.insLogger.log_info(
                    msg=f"[Cameras--load_cameras] Successfully loaded configuration from {filename}"
                )
                return data

        except FileNotFoundError:
            self.insLogger.log_error(
                msg=f"[Cameras--load_cameras ERROR] File not found: {filename}"
            )
        except JSONDecodeError as e:
            self.insLogger.log_error(
                msg=f"[Cameras--load_cameras ERROR] Failed to decode JSON from {filename}: {e}"
            )
        except Exception as e:
            self.insLogger.log_error(
                msg=f"[Cameras--load_cameras ERROR] Unexpected error reading {filename}: {e}"
            )

        return []


    def check_duplicate_camera_ids(self):
        camera_id_map = {}
        duplicates = {}
        for cam in self.data:
            camera_id = cam.get("cameraId")
            name = cam.get("probeFaceCameraName", "Unnamed")
            if camera_id in camera_id_map:
                camera_id_map[camera_id].append(name)
                duplicates[camera_id] = camera_id_map[camera_id]
            else:
                camera_id_map[camera_id] = [name]
        return duplicates

    def report_on_cameraId_duplicates(self):
        try:
            duplicates = self.check_duplicate_camera_ids()
            if duplicates:
                self.insLogger.log_error("[Cameras--report_on_cameraId_duplicates] Duplicate cameraId's found:")
                for camera_id, names in duplicates.items():
                    self.insLogger.log_error(
                        msg = f"[Cameras--report_on_cameraId_duplicates ERROR] cameraId: {camera_id} is used by: {', '.join(names)}"
                    )
            else:
                self.insLogger.log_info (
                    msg = f"[Cameras--report_on_cameraId_duplicates] Validation successful: cameras.json contains only unique cameraId's."
                )
        except Exception as e:
            self.insLogger.log_error(
                msg = f"[Cameras--report_on_cameraId_duplicates ERROR] Failed to check cameraIds duplicates: {e}"
            )


    def query_reader_serial_by_cameraId(self, cameraId: str):
        try:
            for cam in self.data:
                if cam.get("cameraId") == cameraId:
                    if cam.get("enable", False):
                        serial = cam.get("readerSerial")
                        self.insLogger.log_info(f"[CAMERAS] Reader serial for cameraId {cameraId}: {serial}")
                        return serial
                    else:
                        self.insLogger.log_info(f"[CAMERAS] Camera {cameraId} is disabled.")
                        return None
            self.insLogger.log_error(f"[CAMERAS] Camera ID {cameraId} not found.")
            return None
        except Exception as e:
            self.insLogger.log_error(f"[CAMERAS] Error querying reader serial for cameraId {cameraId}: {e}")
            return None

    def query_reader_ip_by_cameraId(self, cameraId: str):
        try:
            for cam in self.data:
                if cam.get("cameraId") == cameraId:
                    if cam.get("enable", False):
                        ip = cam.get("readerIp")
                        self.insLogger.log_info(f"[CAMERAS] Reader IP for cameraId {cameraId}: {ip}")
                        return ip
                    else:
                        self.insLogger.log_info(f"[CAMERAS] Camera {cameraId} is disabled.")
                        return None
            self.insLogger.log_error(f"[CAMERAS] Camera ID {cameraId} not found.")
            return None
        except Exception as e:
            self.insLogger.log_error(f"[CAMERAS] Error querying reader IP for cameraId {cameraId}: {e}")
            return None

    def query_get_reader_serial_numbers_list(self):
        try:
            serials = set()
            for cam in self.data:
                if cam.get("enable", False):
                    serial = cam.get("readerSerial")
                    if serial:
                        serials.add(serial)
            result = list(serials)
            self.insLogger.log_info(f"[CAMERAS] Reader serial numbers (list): {result}")
            return result
        except Exception as e:
            self.insLogger.log_error(f"[CAMERAS] Failed to collect reader serial numbers list: {e}")
            return []

    def query_get_reader_serial_numbers_dict(self):
        try:
            serial_dict = {}
            for cam in self.data:
                if cam.get("enable", False):
                    name = cam.get("readerName")
                    serial = cam.get("readerSerial")
                    if name and serial:
                        serial_dict[name] = serial
            self.insLogger.log_info(f"[CAMERAS] Reader serial numbers (dict): {serial_dict}")
            return serial_dict
        except Exception as e:
            self.insLogger.log_error(f"[CAMERAS] Failed to collect reader serial numbers dict: {e}")
            return {}

    def query_watchlistIds_by_cameraId(self, cameraId: str):
        try:
            for cam in self.data:
                if cam.get("cameraId") == cameraId:
                    if cam.get("enable", False):
                        watchlist_ids = cam.get("watchlistIds", [])
                        self.insLogger.log_info(f"[CAMERAS] {cameraId} → watchlist IDs: {watchlist_ids}")
                        return watchlist_ids
                    else:
                        self.insLogger.log_info(f"[CAMERAS] Camera {cameraId} is disabled.")
                        return None
            self.insLogger.log_error(f"[CAMERAS] Camera ID {cameraId} not found.")
            return None
        except Exception as e:
            self.insLogger.log_error(f"[CAMERAS] Failed to query watchlist IDs for {cameraId}: {e}")
            return None

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

    insCameras = Cameras(
        insLogger = insLogger
    )

    reader_serial = insCameras.query_reader_serial_by_cameraId(
        cameraId="{ca6be1ff-757b-4c69-8425-a043f65820df}"
    )

    reader_ip = insCameras.query_reader_ip_by_cameraId(
        cameraId="{ca6be1ff-757b-4c69-8425-a043f65820df}"
    )

    reader_serial_numbers_list = insCameras.query_get_reader_serial_numbers_list()

    watchlistIds = insCameras.query_watchlistIds_by_cameraId(
        cameraId = "{03a02f94-78a6-4f52-a01c-6aae751953eb}"
    )
#--------------------------------------------------------------------------------------------------------------