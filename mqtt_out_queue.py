# updated: 2025-05-16 13:37:22
# created: 2024-07-21 19:24:15
# filename: mqtt_out_queue.py
#-----------------------------------------------------------------------------------------------------------------------------
from uuid import uuid4
from filelock import FileLock
from datetime import datetime
from mqtt_client import AccessPayload                                       # from a @dataclass 
from json import dump, dumps, loads, JSONDecodeError
from csv_writer import CSVwriter, TemperatureHeader, TransactionHeader     # from a @dataclass
#-----------------------------------------------------------------------------------------------------------------------------
class MQTToutQueue (object):

    # Constants
    ROUTED_TYPE_FACEMATCH = "FaceMatch"

    REQUIRED_KEYS = {  # Class attribute (shared across all instances)
        "_iD", "timestamp", "_watchlistId", "probeFaceCameraName", 
        "cameraId", "personId", "faceId", "firstname", "lastname", 
        "createdBy", "mqtt_target", "routed_msg_type"
    }
#----------------------------------------------------------    
    def __init__ (
            self,
            q,
            insLogger,
            insMQTTbroker,
            insMongoConfig,
            insMongoGeneral,
            insCSVtemperature,
            data_path,
            filename = "transaction_log.csv",
            own_serial_number = None,
            csv_logging_enable = True,
            util_prt = False,
            util_prt0 = False
        ):
        
        self.q = q
        self.insLogger = insLogger
        self.insMQTTbroker = insMQTTbroker
        self.insMongoGeneral = insMongoGeneral
        self.insCSVtemperature = insCSVtemperature

        self.file_lock_mqtt = FileLock('mqtt.lock')
        self.file_lock_queue = FileLock('queue.lock')

        self.own_serial_number = own_serial_number
        self.util_prt = util_prt
        self.util_prt0 = util_prt0

        if csv_logging_enable:
            self.insCSVtransaction = CSVwriter(
                insLogger,
                header = "transactionHeader",       # from a @dataclass
                filename = filename
            )
        else:
            self.insCSVtransaction = None

        mqtt_settings_dict = insMongoConfig.query_config_mqtt_settings()        # derived from mongo database (mqtt_settings)
        paho_mqtt_file = mqtt_settings_dict.get("paho_mqtt_file")
        self.paho_mqtt_file = f"{data_path}{paho_mqtt_file}"                    # created from config.ini and mongo database.

        general_settings_dict = insMongoConfig.query_config_general_settings()  # derived from mongo database (general_settings)
        self.paho_enable = general_settings_dict.get("paho_enable")
        self.gen_datim_format = general_settings_dict.get("datim_format")

        access_settings_dict = insMongoConfig.query_config_access_settings()    # derived from mongo database (access_settings)
        self.perimeter_zone = access_settings_dict.get("perimeter_zone")
        self.access_zone_function   = access_settings_dict.get("access_zone_function", False)
        self.anti_passback_function = access_settings_dict.get("anti_passback_function", False)
        self.watchlist_verif_dict   = access_settings_dict.get("watchlist_verif_dict", {})

        if self.util_prt0:
            print (f"paho_enable: {self.paho_enable}")
            print (f"paho_mqtt_file: {self.paho_mqtt_file}")
            print (f"perimeter_zone: {self.perimeter_zone}")
            print (f"gen_datim_format: {self.gen_datim_format}")
            print (f"access_zone_function: {self.access_zone_function}")
            print (f"watchlist_verif_dict: {self.watchlist_verif_dict}")
            print (f"anti_passback_function: {self.anti_passback_function}")  
#-----------------------------------------------------------------------------------------------------------------------------   
    def check_controller_serial_numbers (self, serial_number: str):
        return serial_number in self.unique_controller_serial_numbers_keys_tuple
#--------------------------------------------------
    def int_to_boolean_tuple(self, n):
        try:
            if n < 0 or n > 15:
                raise ValueError("Input must be between 0 and 15")
            return tuple(bool(n & (1 << i)) for i in range(4))
        except ValueError as e:
            self.insLogger.log_error(f"[BITMAP] Invalid input to int_to_boolean_tuple: {e}")
            return (False, False, False, False)  # Return safe default

#--------------------------------------------------
    def save_mqtt_message_to_file(self, dtt, file_path, message):
        dtt = dtt if dtt is not None else datetime.now()
        dtts = dtt.strftime("%Y-%m-%d_%H-%M-%S") + f"-{dtt.microsecond // 1000:03d}"
        file_name_dtt = f"{file_path}_alert_{dtts}"

        try:
            raw_payload = message.payload

            with open(file_name_dtt, 'wb') as f:
                f.write(raw_payload)

            self.insLogger.log_info(f"[MQTT] Message payload saved to {file_name_dtt}")

        except Exception as e:
            self.insLogger.log_error(f"[MQTT] Failed to save message payload: {e}")

#--------------------------------------------------
    def print_message_information (self, message_information):
        message, payload, payload_str, payload_json, fullname, faceId, cameraId, verifIdent = message_information

        print (f"message-type: {type(message)}") if self.util_prt else None
        print (f"payload-type: {type(payload)}") if self.util_prt else None
        print (f"payload_str-type: {type(payload_str)}") if self.util_prt else None
        print (f"payload_json-type: {type(payload_json)}") if self.util_prt else None
        print (f"message.topic: {message.topic}") if self.util_prt else None
        print (f"message.qos: {message.qos}") if self.util_prt0 else None
        print (f"message.retain: {message.retain}") if self.util_prt0 else None
        print (f"faceId: {faceId}, fullname: {fullname} & cameraId: {cameraId}, ") if self.util_prt else None
        print (f"verifIdent: {verifIdent} & cameraId: {cameraId}, ") if self.util_prt else None
#----------------------------------------------------------------------------------------------------------------
    def has_required_keys(self, json_data):
        return self.REQUIRED_KEYS.issubset(json_data.keys())
#----------------------------------------------------------------------------------------------------------------
# Function: evaluate_zone_access(self, cardNumber: str, cameraId: str)
#
# Description:
#     Evaluates if a user is allowed access through a camera-controlled access point based
#     on their accessZones, current_access_zone, and camera properties. Supports access
#     policies like zone path validation, free movement, and anti-passback enforcement.
#
# Return:
#     dict:
#         {
#             "allowed": bool,
#             "reason": str,
#             "zone_action": "updated" | "not_updated",
#             "used_free_pass": bool
#         }
#
# Step-by-step logic:
#     1. Fetch user access info and camera zone config from MongoDB.
#     2. If accessZones contain 0 (invalid), remove it and deny access.
#     3. If currentZone == 0 and free_movement is True and toZone is allowed:
#        - Update currentZone to toZone if updateZone=True
#        - Else, set currentZone = perimeter_zone
#        - Reset free_movement
#        - Grant access.
#     4. If access_zone_function is True:
#        - Deny if fromZone or toZone not in accessZones.
#     5. If currentZone < perimeter_zone:
#        - Override currentZone to perimeter_zone
#     6. If anti_passback_function is True:
#        - Deny access unless currentZone matches fromZone
#        - If free_movement is True, allow and reset it.
#     7. If updateZone is True:
#        - Update current_access_zone to toZone
#     8. Grant access if no denial was triggered.
#
# Notes:
#     - Uses structured logger with tags: [MQTToutQueue--evaluate_zone_access], [ZONE UPDATE], [MONGO QUERY]
#     - Honors system settings for logging, access enforcement, and zone rules.
#-------------------------------------------------------------------------------------------
    def evaluate_zone_access(self, cardNumber: str, cameraId: str):
        result = {
            "allowed": False,
            "reason": "",
            "zone_action": "not_updated",
            "used_free_pass": False
        }

        try:
            self.insLogger.log_info(msg="[MQTToutQueue--evaluate_zone_access] Step 1: Starting access evaluation")
            self.insLogger.log_info(msg=f"[MQTToutQueue--evaluate_zone_access] Step 1: cardNumber = {cardNumber}, cameraId = {cameraId}")

            # Step 2: Fetch user and camera info
            user_info = self.insMongoGeneral.query_access_zone_info_by_card_number(cardNumber)
            accessZones = user_info[0].get("accessZones", [])
            currentZone = user_info[1].get("current_access_zone")
            freeMovement = user_info[2].get("free_movement", False)

            camera_info = self.insMongoGeneral.query_access_zone_info_by_cameraId(cameraId)
            fromZone = camera_info.get("fromZone")
            toZone = camera_info.get("toZone")
            updateZone = camera_info.get("updateZone", False)

            self.insLogger.log_info(
                msg=f"[MQTToutQueue--evaluate_zone_access] Step 2: User accessZones={accessZones}, currentZone={currentZone}, freeMovement={freeMovement}"
            )
            self.insLogger.log_info(
                msg=f"[MQTToutQueue--evaluate_zone_access] Step 2: Camera fromZone={fromZone}, toZone={toZone}, updateZone={updateZone}"
            )

            # Step 3: Handle invalid zone 0
            if 0 in accessZones:
                result["reason"] = "[MQTToutQueue--evaluate_zone_access] Access denied: accessZones contains invalid zone 0"
                self.insLogger.log_error(msg=result["reason"])
                accessZones = [z for z in accessZones if z != 0]
                self.insMongoGeneral.db["users"].update_one({"cardNumbers": cardNumber}, {"$set": {"accessZones": accessZones}})
                self.insLogger.log_info(
                    msg="[MQTToutQueue--evaluate_zone_access] Step 3: Removed zone 0 from user's accessZones"
                )
                return result

            # Step 4: Undefined currentZone
            if currentZone == 0:
                if freeMovement and toZone in accessZones:
                    self.insLogger.log_info(msg="[MQTToutQueue--evaluate_zone_access] Step 4: currentZone == 0 and freeMovement allows access")
                    result["used_free_pass"] = True

                    if updateZone:
                        updated = self.insMongoGeneral.update_access_zone_info_by_card_number(cardNumber, toZone)
                        if updated:
                            result["zone_action"] = "updated"
                            self.insLogger.log_info(
                                msg=f"[MQTToutQueue--evaluate_zone_access] Step 4: User zone updated to {toZone}"
                            )
                    else:
                        self.insMongoGeneral.db["users"].update_one(
                            {"cardNumbers": cardNumber},
                            {"$set": {"current_access_zone": self.perimeter_zone, "free_movement": False}}
                        )
                        result["zone_action"] = "set_to_perimeter"
                        self.insLogger.log_info(
                            msg=f"[MQTToutQueue--evaluate_zone_access] Step 4: Set current_access_zone to perimeter zone {self.perimeter_zone}"
                        )

                    result["allowed"] = True
                    result["reason"] = "[MQTToutQueue--evaluate_zone_access] Access granted via free_movement (current_zone was 0)"
                    self.insLogger.log_info(msg=result["reason"])
                    return result
                else:
                    result["reason"] = "[MQTToutQueue--evaluate_zone_access] Access denied: current zone is undefined and no free pass"
                    self.insLogger.log_error(msg=result["reason"])
                    return result

            # Step 5: Enforce zone rules
            if self.access_zone_function:
                if fromZone not in accessZones or toZone not in accessZones:
                    result["reason"] = "[MQTToutQueue--evaluate_zone_access] Access denied: fromZone or toZone not in user's accessZones"
                    self.insLogger.log_error(msg=result["reason"])
                    return result
                self.insLogger.log_info(msg="[MQTToutQueue--evaluate_zone_access] Step 5: Zone access check passed")

                # Step 6: Perimeter override
                effectiveCurrentZone = currentZone
                if currentZone < self.perimeter_zone:
                    self.insLogger.log_info(
                        msg=f"[MQTToutQueue--evaluate_zone_access] Step 6: Perimeter override - treating current zone {currentZone} as {self.perimeter_zone}"
                    )
                    effectiveCurrentZone = self.perimeter_zone

                # Step 7: Anti-passback check
                if self.anti_passback_function:
                    if effectiveCurrentZone != fromZone:
                        if freeMovement:
                            self.insLogger.log_info(
                                msg="[MQTToutQueue--evaluate_zone_access] Step 7: Anti-passback mismatch but freeMovement allows"
                            )
                            result["used_free_pass"] = True
                            self.insMongoGeneral.db["users"].update_one(
                                {"cardNumbers": cardNumber},
                                {"$set": {"free_movement": False}}
                            )
                            self.insLogger.log_info(msg="[MQTToutQueue--evaluate_zone_access] Step 7: free_movement reset to False")
                        else:
                            result["reason"] = "[MQTToutQueue--evaluate_zone_access] Access denied: anti-passback violation"
                            self.insLogger.log_error(msg=result["reason"])
                            return result
                    else:
                        self.insLogger.log_info(msg="[MQTToutQueue--evaluate_zone_access] Step 7: Anti-passback direction OK")

            # Step 8: Optional zone update
            if updateZone:
                updated = self.insMongoGeneral.update_access_zone_info_by_card_number(cardNumber, toZone)
                if updated:
                    result["zone_action"] = "updated"
                    self.insLogger.log_info(msg=f"[MQTToutQueue--evaluate_zone_access] Step 8: User zone updated to {toZone}")
            else:
                self.insLogger.log_info(msg="[MQTToutQueue--evaluate_zone_access] Step 8: Zone update not performed (updateZone is False)")

            result["allowed"] = True
            result["reason"] = "[MQTToutQueue--evaluate_zone_access] Access Granted"
            self.insLogger.log_info(msg=f"[MQTToutQueue--evaluate_zone_access] Step 8: {result['reason']}")
            return result

        except Exception as e:
            self.insLogger.log_error(msg=f"[MQTToutQueue--evaluate_zone_access ERROR] Exception occurred: {e}")
            return result

#-------------------------------------------------------------------------------------------
    def service_out_queue(self, dtt: datetime):
        with self.file_lock_queue:
            if self.q.empty():
                return

            try:
                dtts = dtt.strftime(self.gen_datim_format)
                message = self.q.get()
                topic = message.topic
                topic_serial_number = topic.split('/')[-1]

                self.insLogger.log_info(
                    msg=f"[MQTToutQueue--service_out_queue] topic={topic}"
                )

                if self.own_serial_number == topic_serial_number:
                    self.insLogger.log_info(
                        msg=f"[MQTToutQueue--service_out_queue] Ignored loopback message from self, serial={topic_serial_number}"
                    )
                    return

                if self.paho_enable:
                    self.save_mqtt_message_to_file(dtt, self.paho_mqtt_file, message)

                if not message.payload:
                    self.insLogger.log_error(
                        msg="[MQTToutQueue--service_out_queue] Received empty payload."
                    )
                    return

                payload_str = message.payload.decode('utf-8')
                payload_json = loads(payload_str)

                self.insLogger.log_debug(
                    msg=f"[MQTToutQueue--service_out_queue] Decoded payload: {payload_str}"
                )

                # If it's not a routed message, treat it as a regular JSON structure (msg_sd_...)
                if "routed_msg_type" not in payload_json:
                    self.parse_json_data(dtt, payload_json, topic_serial_number)
                    return

                # Skip if not a FaceMatch routed message
                if payload_json.get("routed_msg_type") != self.ROUTED_TYPE_FACEMATCH:
                    self.insLogger.log_info(
                        msg="[MQTToutQueue--service_out_queue] Skipping non-FaceMatch routed message."
                    )
                    return

                # Validate required keys
                if not self.has_required_keys(payload_json):
                    self.insLogger.log_error(
                        msg=f"[FaceMatch] Missing required keys in payload: {payload_str}"
                    )
                    return

                # All checks passed, handle the FaceMatch message
                self.handle_face_match(payload_json, dtt, topic_serial_number, dtts, message)


                # if "routed_msg_type" not in payload_json:
                #     self.parse_json_data(dtt, payload_json, topic_serial_number)    # follow the msg_struture: eg. msg_sd_msg_cpu_sensor
                #     return

                # if payload_json.get("routed_msg_type", "") != self.ROUTED_TYPE_FACEMATCH:
                #     self.insLogger.log_info(
                #         msg="[MQTToutQueue--service_out_queue] Skipping non-FaceMatch routed message."
                #     )
                #     return

                # if not self.has_required_keys(payload_json):
                #     self.insLogger.log_error(
                #         msg=f"[FaceMatch] Missing required keys in payload: {payload_str}"
                #     )
                #     return

                # self.handle_face_match(payload_json, dtt, topic_serial_number, dtts, message)   # follow the ROC_structure: routed_msg_type

            except JSONDecodeError as e:
                self.insLogger.log_error(
                    msg=f"[MQTToutQueue ERROR] Failed to parse JSON: {e}"
                )

            except Exception as e:
                self.insLogger.log_error(
                    msg=f"[MQTToutQueue ERROR] Unexpected exception: {e}"
                )

            finally:
                self.q.task_done()

#----------------------------------------------------------------------------------------------------------------
    def handle_face_match(self, payload_json, dtt, topic_serial_number, dtts, message):
        try:
            parsed = {k: payload_json.get(k, "") for k in self.REQUIRED_KEYS}
            objectId = parsed["_iD"]
            timestamp_str = datetime.fromtimestamp(parsed["timestamp"] / 1000).strftime(self.gen_datim_format)
            faceId = parsed["faceId"].strip()
            fullname = f"{parsed['firstname']} {parsed['lastname']}"
            cameraId = parsed["cameraId"]
            probeFaceCameraName = parsed["probeFaceCameraName"]
            _watchlistId = parsed["_watchlistId"]
            personId = parsed["personId"]
            createdBy = parsed["createdBy"]
            mqtt_target = parsed["mqtt_target"]
            # templateId = parsed["templateId"]       # derived from ROC Watch:  "watchlistedFaceMatch.templateId"

            self.insLogger.log_info(
                msg=f"[MQTToutQueue--handle_face_match] objectId={objectId}, cameraId={cameraId}, faceId={faceId}, name={fullname}"
            )
            self.insLogger.log_info(
                msg=f"[MQTToutQueue--handle_face_match] timestamp={timestamp_str}, createdBy={createdBy}, mqtt_target={mqtt_target}, probe={probeFaceCameraName}"
            )
            self.insLogger.log_info(
                msg=f"[MQTToutQueue--handle_face_match] watchlistId={_watchlistId}"
            )

            watchlistIds = self.insMongoGeneral.query_watchlistIds_by_cameraId(cameraId)
            self.insLogger.log_info(
                msg=f"[MQTToutQueue--handle_face_match] watchlistIds: {watchlistIds}"
            )

            permitted_ids = {wl_id for _, wl_id in watchlistIds} if watchlistIds else set()
            if _watchlistId not in permitted_ids:
                self.insLogger.log_info(
                    msg=f"[MQTToutQueue--handle_face_match] watchlistId {_watchlistId} not permitted for camera {cameraId} — skipping."
                )
                return

            link_serial_number = self.insMongoGeneral.query_reader_serial_by_cameraId(cameraId)
            if not link_serial_number:
                return

            if objectId not in self.insMQTTbroker.objectId_dict:
                self.insMQTTbroker.objectId_dict[objectId] = link_serial_number
            else:
                self.insLogger.log_warning(
                    msg=f"[MQTTBroker] Duplicate objectId detected: {objectId}"
                )

            fullName = self.insMongoGeneral.query_user_by_faceId(faceId) or "Person in DB Un-named!"
            found = fullName != "Person in DB Un-named!"
            card_numbers = self.insMongoGeneral.query_cards_by_faceId(faceId)
            pin_number = self.insMongoGeneral.query_pin_by_faceId(faceId)
            card_number = (card_numbers or [None])[-1]
            pincode = None

            self.insLogger.log_info(
                msg=f"[MQTToutQueue--handle_face_match] User Lookup, faceId={faceId}, name={fullName}, card_numbers={card_numbers}, pin_number={pin_number}"
            )

            result = self.evaluate_zone_access(cardNumber=card_number, cameraId=cameraId)
            if not result.get("allowed") or "access granted" not in result.get("reason", "").lower():
                payload = AccessPayload(        # from a @dataclass
                    objectId      = objectId,
                    serial_number = link_serial_number,
                    full_name     = fullName,
                    found         = False,
                    pincode       = pincode,
                    pin_number    = pin_number,
                    card_number   = card_number,
                    face_id       = faceId,
                    verif_ident   = False
                )
                self.insMQTTbroker.mqtt_publish_access_response(payload)

                self.insLogger.log_info(
                    msg = f"[MQTToutQueue--handle_face_match] Published access response: link_serial_number: {link_serial_number}, faceId: {faceId}, found: {found}"
                )

                return

            self.insLogger.log_debug(
                msg=f"[MQTToutQueue--handle_face_match] cardNumber={card_number}, cameraId={cameraId}, result={result}"
            )
            decision = "Granted" if result.get("allowed") else "DENIED"
            self.insLogger.log_info(
                msg=f"[MQTToutQueue--handle_face_match] {decision} for faceId={faceId} | Reason: {result.get('reason')}"
            )

            userVerifIdent = self.insMongoGeneral.query_verifIdent_by_card_number(cardNumber=card_number)
            mode = "Verify" if userVerifIdent else "Ident"
            self.insLogger.log_info(
                msg=f"[MQTToutQueue--handle_face_match] userVerifIdent_by_card_number: {card_number} userVerifIdent: {userVerifIdent} ({mode} mode)"
            )

            cameraVerifIdent = self.insMongoGeneral.query_verifIdent_by_cameraId(cameraId=cameraId)
            watchlistVerifList = list(self.watchlist_verif_dict.values())
            watchlistVerifIdent = _watchlistId in watchlistVerifList
            mode = "Verify" if watchlistVerifIdent else "Ident"
            self.insLogger.log_info(
                msg=f"[MQTToutQueue--handle_face_match] verifIdent_by_watchlistId: {_watchlistId} watchlistVerifIdent: {watchlistVerifIdent} ({mode} mode)"
            )

            payload = AccessPayload(        # from a @dataclass
                objectId      = objectId,
                serial_number = link_serial_number,
                full_name     = fullName,
                found         = found,
                pincode       = pincode,
                pin_number    = pin_number,
                card_number   = card_number,
                face_id       = faceId,
                verif_ident   = userVerifIdent or cameraVerifIdent or watchlistVerifIdent
            )
            self.insMQTTbroker.mqtt_publish_access_response(payload)
 
            self.insLogger.log_info(
                msg = f"[MQTToutQueue--handle_face_match] Published access response: link_serial_number: {link_serial_number}, faceId: {faceId}, found: {found}"
            )

            # self.insCSV.write_transaction_to_csv_file((uuid4().hex[:24], dtts, "FACE_Identified", faceId, fullName, link_serial_number))
            # self.insCSV.write_transaction_to_csv_file((uuid4().hex[:24], dtts, "UniqueId", personId, fullName, link_serial_number))

            # Creating an instance of TransactionHeader
            transaction_data = TransactionHeader(       # from a @dataclass
                _iD             = objectId,
                dateTime        = dtts,
                transactionType ='FACE_Identified',
                idNumber        = faceId,
                UniqueId        = personId,
                fullName        = fullName,
                serialSource    = link_serial_number
            )
            self.insCSVtransaction.write_transaction_to_csv_file(transaction_data)


            self.insLogger.log_info(
                msg=f"[MQTToutQueue--handle_face_match] Data written to CSV for faceId={faceId}, personId={personId}"
            )

            self.insLogger.log_debug(
                msg = f"[MQTToutQueue--handle_face_match] Simulated debug payload: {payload_json}"
            )

        except Exception as e:
            self.insLogger.log_error(
                msg=f"[MQTToutQueue--handle_face_match ERROR] Exception occurred: {str(e)}"
            )

#----------------------------------------------------------------------------------------------------------------
    def parse_json_data(self, dtt, payload_json, topic_serial_number):
        with self.file_lock_mqtt:
            try:
                dtt = dtt if dtt is not None else datetime.now()
                dtts = dtt.strftime(self.gen_datim_format)

                self.insLogger.log_info(
                    msg=f"[MQTToutQueue--parse_json_data] Topic serial number: {topic_serial_number}"
                )

                top_level_key = next(iter(payload_json))
                msg_data = next(iter(payload_json.values()))
                objectId = msg_data.get('_iD')
                date_time = msg_data.get('dateTime')
                host_name = msg_data.get('hostName')
                ip_address = msg_data.get('ipAddress')
                broad_cast = msg_data.get('broadCast', True)
                serial_source = msg_data.get('serialSource')
                serial_destination = msg_data.get('serialDestination')
                
                self.insLogger.log_info(
                    msg=f"[MQTToutQueue--parse_json_data] {top_level_key} received from topic_serial_number: {topic_serial_number}"
                )

                if not broad_cast and serial_destination != self.own_serial_number:
                    self.insLogger.log_info(
                        msg=f"[MQTToutQueue--parse_json_data] {top_level_key} skipped: not for this client (serialDestination: {serial_destination})"
                    )
                    return
                else:
                    self.insLogger.log_info(
                        msg=f"[MQTToutQueue--parse_json_data] {top_level_key} accepted: serialDestination: {serial_destination}, broadcast: {broad_cast}"
                    )

                if top_level_key == 'msg_sd_status':
                    response = msg_data.get('response')
                    reason = msg_data.get('reason')
                    self.insLogger.log_info(
                        msg=f"[MQTToutQueue--parse_json_data] {top_level_key} - serialSource: {serial_source}, response: {response}, reason: {reason}"
                    )

                elif top_level_key in ('msg_sd_msg_sensors', 'msg_sd_msg_cpu_sensor'):
                    sensor_name = msg_data.get('sensorName')
                    temperature = msg_data.get('Temperature')
                    if temperature is not None:
                        temperature = float(temperature)

                    # Creating an instance of TemperatureHeader
                    temperature_data = TemperatureHeader(       # from a @dataclass
                        _iD          = objectId,
                        dateTime     = dtts,
                        serialSource = topic_serial_number,
                        hostName     = host_name,
                        ipAddress    = ip_address,
                        sensorName   = sensor_name,
                        tempValue    = temperature
                    )
                    self.insCSVtemperature.write_temperature_to_csv_file(temperature_data)

                    self.insLogger.log_info(
                        msg=f"[MQTToutQueue--parse_json_data] {top_level_key} - serialSource: {serial_source}, sensorName: {sensor_name}, temperature: {temperature}"
                    )

                elif top_level_key == 'msg_sd_get_sysinfo':
                    self.insMQTTbroker.mqtt_publish_sysinfo_request()

                elif top_level_key == 'msg_sd_sysinfo':
                    file_name = f"clients_sysinfo/sysinfo_{topic_serial_number}.json"
                    with open(file_name, 'w') as file:
                        dump(msg_data, file, indent=4)

                elif top_level_key == 'msg_sd_get_config_file':
                    self.insMQTTbroker.mqtt_broadcast_sysconfig()

                elif top_level_key == 'msg_sd_sysconfig':
                    try:
                        json_string = dumps(msg_data)
                        loads(json_string)
                        self.insLogger.log_info(
                            msg=f"[MQTToutQueue--parse_json_data] {top_level_key}: The data is valid JSON."
                        )
                    except JSONDecodeError as e:
                        self.insLogger.log_error(
                            msg=f"[MQTToutQueue--parse_json_data] Invalid JSON data. Error: {e}"
                        )
                        return

                    if ('sysConfig' in msg_data and
                        'DEBOUNCE' in msg_data['sysConfig'] and
                        'HOLD_TIMER_VALUES' in msg_data['sysConfig']['DEBOUNCE']):
                        sorted_hold_timer_values = dict(
                            sorted(msg_data['sysConfig']['DEBOUNCE']['HOLD_TIMER_VALUES'].items()))
                        msg_data['sysConfig']['DEBOUNCE']['HOLD_TIMER_VALUES'] = sorted_hold_timer_values
                        self.insLogger.log_info(
                            msg=f"[MQTToutQueue--parse_json_data] Sorted HOLD_TIMER_VALUES."
                        )

                    if 'sysConfig' in msg_data and 'SERIAL_LOCATION' in msg_data['sysConfig']:
                        sorted_serial_values = dict(
                            sorted(msg_data['sysConfig']['SERIAL_LOCATION'].items()))
                        msg_data['sysConfig']['SERIAL_LOCATION'] = sorted_serial_values
                        self.insLogger.log_info(
                            msg=f"[MQTToutQueue--parse_json_data] Sorted SERIAL_LOCATION."
                        )

                    file_name = f'clients_sysinfo/config_{topic_serial_number}.json'
                    try:
                        with open(file_name, 'w') as file:
                            dump(msg_data, file, indent=4)
                        self.insLogger.log_info(
                            msg=f"[MQTToutQueue--parse_json_data] JSON configuration data saved to {file_name}"
                        )
                    except Exception as e:
                        self.insLogger.log_error(
                            msg=f"[MQTToutQueue--parse_json_data] Failed to write JSON to {file_name}. Error: {e}"
                        )

                elif top_level_key == 'msg_sd_get_inputs':
                    pass

                elif top_level_key == 'msg_sd_inputs_deb':
                    input_ports = msg_data.get('inputPorts')
                    actual_inputs = self.int_to_boolean_tuple(input_ports)
                    current_time = dtt.time()
                    input_schedule = None
                    # input_schedule = self.insJSONconfig.check_input_schedules(topic_serial_number, current_time)

                    if any(actual_inputs) or any(input_schedule):
                        self.insLogger.log_info(
                            msg=f"[MQTToutQueue--parse_json_data] actual_inputs: {actual_inputs}"
                        )
                        self.insLogger.log_info(
                            msg=f"[MQTToutQueue--parse_json_data] input_schedule: {input_schedule}"
                        )

                    if any(actual_inputs) and any(input_schedule):
                        for i, (actual, scheduled) in enumerate(zip(actual_inputs, input_schedule)):
                            if actual and scheduled:
                                self.insLogger.log_info(
                                    msg=f"[MQTToutQueue--parse_json_data] {topic_serial_number} Input {i+1} triggered and scheduled — reporting"
                                )
                                self.insAlertReport.prepare_schedule_input_alert_send(dtt, topic_serial_number, i)
                    else:
                        if any(actual_inputs) or any(input_schedule):
                            self.insLogger.log_info(
                                msg=f"[MQTToutQueue--parse_json_data] *** Window within range, no action required *** {topic_serial_number}"
                            )

                elif top_level_key in ('msg_sd_input_edge', 'msg_input'):
                    self.insLogger.log_info(
                        msg=f"[MQTToutQueue--parse_json_data] Input event received"
                    )
                    self.insLogger.log_info(
                        msg=f"[MQTToutQueue--parse_json_data] serialSource: {serial_source}"
                    )

                    recorded_datim = msg_data.get('dateTime')
                    if not recorded_datim:
                        self.insLogger.log_error(
                            msg=f"[MQTToutQueue--parse_json_data] Missing 'dateTime' in message"
                        )
                        return
                    self.insLogger.log_info(
                        msg=f"[MQTToutQueue--parse_json_data] recorded_datim: {recorded_datim}"
                    )

                    if 'inputPort' not in msg_data:
                        self.insLogger.log_error(
                            msg=f"[MQTToutQueue--parse_json_data] Missing 'inputPort' in message"
                        )
                        return
                    input_port = msg_data['inputPort']

                    if 'AlertType' not in msg_data:
                        self.insLogger.log_error(
                            msg=f"[MQTToutQueue--parse_json_data] Missing 'AlertType' in message"
                        )
                        return
                    alert_type = msg_data['AlertType']

                    self.insLogger.log_info(
                        msg=f"[MQTToutQueue--parse_json_data] inputPort: {input_port}, AlertType: {alert_type}"
                    )

                    alert_tuple = (topic_serial_number, recorded_datim, input_port, alert_type, "mqtt_external")
                    self.insLogger.log_info(
                        msg=f"[MQTToutQueue--parse_json_data] alert_tuple created: {alert_tuple}"
                    )
                    self.insAlertReport.analize_and_send_alert(dtt, alert_tuple)

                elif top_level_key == 'msg_sd_get_outputs':
                    pass

                elif top_level_key == 'msg_sd_output':
                    output_port = msg_data.get("outputPort")
                    on_off = msg_data.get("onOff")
                    timer_value = msg_data.get("timerValue")

                    self.insLogger.log_info(
                        msg=f"[MQTToutQueue--parse_json_data] Output received: output_port={output_port}, on_off={on_off}, timer_value={timer_value}"
                    )

                elif top_level_key == 'msg_sd_clear_outputs':
                    pass

                elif top_level_key == 'msg_sd_hold_timers':
                    hold_timers = (
                        msg_data.get('Input1'),
                        msg_data.get('Input2'),
                        msg_data.get('Input3'),
                        msg_data.get('Input4')
                    )
                    self.insLogger.log_info(
                        msg=f"[MQTToutQueue--parse_json_data] Received hold_timers: {hold_timers}"
                    )

                elif top_level_key == 'msg_sd_users':
                    try:
                        json_string = dumps(msg_data)
                        loads(json_string)
                        self.insLogger.log_info(
                            msg=f"[MQTToutQueue--parse_json_data] {top_level_key}: The data is valid JSON."
                        )
                    except JSONDecodeError as e:
                        self.insLogger.log_error(
                            msg=f"[MQTToutQueue--parse_json_data] Invalid JSON data received. Error: {e}"
                        )
                        return

                    file_name = 'config/users_schema.json'
                    try:
                        with open(file_name, 'w') as file:
                            dump(msg_data, file, indent=4)
                        self.insLogger.log_info(
                            msg=f"[MQTToutQueue--parse_json_data] JSON data saved to {file_name}"
                        )
                    except Exception as e:
                        self.insLogger.log_error(
                            msg=f"[MQTToutQueue--parse_json_data] Failed to save JSON data to {file_name}. Error: {e}"
                        )

                elif top_level_key == 'msg_sd_log_transation':
                    objectId = msg_data.get('_iD')
                    serial_number = self.insMQTTbroker.objectId_dict.pop(objectId, None)
                    if serial_number is None:
                        return  # or handle the missing objectId if needed

                    if serial_source == serial_number:
                        # Creating an instance of TransactionHeader
                        transaction_data = TransactionHeader(       # from a @dataclass
                            _iD             = objectId,
                            dateTime        = msg_data.get('dateTime'),
                            transactionType = msg_data.get('transactionType'),
                            idNumber        = msg_data.get('idNumber'),
                            UniqueId        = f"{{{uuid4()}}}",
                            fullName        = msg_data.get('fullName'),
                            serialSource    = serial_source
                        )
                        self.insCSVtransaction.write_transaction_to_csv_file(transaction_data)

                        self.insLogger.log_info(
                            msg = f"[MQTToutQueue--parse_json_data] Logged transaction to CSV: data={transaction_data}"
                        )
                    else:
                        self.insLogger.log_error(
                            msg = f"[MQTToutQueue--parse_json_data ERROR] Transaction mismatch: serial_source={serial_source}, serial_number={serial_number}"
                        )

                elif top_level_key == 'msg_sd_msg_pincode':
                    face_id = msg_data.get("faceId")
                    pincode = msg_data.get("pinCode")
                    pin_number = msg_data.get("pinNumber")
                    card_number = msg_data.get("cardNumber")
                    access_zone_inside = msg_data.get("accessZoneInside")
                    access_zone_outside = msg_data.get("accessZoneOutside")
                    userVerifIdent = False

                    self.insLogger.log_info(
                        msg=f"[MQTToutQueue--parse_json_data] access_zone_inside={access_zone_inside}"
                    )
                    self.insLogger.log_info(
                        msg=f"[MQTToutQueue--parse_json_data] access_zone_outside={access_zone_outside}"
                    )

                    found = False
                    fullName = None

                    if card_number:
                        fullName = self.insMongoGeneral.query_user_by_card_number(cardNumber=card_number)
                        found = bool(fullName)
                        self.insLogger.log_info(
                            msg=f"[MQTToutQueue--parse_json_data] card_number={card_number} -> fullName='{fullName}', found={found}"
                        )
                        userVerifIdent = self.insMongoGeneral.query_verifIdent_by_card_number(cardNumber=card_number)
                        mode = "Verify" if userVerifIdent else "Ident"
                        self.insLogger.log_info(
                            msg=f"[MQTToutQueue--parse_json_data] userVerifIdent_by_card_number: {card_number} userVerifIdent: {userVerifIdent} ({mode} mode)"
                        )

                    elif face_id:
                        self.insLogger.log_info(
                            msg=f"[MQTToutQueue--parse_json_data] Received faceId={face_id} — no matching card or PIN logic executed"
                        )

                    elif pincode:
                        self.insLogger.log_info(
                            msg=f"[MQTToutQueue--parse_json_data] Received pincode={pincode} — no matching card or PIN logic executed"
                        )

                    elif pin_number:
                        fullName = self.insMongoGeneral.query_user_by_pinNumber(pinNumber=pin_number)
                        found = bool(fullName)
                        self.insLogger.log_info(
                            msg=f"[MQTToutQueue--parse_json_data] pin_number={pin_number} -> fullName='{fullName}', found={found}"
                        )

                    else:
                        self.insLogger.log_error(
                            msg=f"[MQTToutQueue--parse_json_data] No identifying information provided — skipping"
                        )

                    payload = AccessPayload(        # from a @dataclass
                        objectId      = objectId,
                        serial_number = topic_serial_number,
                        full_name     = fullName,
                        found         = found,
                        pincode       = pincode,
                        pin_number    = pin_number,
                        card_number   = card_number,
                        face_id       = face_id,
                        verif_ident   = userVerifIdent
                    )
                    self.insMQTTbroker.mqtt_publish_access_response(payload)

                    # verif_ident = userVerifIdent
                    # access_tuple = (topic_serial_number, fullName, found, pincode, pin_number, card_number, face_id, verif_ident)
                    # self.insMQTTbroker.mqtt_publish_access_response(access_tuple=access_tuple)

                    self.insLogger.log_info(
                        msg=f"[MQTToutQueue--parse_json_data] MQTT Response published: fullName='{fullName}', card_number={card_number}, found={found}"
                    )

                else:
                    self.insLogger.log_error(
                        msg=f"[MQTToutQueue--parse_json_data] Invalid message received — unknown top-level key: '{top_level_key}'"
                    )

            except Exception as e:
                self.insLogger.log_error(
                    msg=f"[MQTToutQueue--parse_json_data ERROR] Exception while processing payload: {str(e)}"
                )

#----------------------------------------------------------------------------------------------------------------
#   _iD, dateTime, transactionCode, idNumber, fullName, serialSource
#   4388738612ee4fc4ba179f30, 2024/12/18  16:49:44, RFE_Access, 777, Push Button, 251096701259753
#-----------------------------------------------------------------------------------------------------------------------------