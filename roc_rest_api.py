# updated: 2025-05-15 19:05:14
# created: 2025-05-11 16:53:52
# filename: roc_rest_api.py
#--------------------------------------------------------------------------------------------------------------
import re
import csv
from time import sleep
from pathlib import Path
from requests import get, post, exceptions
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning
from roc_api_keys import ROC_Api  # Assumes roc_api_keys.py exists in the same directory or Python path
from logger import CustomLogger
from json import load, dump  # ✅ as requested
from dataclasses import dataclass, asdict
# Disable SSL warnings for self-signed certs (optional, dev-only)
disable_warnings(InsecureRequestWarning)
#--------------------------------------------------------------------------------------------------------------
@dataclass
class WatchlistedFaceCSV:
    firstname: str
    lastname: str
    internal_id: str
    employee_id: str
    badge_id: str
    pin_number: str
    access_zones: str
    customer_id: str
    media_id: str
#--------------------------------------------------------------------------------------------------------------
class ROCRestAPI:
    def __init__(self, insLogger, rocServer):
        self.insLogger = insLogger

        # Load API credentials using rocServer (e.g., "rocdemo1")
        self.api = ROC_Api(insLogger=insLogger, rocServer=rocServer)
        (
            self.rocServer,
            self.serverIp,
            self.api_key,
            self.api_secret,
            self.user_access_id
        ) = self.api.get_credentials()

        # print (f"server:{self.rocServer}, ip:{self.serverIp}, key:{self.api_key}, secret:{self.api_secret}, user:{self.user_access_id}")

        self.base_url = f"https://{self.serverIp}/rest/v1"
        self.session = None
        self._prepare_session()

#--------------------------------------------------------------------------------------------------------------
    def _prepare_session(self):
        self.session = {
            "headers": {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "x-api-key": self.api_key,
                "x-api-secret": self.api_secret
            },
            "verify": False  # for self-signed certs
        }
        self.insLogger.log_info(
            msg=f"[ROCRestAPI--_prepare_session] Custom header auth session prepared for {self.rocServer} ({self.rocServer})"
        )

#--------------------------------------------------------------------------------------------------------------
    def get_camera_info(self, camera_uuid):
        """Call: GET /camera/{uuid}"""
        url = f"{self.base_url}/camera/{camera_uuid}"
        self.insLogger.log_info(msg=f"[ROCRestAPI--get_camera_info] Calling: {url}")

        try:
            response = get(
                url,
                headers=self.session["headers"],
                verify=self.session["verify"]
            )


            if response.status_code == 200:
                self.insLogger.log_info(
                    msg=f"[ROCRestAPI--get_camera_info] Success: {response.status_code}"
                )
                return response.json()
            else:
                self.insLogger.log_warning(
                    msg=f"[ROCRestAPI--get_camera_info] Failed: {response.status_code} | {response.text}"
                )
                return None

        except exceptions.RequestException as e:
            self.insLogger.log_error(
                msg=f"[ROCRestAPI--get_camera_info ERROR] Request failed: {e}"
            )
            return None

#--------------------------------------------------------------------------------------------------------------
    def get_cases(self, filter_name=None):
        """Call: GET /cases and optionally filter by case name."""
        url = f"{self.base_url}/cases"
        self.insLogger.log_info(msg=f"[ROCRestAPI--get_cases] Calling: {url}")

        try:
            response = get(
                url,
                headers=self.session["headers"],
                verify=self.session["verify"]
            )

            if response.status_code == 200:
                data = response.json()
                self.insLogger.log_info(
                    msg=f"[ROCRestAPI--get_cases] Success: {response.status_code}"
                )

                if filter_name:
                    # Filter by 'name'
                    for case in data.get("result", []):
                        if case.get("name") == filter_name:
                            self.insLogger.log_info(
                                msg=f"[ROCRestAPI--get_cases] Found case with name '{filter_name}' and _id: {case.get('_id')}"
                            )
                            return case.get("_id")
                    self.insLogger.log_warning(
                        msg=f"[ROCRestAPI--get_cases] No case found with name '{filter_name}'"
                    )
                    return None

                return data  # Unfiltered full response

            else:
                self.insLogger.log_warning(
                    msg=f"[ROCRestAPI--get_cases] Failed: {response.status_code} | {response.text}"
                )
                return None

        except exceptions.RequestException as e:
            self.insLogger.log_error(
                msg=f"[ROCRestAPI--get_cases ERROR] Request failed: {e}"
            )
            return None

#--------------------------------------------------------------------------------------------------------------
    def get_cameras_by_case_id(self, case_id, extract_only=False):
        """Call: GET /case/{caseId}/cameras and optionally extract URL and GUID."""
        url = f"{self.base_url}/case/{case_id}/cameras"
        self.insLogger.log_info(msg=f"[ROCRestAPI--get_cameras_by_case_id] Calling: {url}")

        try:
            response = get(
                url,
                headers=self.session["headers"],
                verify=self.session["verify"]
            )

            if response.status_code == 200:
                data = response.json()
                self.insLogger.log_info(
                    msg=f"[ROCRestAPI--get_cameras_by_case_id] Success: {response.status_code}"
                )

                if extract_only:
                    filtered = [
                        {"url": cam.get("url"), "GUID": cam.get("GUID")}
                        for cam in data.get("result", [])
                        if cam.get("url") and cam.get("GUID")
                    ]
                    return filtered

                return data

            else:
                self.insLogger.log_warning(
                    msg=f"[ROCRestAPI--get_cameras_by_case_id] Failed: {response.status_code} | {response.text}"
                )
                return None

        except exceptions.RequestException as e:
            self.insLogger.log_error(
                msg=f"[ROCRestAPI--get_cameras_by_case_id ERROR] Request failed: {e}"
            )
            return None

#--------------------------------------------------------------------------------------------------------------
    def update_camera_ids_from_api(self, case_name, cameras_json_path="config/cameras.json"):
        """
        Match and update cameraId fields in cameras.json using GUIDs from API response.
        Only updates entries matching both camera IP and rocServer.
        """
        self.insLogger.log_info(msg=f"[ROCRestAPI--update_camera_ids_from_api] Starting update for case: {case_name}")

        case_id = self.get_cases(filter_name=case_name)
        if not case_id:
            self.insLogger.log_error(msg=f"[ROCRestAPI--update_camera_ids_from_api] Case '{case_name}' not found")
            return False

        camera_list = self.get_cameras_by_case_id(case_id, extract_only=True)
        if not camera_list:
            self.insLogger.log_error(msg="[ROCRestAPI--update_camera_ids_from_api] No cameras found for case")
            return False

        json_path = Path(cameras_json_path)
        if not json_path.exists():
            self.insLogger.log_error(msg=f"[ROCRestAPI--update_camera_ids_from_api] File not found: {cameras_json_path}")
            return False

        try:
            with json_path.open("r") as f:
                local_cameras = load(f)
        except Exception as e:
            self.insLogger.log_error(msg=f"[ROCRestAPI--update_camera_ids_from_api] Failed to parse cameras.json: {e}")
            return False

        updated = False

        def extract_ip(rtsp_url):
            match = re.search(r"rtsp://([\d.]+)", rtsp_url)
            return match.group(1) if match else None

        ip_to_guid = {}
        for cam in camera_list:
            ip = extract_ip(cam.get("url", ""))
            guid = cam.get("GUID")
            if ip and guid:
                ip_to_guid[ip] = guid

        self.insLogger.log_info(msg=f"[ROCRestAPI--update_camera_ids_from_api] IP → GUID map: {ip_to_guid}")

        for entry in local_cameras:
            camera_ip = entry.get("cameraIp")
            roc_server = entry.get("rocServer")
            existing_guid = entry.get("cameraId")
            new_guid = ip_to_guid.get(camera_ip)

            self.insLogger.log_info(
                msg=(
                    f"[ROCRestAPI--update_camera_ids_from_api] ENTRY: cameraIp={camera_ip} | "
                    f"rocServer={roc_server} | file.cameraId={existing_guid} | api.GUID={new_guid}"
                )
            )

            if not camera_ip or not roc_server:
                self.insLogger.log_warning(
                    msg="[ROCRestAPI--update_camera_ids_from_api] Skipping entry with missing cameraIp or rocServer"
                )
                continue

            if roc_server != self.rocServer:
                self.insLogger.log_info(
                    msg=f"[ROCRestAPI--update_camera_ids_from_api] Skipping entry: rocServer mismatch ({roc_server} != {self.rocServer})"
                )
                continue

            if new_guid is None:
                self.insLogger.log_warning(
                    msg=f"[ROCRestAPI--update_camera_ids_from_api] No matching API GUID found for cameraIp {camera_ip} (entry will not be updated)"
                )
                continue

            if existing_guid != new_guid:
                self.insLogger.log_info(
                    msg=f"[ROCRestAPI--update_camera_ids_from_api] → Updating cameraId for cameraIp {camera_ip}: {existing_guid} → {new_guid}"
                )
                entry["cameraId"] = new_guid
                updated = True
            else:
                self.insLogger.log_info(
                    msg=f"[ROCRestAPI--update_camera_ids_from_api] → cameraId already correct for {camera_ip}"
                )


            if existing_guid != new_guid:
                self.insLogger.log_info(
                    msg=f"[ROCRestAPI--update_camera_ids_from_api] → Updating cameraId for cameraIp {camera_ip}: {existing_guid} → {new_guid}"
                )
                entry["cameraId"] = new_guid
                updated = True
            else:
                self.insLogger.log_info(
                    msg=f"[ROCRestAPI--update_camera_ids_from_api] → cameraId already correct for {camera_ip}"
                )

        if updated:
            try:
                with json_path.open("w") as f:
                    dump(local_cameras, f, indent=4)
                self.insLogger.log_info(msg="[ROCRestAPI--update_camera_ids_from_api] cameras.json updated successfully")
            except Exception as e:
                self.insLogger.log_error(msg=f"[ROCRestAPI--update_camera_ids_from_api] Failed to write cameras.json: {e}")
                return False
        else:
            self.insLogger.log_info(msg="[ROCRestAPI--update_camera_ids_from_api] No updates required")

        return updated

#--------------------------------------------------------------------------------------------------------------
    def get_watchlists(self):
        """Call: GET /watchlists — returns only enabled watchlists as {name: _id}."""
        url = f"{self.base_url}/watchlists"
        self.insLogger.log_info(msg=f"[ROCRestAPI--get_watchlists] Calling: {url}")

        try:
            response = get(
                url,
                headers=self.session["headers"],
                verify=self.session["verify"]
            )

            if response.status_code == 200:
                self.insLogger.log_info(
                    msg=f"[ROCRestAPI--get_watchlists] Success: {response.status_code}"
                )

                result = response.json()
                filtered = {
                    w["name"]: w["_id"]
                    for w in result.get("result", [])
                    if w.get("enabled", False)
                }

                for name, watchlist_id in filtered.items():
                    self.insLogger.log_info(
                        msg=f"[ROCRestAPI--get_watchlists] Watchlist: name='{name}' | _id={watchlist_id}"
                    )

                return filtered

            else:
                self.insLogger.log_warning(
                    msg=f"[ROCRestAPI--get_watchlists] Failed: {response.status_code} | {response.text}"
                )
                return {}

        except exceptions.RequestException as e:
            self.insLogger.log_error(
                msg=f"[ROCRestAPI--get_watchlists ERROR] Request failed: {e}"
            )
            return {}

#--------------------------------------------------------------------------------------------------------------
    def sync_watchlists_to_cameras(self, cameras_json_path="config/cameras.json"):
        """
        Sync watchlists from API into cameras.json.
        - Only updates entries where camera['rocServer'] == self.rocServer
        - Adds new watchlistIds that are missing
        - Removes any watchlistIds not found in current API result
        """
        self.insLogger.log_info(
            msg=f"[ROCRestAPI--sync_watchlists_to_cameras] Starting sync for server: {self.rocServer}"
        )

        watchlist_map = self.get_watchlists()
        if not watchlist_map:
            self.insLogger.log_warning(
                msg="[ROCRestAPI--sync_watchlists_to_cameras] No enabled watchlists found from API"
            )
            return False

        json_path = Path(cameras_json_path)
        if not json_path.exists():
            self.insLogger.log_error(
                msg=f"[ROCRestAPI--sync_watchlists_to_cameras] File not found: {cameras_json_path}"
            )
            return False

        try:
            with json_path.open("r") as f:
                local_cameras = load(f)
        except Exception as e:
            self.insLogger.log_error(
                msg=f"[ROCRestAPI--sync_watchlists_to_cameras] Failed to read JSON: {e}"
            )
            return False

        updated = False

        for camera in local_cameras:
            if camera.get("rocServer") != self.rocServer:
                continue

            if "watchlistIds" not in camera or not isinstance(camera["watchlistIds"], dict):
                camera["watchlistIds"] = {}

            current_ids = camera["watchlistIds"]
            new_ids = {}

            # Add/update watchlists
            for name, wid in watchlist_map.items():
                existing_id = current_ids.get(name)
                if existing_id != wid:
                    action = "Adding" if existing_id is None else "Updating"
                    self.insLogger.log_info(
                        msg=(
                            f"[ROCRestAPI--sync_watchlists_to_cameras] {action} watchlist '{name}' "
                            f"on camera {camera.get('cameraIp')} | old={existing_id} → new={wid}"
                        )
                    )
                    updated = True
                new_ids[name] = wid

            # Detect removed watchlists
            removed_keys = [k for k in current_ids if k not in watchlist_map]
            for k in removed_keys:
                self.insLogger.log_info(
                    msg=f"[ROCRestAPI--sync_watchlists_to_cameras] Removing outdated watchlist '{k}' from camera {camera.get('cameraIp')}"
                )
                updated = True

            camera["watchlistIds"] = new_ids

        # Write back if any changes made
        if updated:
            try:
                with json_path.open("w") as f:
                    dump(local_cameras, f, indent=4)
                self.insLogger.log_info(
                    msg="[ROCRestAPI--sync_watchlists_to_cameras] cameras.json updated successfully"
                )
            except Exception as e:
                self.insLogger.log_error(
                    msg=f"[ROCRestAPI--sync_watchlists_to_cameras] Failed to write cameras.json: {e}"
                )
                return False
        else:
            self.insLogger.log_info(
                msg="[ROCRestAPI--sync_watchlists_to_cameras] No changes were necessary"
            )

        return updated

#--------------------------------------------------------------------------------------------------------------
    def get_watchlist_summary(self):
        """Call: GET /watchlists/summary"""
        url = f"{self.base_url}/watchlists/summary"
        self.insLogger.log_info(msg=f"[ROCRestAPI--get_watchlist_summary] Calling: {url}")

        try:
            response = get(
                url,
                headers=self.session["headers"],
                verify=self.session["verify"]
            )

            if response.status_code == 200:
                self.insLogger.log_info(
                    msg=f"[ROCRestAPI--get_watchlist_summary] Success: {response.status_code}"
                )
                return response.json()
            else:
                self.insLogger.log_warning(
                    msg=f"[ROCRestAPI--get_watchlist_summary] Failed: {response.status_code} | {response.text}"
                )
                return None

        except exceptions.RequestException as e:
            self.insLogger.log_error(
                msg=f"[ROCRestAPI--get_watchlist_summary ERROR] Request failed: {e}"
            )
            return None

#---------------------------------------------------------------------------------------------------------------
    def get_watchlisted_faces_by_watchlist_id(self, watchlist_id, page=1, extract_only=True):
        url = f"{self.base_url}/watchlistedFace/{watchlist_id}/{page}"
        self.insLogger.log_info(
            msg=f"[ROCRestAPI--get_watchlisted_faces_by_watchlist_id] POSTing to: {url}"
        )

        try:
            response = post(
                url,
                headers=self.session["headers"],
                verify=self.session["verify"]
            )
            if response.status_code == 200:
                data = response.json()
                self.insLogger.log_info(
                    msg=(
                        f"[ROCRestAPI--get_watchlisted_faces_by_watchlist_id] "
                        f"Page {data.get('page', page)}/{data.get('totalPages', '?')} → "
                        f"{len(data.get('elements', []))} face(s)"
                    )
                )
                self.insLogger.log_debug(
                    msg=f"[DEBUG] Response JSON: {data}"
                )
                if extract_only:
                    return data.get("elements", [])
                return data
            else:
                self.insLogger.log_warning(
                    msg=f"[ROCRestAPI--get_watchlisted_faces_by_watchlist_id] Failed: {response.status_code} | {response.text}"
                )
                return [] if extract_only else None

        except exceptions.RequestException as e:
            self.insLogger.log_error(
                msg=f"[ROCRestAPI--get_watchlisted_faces_by_watchlist_id ERROR] Request failed: {e}"
            )
            return [] if extract_only else None

#---------------------------------------------------------------------------------------------------------------
    def sync_all_watchlisted_faces(self, delay_between_pages=0.001):
        """
        Fetch all watchlisted faces for all enabled watchlists.
        """
        self.insLogger.log_info(msg="[ROCRestAPI--sync_all_watchlisted_faces] Starting full sync...")

        all_faces = {}
        watchlists = self.get_watchlists()  # returns dict {name: _id}

        for name, watchlist_id in watchlists.items():
            self.insLogger.log_info(
                msg=f"[ROCRestAPI--sync_all_watchlisted_faces] Syncing faces for watchlist '{name}' (ID={watchlist_id})"
            )

            page = 1
            total_pages = 1
            faces = []

            while page <= total_pages:
                url = f"{self.base_url}/watchlistedFace/{watchlist_id}/{page}"
                self.insLogger.log_info(
                    msg=f"[ROCRestAPI--sync_all_watchlisted_faces] POSTing: {url}"
                )

                try:
                    response = post(
                        url,
                        headers={
                            "Accept": "application/json",
                            "Content-Type": "application/json",
                            "x-api-key": self.api_key,
                            "x-api-secret": self.api_secret
                        },
                        json={},
                        verify=self.session["verify"]
                    )

                    if response.status_code != 200:
                        self.insLogger.log_warning(
                            msg=f"[ROCRestAPI--sync_all_watchlisted_faces] Failed (page {page}): {response.status_code} | {response.text}"
                        )
                        break

                    result = response.json()
                    if page == 1:
                        total_pages = int(result.get("totalPages", 1))

                    elements = result.get("elements", [])
                    self.insLogger.log_info(
                        msg=f"[ROCRestAPI--sync_all_watchlisted_faces] Page {page}/{total_pages} → {len(elements)} face(s)"
                    )
                    faces.extend(elements)
                    page += 1
                    if page <= total_pages:
                        sleep(delay_between_pages)

                except exceptions.RequestException as e:
                    self.insLogger.log_error(
                        msg=f"[ROCRestAPI--sync_all_watchlisted_faces ERROR] Watchlist {watchlist_id} page {page} failed: {e}"
                    )
                    break

            self.insLogger.log_info(
                msg=f"[ROCRestAPI--sync_all_watchlisted_faces] Completed: '{name}' → {len(faces)} face(s)"
            )
            all_faces[name] = faces

        self.insLogger.log_info(msg="[ROCRestAPI--sync_all_watchlisted_faces] Sync complete for all watchlists.")
        return all_faces

#---------------------------------------------------------------------------------------------------------------
    def export_all_watchlisted_faces_to_csv(self, delay_between_pages=0.001):
        self.insLogger.log_info(msg="[ROCRestAPI--export_all_watchlisted_faces_to_csv] Starting export...")

        # Define the helper here
        def extract_id_value(id_numbers, target_type):
            for item in id_numbers:
                if item.get("type") == target_type:
                    return item.get("value")
            return None

        watchlists = self.get_watchlists()  # {name: _id}
        export_dir = Path("exports")
        export_dir.mkdir(exist_ok=True)

        for name, watchlist_id in watchlists.items():
            faces = []
            page = 1
            total_pages = 1

            while page <= total_pages:
                self.insLogger.log_info(
                    msg=f"[ROCRestAPI--export_all_watchlisted_faces_to_csv] Fetching page {page} of watchlist '{name}'"
                )
                result_full = self.get_watchlisted_faces_by_watchlist_id(
                    watchlist_id, page=page, extract_only=False
                )
                if not result_full:
                    break

                if page == 1:
                    total_pages = int(result_full.get("totalPages", 1))

                for entry in result_full.get("elements", []):
                    if not entry.get("enabled", False):
                        continue
                    if entry.get("firstname") == "0001" or entry.get("lastname") == "001":
                        continue

                    id_numbers = entry.get("idNumbers", [])  # ✅ Define this first

                    row = WatchlistedFaceCSV(
                        firstname=entry.get("firstname"),
                        lastname=entry.get("lastname"),
                        internal_id=entry.get("internalId"),
                        employee_id=extract_id_value(id_numbers, "Employee ID"),
                        badge_id=extract_id_value(id_numbers, "Badge ID"),
                        pin_number=extract_id_value(id_numbers, "PIN Number"),
                        access_zones=extract_id_value(id_numbers, "Access Zones"),
                        customer_id=entry.get("identityData", {}).get("customerId"),
                        media_id=entry.get("mediaId")
                    )
                    faces.append(row)

                page += 1
                if page <= total_pages:
                    sleep(delay_between_pages)

            if faces:
                filename_safe = re.sub(r"[^\w\-]", "_", name.lower())
                output_file = export_dir / f"watchlist_export_{filename_safe}.csv"
                with output_file.open("w", newline="") as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=WatchlistedFaceCSV.__annotations__.keys())
                    writer.writeheader()
                    for row in faces:
                        writer.writerow(asdict(row))
                self.insLogger.log_info(
                    msg=f"[ROCRestAPI--export_all_watchlisted_faces_to_csv] Exported {len(faces)} faces to {output_file}"
                )
            else:
                self.insLogger.log_info(
                    msg=f"[ROCRestAPI--export_all_watchlisted_faces_to_csv] No valid faces found for watchlist '{name}'"
                )

        self.insLogger.log_info(msg="[ROCRestAPI--export_all_watchlisted_faces_to_csv] Export complete.")


#---------------------------------------------------------------------------------------------------------------
# Example usage
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test ROC REST API endpoints")
    parser.add_argument("--server", required=True, help="Server name from .roc_api_keys.json (e.g., server_121)")
    parser.add_argument("--uuid", help="Camera UUID (required for get_camera_info)")
    parser.add_argument("--case_id", help="Case ID for retrieving associated cameras")
    parser.add_argument("--case_name", help="Case name for update_camera_ids or get_cameras_by_case_name")
    parser.add_argument("--watchlist_id", help="Watchlist ID to fetch faces from (for post_watchlist_faces_page)")
    parser.add_argument("--page", type=int, default=1, help="Page number to fetch (default: 1)")
    parser.add_argument("--dump", action="store_true", help="If set, dump the retrieved watchlisted faces to a local JSON file")

    parser.add_argument(
        "--action",
        required=True,
        choices=[
            "get_camera_info",
            "get_watchlist_summary",
            "get_cases",
            "get_cameras_by_case_id",
            "get_cameras_by_case_name",
            "update_camera_ids",
            "get_watchlists",
            "sync_watchlists",
            "sync_watchlisted_faces",
            "post_watchlist_faces_page",
            "export_watchlisted_faces_to_csv"
        ],
        help="API action to perform"
    )

    args = parser.parse_args()


    # Logger setup
    custom_logger = CustomLogger(
        backup_count=5,
        max_bytes=10485760,
        logfile="logs/roc_rest_api.log",
        logger_level="DEBUG",
        util_prt=False,
        util_prt0=False
    )
    custom_logger.exclude_debug_entries(r".*Lock \d+ acquired on queue\.lock")
    custom_logger.log_info(msg=f"[ROCRestAPI--example usage] REST Client starting for {args.server}...")

    # Create insClient
    insClient = ROCRestAPI(insLogger=custom_logger, rocServer=args.server)

    # Route to action
    if args.action == "get_camera_info":
        if not args.uuid:
            custom_logger.log_error(msg="Missing --uuid argument for get_camera_info")
        else:
            result = insClient.get_camera_info(args.uuid)
            custom_logger.log_info(msg=f"[ROCRestAPI--get_camera_info result] {result}")

    elif args.action == "get_watchlist_summary":
        result = insClient.get_watchlist_summary()
        custom_logger.log_info(msg=f"[ROCRestAPI--get_watchlist_summary result] {result}")

    elif args.action == "get_cases":
        result = insClient.get_cases(filter_name=args.case_name)
        custom_logger.log_info(msg=f"[ROCRestAPI--get_cases result] {result}")
        # print(result)   # Watchlist_summary

    elif args.action == "get_cameras_by_case_id":
        if not args.case_id:
            custom_logger.log_error(msg="Missing --case_id argument for get_cameras_by_case_id")
        else:
            result = insClient.get_cameras_by_case_id(args.case_id, extract_only=True)
            custom_logger.log_info(msg=f"[ROCRestAPI--get_cameras_by_case_id filtered] {result}")
            # print(result)  # Optional: Also print to stdout

    elif args.action == "get_cameras_by_case_name":
        if not args.case_name:
            custom_logger.log_error(msg="Missing --case_name argument for get_cameras_by_case_name")
        else:
            case_id = insClient.get_cases(filter_name=args.case_name)
            if not case_id:
                custom_logger.log_error(msg=f"No case ID found for case name: {args.case_name}")
            else:
                result = insClient.get_cameras_by_case_id(case_id, extract_only=True)
                custom_logger.log_info(msg=f"[ROCRestAPI--get_cameras_by_case_name result] {result}")
                # print(result)  # Optional stdout

    elif args.action == "update_camera_ids":
        if not args.case_name:
            custom_logger.log_error(msg="Missing --case_name argument for update_camera_ids")
        else:
            success = insClient.update_camera_ids_from_api(case_name=args.case_name)
            # print("✅ cameras.json updated." if success else "ℹ️ No update needed or an error occurred.")

    elif args.action == "get_watchlists":
        result = insClient.get_watchlists()
        custom_logger.log_info(msg=f"[ROCRestAPI--get_watchlists result] {result}")
        print(result)

    elif args.action == "sync_watchlists":
        result = insClient.sync_watchlists_to_cameras()
        custom_logger.log_info(msg=f"[ROCRestAPI--sync_watchlists_to_cameras result] {result}")
        print(result)

    elif args.action == "sync_watchlisted_faces":
        result = insClient.sync_all_watchlisted_faces()
        custom_logger.log_info(msg=f"[ROCRestAPI--sync_watchlisted_faces result] {result}")

    elif args.action == "post_watchlist_faces_page":
        if not args.watchlist_id:
            custom_logger.log_error(msg="Missing --watchlist_id argument for post_watchlist_faces_page")
        else:
            page = int(args.page) if args.page else 1
            result = insClient.get_watchlisted_faces_by_watchlist_id(args.watchlist_id, page=page)

            custom_logger.log_info(
                msg=f"[ROCRestAPI--post_watchlist_faces_page] Retrieved {len(result)} face(s) from page {page}"
            )

            from pathlib import Path

            filename = f"exports/watchlisted_faces_page_{page}.json"
            file_path = Path(filename)

            if args.dump:
                from json import dump
                with file_path.open("w") as f:
                    dump(result, f, indent=4)
                custom_logger.log_info(
                    msg=f"[ROCRestAPI--post_watchlist_faces_page] Dumped data to {filename}"
                )
            else:
                if file_path.exists():
                    file_path.unlink()
                    custom_logger.log_info(
                        msg=f"[ROCRestAPI--post_watchlist_faces_page] Deleted existing file: {filename}"
                    )

    elif args.action == "export_watchlisted_faces_to_csv":
        result = insClient.export_all_watchlisted_faces_to_csv()

    else:
        print(f"Invalid Selection! {args.action}")
#--------------------------------------------------------------------------------------------------------------
"""
python3 roc_rest_api.py --server rocdemo1 --action get_camera_info --uuid "{059643c9-f5c1-43f1-9067-c6f73c12582d}"
python3 roc_rest_api.py --server rocdemo1 --action get_cases
python3 roc_rest_api.py --server rocdemo1 --action get_cases --case_name "Live-01"
python3 roc_rest_api.py --server rocdemo1 --action get_cameras_by_case_id --case_id 682233c77152c60014d7b965
python3 roc_rest_api.py --server rocdemo1 --action get_cameras_by_case_name --case_name "Live-01"
python3 roc_rest_api.py --server rocdemo1 --action update_camera_ids --case_name "Live-01"
python3 roc_rest_api.py --server rocdemo1 --action get_watchlist_summary
python3 roc_rest_api.py --server rocdemo1 --action get_watchlists
python3 roc_rest_api.py --server rocdemo2 --action sync_watchlists

python3 roc_rest_api.py --server rocdemo1 --action post_watchlist_faces_page --watchlist_id 682235fd7152c60014d7caad --page 1
python3 roc_rest_api.py --server rocdemo1 --action post_watchlist_faces_page --watchlist_id 682235fd7152c60014d7caad --page 1 --dump

python3 roc_rest_api.py --server rocdemo2 --action sync_watchlisted_faces

python3 roc_rest_api.py --server rocdemo2 --action get_cameras_by_case_id --case_id 680558e3d3b56f001413fcf4

python3 roc_rest_api.py --server rocdemo1 --action export_watchlisted_faces_to_csv

"""
#--------------------------------------------------------------------------------------------------------------