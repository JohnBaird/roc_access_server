# updated: 2025-05-10 17:54:06
# created: 2024-06-13 19:00:00
# filename: mqtt_client.py
#--------------------------------------------------------------------------------------------------
# https://www.eclipse.org/paho/index.php?page=clients/python/index.php 
# https://cedalo.com/blog/configuring-paho-mqtt-python-client-with-examples/
# https://www.eclipse.org/paho/index.php?page=clients/python/docs/index.php 
# http://www.steves-internet-guide.com/client-connections-python-mqtt/ 
#--------------------------------------------------------------------------------------------------
from time import sleep
from json import dumps, loads
from uuid import uuid4
from datetime import datetime
import paho.mqtt.client as mqtt
from dataclasses import dataclass
from ssl import PROTOCOL_TLS, CERT_REQUIRED
#--------------------------------------------------------------------------------------------------
@dataclass
class AccessPayload:
    objectId: str
    serial_number: str
    full_name: str
    found: bool
    pincode: str
    pin_number: str
    card_number: str
    face_id: str
    verif_ident: bool
#--------------------------------------------------------------------------------------------------
class MqttBroker (object):
    def __init__ (
            self,
            q,
            insLogger,
            insMongoConfig,
            insMachineInfo,
            util_prt = False,
            util_prt0 = False
        ) -> None:

        self.q = q
        self.insLogger = insLogger
        self.insMongoConfig = insMongoConfig
        self.insMachineInfo = insMachineInfo

        self.util_prt = util_prt
        self.util_prt0 = util_prt0

        mqtt_settings_dict = insMongoConfig.query_config_mqtt_settings() # derived from mongo database (mqtt_settings)
        self.mqtt_topic = mqtt_settings_dict.get("topic")
        self.mqtt_enable = mqtt_settings_dict.get("enable")
        self.mqtt_version = mqtt_settings_dict.get("version")
        self.mqtt_username = mqtt_settings_dict.get("username")
        self.mqtt_password = mqtt_settings_dict.get("password")
        self.mqtt_keepalive = mqtt_settings_dict.get("keepalive")
        self.mqtt_transport = mqtt_settings_dict.get("transport")
        self.mqtt_encryption = mqtt_settings_dict.get("encryption")
        self.mqtt_client_key = mqtt_settings_dict.get("client_key")
        self.mqtt_datim_format = mqtt_settings_dict.get("datim_format")
        self.mqtt_broker = mqtt_settings_dict.get("broker", "localhost")
        self.mqtt_certs_location = mqtt_settings_dict.get("certs_location")
        self.mqtt_authentication = mqtt_settings_dict.get("authentication")
        self.mqtt_offline_reporting = mqtt_settings_dict.get("offline_reporting")
        self.mqtt_server_certificate = mqtt_settings_dict.get("server_certificate")
        self.mqtt_client_certificate = mqtt_settings_dict.get("client_certificate")
        self.mqtt_status_reporting_enable = mqtt_settings_dict.get("status_reporting_enable")

        # mqtt_finalize_labels
        self.mqtt_port = 8883 if self.mqtt_encryption else 1883
        self.unique_client_id = insMachineInfo.get_unique_client_id ()
        self.own_serial_number = insMachineInfo.get_own_serial_number()
        self.mqtt_publish_topic = f"{self.mqtt_topic}/{self.own_serial_number}"

        general_settings_dict = insMongoConfig.query_config_general_settings() # derived from mongo database (general_settings)
        self.raspberry_pi = general_settings_dict.get("raspberry_pi")
        self.sys_name = insMachineInfo.get_raspberry_pi_model () if self.raspberry_pi else insMachineInfo.get_cpu_information ()
        self.hostname, self.ip_address = self.insMachineInfo.get_ip_address()
        self.program_version = insMachineInfo.program_version
        self.objectId_dict = {}

        # mqtt_general
        if self.util_prt0:
            print (f"mqtt_topic: {self.mqtt_topic}")
            print (f"mqtt_enable: {self.mqtt_enable}")
            print (f"mqtt_broker: {self.mqtt_broker}")
            print (f"mqtt_version: {self.mqtt_version}")
            print (f"raspberry_pi: {self.raspberry_pi}")
            print (f"mqtt_keepalive: {self.mqtt_keepalive}")
            print (f"mqtt_client_key: {self.mqtt_client_key}")
            print (f"unique_client_id: {self.unique_client_id}")
            print (f"mqtt_datim_format: {self.mqtt_datim_format}")
            print (f"own_serial_number: {self.own_serial_number}")
            print (f"mqtt_datim_format: {self.mqtt_datim_format}")
            print (f"mqtt_publish_topic: {self.mqtt_publish_topic}")
            print (f"mqtt_status_reporting_enable: {self.mqtt_status_reporting_enable}")
            
        # mqtt_credentials
        if self.util_prt0:
            print (f"mqtt_transport: {self.mqtt_transport}")
            print (f"mqtt_username: {self.mqtt_username}")
            print (f"mqtt_password: {self.mqtt_password}")
            print (f"mqtt_encryption: {self.mqtt_encryption}")
            print (f"mqtt_authentication: {self.mqtt_authentication}")
            print (f"mqtt_certs_location: {self.mqtt_certs_location}")
            print (f"mqtt_client_certificate: {self.mqtt_client_certificate}")
            print (f"mqtt_server_certificate: {self.mqtt_server_certificate}")
            
        self.connect ()
#--------------------------------------------------------------------------------------------------
    # def clear_controller_output_ports(self, dtt, serial_number):
    #     if serial_number == self.insJSONconfig.main_controller_serial_number and not self.main_controller_init:
    #         # Initialize main controller ports
    #         self.main_controller_init = True
    #         self.mqtt_clear_all_outputs_instruction(serial_number, broad_cast=False)
    #         self.insLogger.log_info(f"[OUTPUT INIT] Main controller {serial_number} initialized: {self.main_controller_init}")
    #     else:
    #         # Initialize other controller's ports
    #         serial_number_index = self.insJSONconfig.get_controller_serial_number_index(serial_number)
    #         if not self.controller_serial_numbers_init[serial_number_index]:
    #             self.controller_serial_numbers_init[serial_number_index] = True
    #             self.mqtt_clear_all_outputs_instruction(serial_number, broad_cast=False)
    #             self.insLogger.log_info(f"[OUTPUT INIT] Controller {serial_number} initialized at index {serial_number_index}")

#--------------------------------------------------------------------------------------------------
    def subscribe_bulk(self):
        def mqtt_subscribe(topic, qos=0):
            result = self.client.subscribe(topic, qos=qos)
            return result  # Returns a tuple: (result_code, mid)

        def get_combined_dict():
            reader_serial_numbers_dict = self.insMongoConfig.query_get_reader_serial_numbers_dict(status=True)
            server_serial_numbers_dict = self.insMongoConfig.query_get_servers_serial_numbers_dict(status=True)
            qr_code_servers_serial_numbers_dict = self.insMongoConfig.query_get_qr_code_servers_serial_numbers_dict(status=True)
            test_clients_serial_numbers_dict = self.insMongoConfig.query_config_mqtt_subscribe_test_clients(status=True)
            
            combined_items = list(reader_serial_numbers_dict.items()) + \
                            list(server_serial_numbers_dict.items()) + \
                            list(qr_code_servers_serial_numbers_dict.items()) + \
                            list(test_clients_serial_numbers_dict.items())

            seen_serials = set()
            combined_unique_dict = {}

            for key, serial in combined_items:
                if serial not in seen_serials:
                    combined_unique_dict[key] = serial
                    seen_serials.add(serial)

            self.insLogger.log_debug(msg=f"[MqttBroker--subscribe_bulk] reader_serial_numbers_dict: {reader_serial_numbers_dict}")
            self.insLogger.log_debug(msg=f"[MqttBroker--subscribe_bulk] server_serial_numbers_dict: {server_serial_numbers_dict}")
            self.insLogger.log_debug(msg=f"[MqttBroker--subscribe_bulk] qr_code_servers_serial_numbers_dict: {qr_code_servers_serial_numbers_dict}")
            self.insLogger.log_debug(msg=f"[MqttBroker--subscribe_bulk] test_clients_serial_numbers_dict: {test_clients_serial_numbers_dict}")
            self.insLogger.log_debug(msg=f"[MqttBroker--subscribe_bulk] combined_unique_dict: {combined_unique_dict}")

            return combined_unique_dict

        self.subscriptions = {}
        combined_unique_dict = get_combined_dict()

        for server_name, serial_number in combined_unique_dict.items():
            if serial_number == self.own_serial_number:
                continue

            subscribe_topic = f"{self.mqtt_topic}/{serial_number}"
            try:
                result_code, mid = mqtt_subscribe(topic=subscribe_topic.strip())
                self.subscriptions[mid] = {
                    'topic': subscribe_topic,
                    'server_name': server_name
                }
                self.insLogger.log_info(
                    msg=f"[MqttBroker--subscribe_bulk] Subscribed to topic '{subscribe_topic}' for server '{server_name}' (mid={mid})"
                )
            except Exception as e:
                self.insLogger.log_error(
                    msg=f"[MqttBroker--subscribe_bulk ERROR] Failed to subscribe to '{subscribe_topic}' for server '{server_name}': {e}"
                )

        if self.subscriptions:
            self.insLogger.log_info(
                msg=f"[MqttBroker--subscribe_bulk] All subscriptions initialized: {self.subscriptions}"
            )

#--------------------------------------------------------------------------------------------------
    def connect(self):
        try:
            # Set Connecting Client ID
            if self.mqtt_version == 'v3':
                self.client = mqtt.Client(
                    client_id=self.unique_client_id,
                    transport=self.mqtt_transport,
                    protocol=mqtt.MQTTv311,
                    clean_session=True
                )
            elif self.mqtt_version == 'v5':
                self.client = mqtt.Client(
                    client_id=self.unique_client_id,
                    transport=self.mqtt_transport,
                    protocol=mqtt.MQTTv5
                )
            else:
                self.client = mqtt.Client(self.unique_client_id)

            if self.mqtt_authentication:
                self.client.username_pw_set(
                    self.mqtt_username,
                    self.mqtt_password
                )

            if self.mqtt_encryption:
                self.client.tls_set(
                    ca_certs=self.mqtt_server_certificate,
                    certfile=self.mqtt_client_certificate,
                    keyfile=self.mqtt_client_key,
                    cert_reqs=CERT_REQUIRED,
                    tls_version=PROTOCOL_TLS,
                    ciphers=None
                )

            self.client.connected_flag = False
            self.client.disconnect_flag = False
            self.client.bad_connection_flag = False

            self.client.on_log = self.on_log
            self.client.on_connect = self.on_connect
            self.client.on_disconnect = self.on_disconnect
            self.client.on_publish = self.on_publish
            self.client.on_message = self.on_message
            self.client.on_subscribe = self.on_subscribe
            self.client.on_unsubscribe = self.on_unsubscribe

            self.client.loop_start()
            timer_count = 0

            self.client.connect(
                self.mqtt_broker,
                self.mqtt_port,
                self.mqtt_keepalive
            )

            while not self.client.connected_flag and not self.client.bad_connection_flag:
                timer_count += 1
                dots = "." * timer_count
                if self.util_prt0:
                    print(dots, end='', flush=True)
                sleep(0.2)

            connect_message = f"[MqttBroker--connect] Connected_flag detected in {200 * timer_count}-ms"
            client_id_message = f"[MqttBroker--connect] Connected using client_id: {self.unique_client_id}"

            if self.util_prt0:
                print(f" {connect_message}")

            self.insLogger.log_info(msg=connect_message)
            self.insLogger.log_info(msg=client_id_message)

        except Exception as e:
            self.client.loop_stop()
            error_message = f"[MqttBroker--connect ERROR] Connection failed: {e}"
            self.insLogger.log_error(msg=error_message)

#--------------------------------------------------------------------------------------------------
    def on_connect(self, client, userdata, flags, rc):
        try:
            self.insLogger.log_info("[MqttBroker--on_connect] Connection event triggered")

            if rc == 0:
                self.client.connected_flag = True
                self.client.disconnect_flag = False
                dtt = datetime.now()

                self.insLogger.log_info(
                    msg=f"[MqttBroker--on_connect] {self.unique_client_id} successfully connected to {self.mqtt_broker}"
                )

                self.subscribe_bulk()
                self.mqtt_publish_sysinfo_request()
                self.mqtt_publish_config_file_request(broad_cast=True)

                if self.mqtt_status_reporting_enable:
                    self.mqtt_publish_status(response="online", reason="restarted")
                    self.mqtt_publish_status_request()

                    temp_value = (
                        self.insMachineInfo.get_cpu_temperature_pi()
                        if self.raspberry_pi
                        else self.insMachineInfo.get_cpu_temperature_average()
                    )

                    self.mqtt_publish_cpu_temp_sensor(
                        sensor_name=self.sys_name,
                        sensor_value=temp_value
                    )
            else:
                self.client.loop_stop()
                self.client.bad_connection_flag = True
                self.insLogger.log_error(
                    msg=f"[MqttBroker--on_connect] Failed to connect to {self.mqtt_broker}, return code: {rc}"
                )

        except Exception as e:
            self.insLogger.log_error(
                msg=f"[MqttBroker--on_connect ERROR] Exception occurred during connection handling: {str(e)}"
            )

#--------------------------------------------------------------------------------------------------
    def on_disconnect(self, client, userdata, rc):
        self.insLogger.log_info("[MqttBroker--on_disconnect] MQTT client disconnected")
        self.client.connected_flag = False
        self.client.disconnect_flag = True

    def on_message(self, client, userdata, message):
        self.q.put(message)
        payload_str = message.payload.decode('utf-8')
        payload_json = loads(payload_str)
        self.insLogger.log_info(msg = f"[MqttBroker--on_message] Topic: {message.topic}")
        self.insLogger.log_debug(msg = f"[MqttBroker--on_message] Message: {payload_json}")
        
    def on_publish(self, client, userdata, result):
        self.insLogger.log_info("[MqttBroker--on_publish] Publish operation completed")

    def on_unsubscribe(self, client, userdata, mid):
        self.insLogger.log_info("[MqttBroker--on_unsubscribe] Unsubscribe event triggered")

    def on_log(self, client, userdata, level, buf):
        self.insLogger.log_debug("[MqttBroker--on_log] Log event triggered")
        self.insLogger.log_debug(f"[MqttBroker--on_log] {buf}")
        self.insLogger.log_debug(f"[MqttBroker--on_log] Broker in use: {self.mqtt_broker}")

    def on_subscribe(self, client, userdata, mid, granted_qos):
        subscription_info = self.subscriptions.get(mid, {'topic': 'Unknown', 'server_name': 'Unknown'})
        topic = subscription_info['topic']
        server_name = subscription_info['server_name']
        qos = granted_qos[0] if granted_qos else 'N/A'
        self.insLogger.log_info(
            f"[MqttBroker--on_subscribe] Subscribed to topic: {topic} from: {server_name} with QoS: {qos}"
        )

#==================================================================================================
# Messages for controllers
#==================================================================================================
    def create_and_publish(
            self,
            message_cmd,
            objectId = None,
            publish_topic = None,
            additional_params = None,
            serial_destination = None,
            broad_cast = False
        ):
        try:
            publish_topic = publish_topic or self.mqtt_publish_topic
            broad_cast = True if broad_cast is True else False
            objectId = objectId or uuid4().hex[:24]
            current_time = datetime.now()

            message = {
                message_cmd: {
                    "_iD":               objectId,
                    "clientId":          self.unique_client_id,
                    "programVersion":    self.program_version,
                    "serialSource":      self.own_serial_number,
                    "serialDestination": serial_destination,
                    "broadCast":         broad_cast,
                    "ipAddress":         self.ip_address,
                    "hostName":          self.hostname,
                    "unixTime":          int(current_time.timestamp()),
                    "dateTime":          current_time.strftime(self.mqtt_datim_format)
                }
            }

            if additional_params:
                message[message_cmd].update(additional_params)

            json_message = dumps(message)

            self.insLogger.log_debug(
                msg = f"[MqttBroker--create_and_publish] topic={publish_topic}, payload={json_message}"
            )

            if self.client.connected_flag:
                self.client.publish(topic=publish_topic, payload=json_message)
                self.insLogger.log_info(
                    msg = f"[MqttBroker--create_and_publish] Successful: objectId: {objectId}, "
                          f"publish_topic: {publish_topic}, message_cmd: {message_cmd}."
                )
            else:
                self.insLogger.log_warning(
                    msg = f"[MqttBroker--create_and_publish] Client not connected — publish skipped"
                )

        except Exception as e:
            self.insLogger.log_error(
                msg = f"[MqttBroker--create_and_publish ERROR] Failed to publish message: {str(e)}"
            )

#--------------------------------------------------------------------------------------------------
    def mqtt_publish_status (self, response, reason):
        if self.mqtt_status_reporting_enable:
            self.create_and_publish (
                message_cmd = "msg_sd_status", 
                additional_params = {
                    "response": response,
                    "reason": reason
                }
            )
#-------------------------------------------------------------------------------------------------
    def mqtt_publish_cpu_temp_sensor (self, sensor_name, sensor_value):
        if self.mqtt_status_reporting_enable:
            self.create_and_publish (
                message_cmd = "msg_sd_msg_cpu_sensor", 
                broad_cast = True,
                additional_params = {
                    "sensorName":  sensor_name,
                    "Temperature": sensor_value
                }
            )
#-------------------------------------------------------------------------------------------------
    def mqtt_publish_status_request (self, serial_number=None, broad_cast=None):
        self.create_and_publish (
            message_cmd = "msg_sd_get_status",
            serial_destination = serial_number,
            broad_cast = True if broad_cast is None or broad_cast == True else False
        )
#-------------------------------------------------------------------------------------------------
    # def mqtt_publish_sysinfo_request (self, serial_number=None, broad_cast=None):
    #     self.create_and_publish (
    #         message_cmd = "msg_sd_get_sysinfo", 
    #         serial_destination = serial_number,
    #         broad_cast = True if broad_cast is None or broad_cast == True else False
    #     )
#-------------------------------------------------------------------------------------------------
    def mqtt_publish_sysinfo_request (self, serial_number=None, broad_cast=None):
        self.create_and_publish (
            message_cmd = "msg_str_sysinfo_request",
            serial_destination = serial_number,
            broad_cast = True if broad_cast is None or broad_cast == True else False
        )
#--------------------------------------------------------------------------------------------------
    def mqtt_publish_config_file_request (self, serial_number=None, broad_cast=None):
        self.create_and_publish (
            message_cmd = "msg_sd_get_config_file", 
            serial_destination = serial_number,
            broad_cast = broad_cast
        )
#--------------------------------------------------------------------------------------------------
    def mqtt_publish_output_port_instruction (self, serial_number, output_port, on_off, timer_value):
        self.create_and_publish (
            message_cmd = "msg_str_output_on_off_instuction",
            serial_destination = serial_number,
            additional_params = {
                "onOff": on_off,
                "outputPort": output_port,
                "timerValue": timer_value
            }
        )
#--------------------------------------------------------------------------------------------------
    def mqtt_publish_clear_all_outputs_instruction (self, serial_number=None, broad_cast=None):
        self.create_and_publish (
            message_cmd = "msg_str_clear_all_outputs_instruction",
            serial_destination = serial_number,
            broad_cast = True if broad_cast is None or broad_cast == True else False
        )
#--------------------------------------------------------------------------------------------------
    def mqtt_publish_all_inputs_request (self, serial_number):
        self.create_and_publish (
            message_cmd = "msg_str_all_inputs_request",
            serial_destination = serial_number
        )
#--------------------------------------------------------------------------------------------------
    def mqtt_publish_hold_timers_request (self, serial_number):
        self.create_and_publish (
            message_cmd = "msg_str_hold_timers_request",
            serial_destination = serial_number
        )
#--------------------------------------------------------------------------------------------------
    def mqtt_publish_set_hold_timers_instruction (self, serial_number, new_values_dict):
        self.create_and_publish (
            message_cmd = "msg_str_set_hold_timers_instruction",
            serial_destination = serial_number,
            additional_params = {
                "holdTimerValues": new_values_dict
            }
        )
#--------------------------------------------------------------------------------------------------
    def mqtt_publish_controller_offline_alert (self, controller_sn, serial_number=None, broad_cast=None):
        self.create_and_publish (
            message_cmd = "msg_str_offline_alert",
            serial_destination = serial_number,
            broad_cast = True if broad_cast is None or broad_cast == True else False,
            additional_params = {
                "controllerSn": controller_sn,
                "controllerStatus": "Offline"
            }
        )
#--------------------------------------------------------------------------------------------------
    def mqtt_publish_controller_status (self, controller_sn, status, serial_number=None, broad_cast=None):
        self.create_and_publish (
            message_cmd = "msg_str_controller_status",
            serial_destination = serial_number,
            broad_cast = True if broad_cast is None or broad_cast == True else False,
            additional_params = {
                "controllerSn": controller_sn,
                "controllerStatus": status
            }
        )
#--------------------------------------------------------------------------------------------------
    # def mqtt_otp_response (self, card_number):
    #     self.create_and_publish (
    #         message_cmd = "msg_str_otp_response", 
    #         additional_params = {
    #             "cardNumber": card_number,
    #             "pinCode": self.insSecKey.otp_creator (card_number)
    #         }
    #     )
#--------------------------------------------------------------------------------------------------
    def xmqtt_publish_access_response(self, access_tuple: tuple):
        try:
            serial_number, full_name, found, pincode, pin_number, card_number, face_id, verif_ident = access_tuple

            self.insLogger.log_info(
                msg=f"[MqttBroker--mqtt_publish_access_response] Preparing to publish access result to serialNumber: {serial_number}"
            )

            self.create_and_publish(
                message_cmd="msg_str_user_record_response",
                serial_destination=serial_number,
                additional_params={
                    "granted":    found,
                    "faceId":     face_id,
                    "pinCode":    pincode,
                    "fullName":   full_name,
                    "pinNumber":  pin_number,
                    "cardNumber": card_number,
                    "verifIdent": verif_ident
                }
            )

            self.insLogger.log_info(
                msg=(
                    f"[MqttBroker--mqtt_publish_access_response] serialNumber: {serial_number}, fullName: {full_name}, "
                    f"cardNumber: {card_number}, faceId: {face_id}, pinNumber: {pin_number}, granted: {found}, verifIdent: {verif_ident}"
                )
            )

        except Exception as e:
            self.insLogger.log_error(
                msg=f"[MqttBroker--mqtt_publish_access_response ERROR] Failed to publish access response: {e}"
            )

#--------------------------------------------------------------------------------------------------
    def mqtt_publish_access_response(self, payload: AccessPayload):     # from a @dataclass on top
        try:
            self.insLogger.log_info(
                msg=f"[MqttBroker--mqtt_publish_access_response] Preparing to publish access result to serialNumber: {payload.serial_number}"
            )

            self.create_and_publish(
                message_cmd = "msg_str_user_record_response",
                objectId = payload.objectId,
                serial_destination=payload.serial_number,
                additional_params={
                    "granted":    payload.found,
                    "faceId":     payload.face_id,
                    "pinCode":    payload.pincode,
                    "fullName":   payload.full_name,
                    "pinNumber":  payload.pin_number,
                    "cardNumber": payload.card_number,
                    "verifIdent": payload.verif_ident
                }
            )

            self.insLogger.log_info(
                msg=(
                    f"[MqttBroker--mqtt_publish_access_response] "
                    f"objectId: {payload.objectId}, serialNumber: {payload.serial_number}, "
                    f"fullName: {payload.full_name}, cardNumber: {payload.card_number}, faceId: {payload.face_id}, "
                    f"pinNumber: {payload.pin_number}, granted: {payload.found}, verifIdent: {payload.verif_ident}"
                )
            )

        except Exception as e:
            self.insLogger.log_error(
                msg=f"[MqttBroker--mqtt_publish_access_response ERROR] Failed to publish access response: {e}"
            )

#--------------------------------------------------------------------------------------------------    