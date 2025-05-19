# updated: 2025-05-06 18:09:31
# created: 2024-07-21 13:51:09
# filename: machine_info.py
#--------------------------------------------------------------------------------------------------------------
from os import path
from time import sleep
from random import getrandbits
from uuid import UUID, getnode, uuid4
from subprocess import check_output, CalledProcessError
from socket import socket, gethostname, AF_INET, SOCK_DGRAM
#--------------------------------------------------------------------------------------------------------------
class MachineInfo (object):
    MAC_ADDRESS_FILE = "config/mac_address.txt"
    def __init__ (
            self,
            insLogger,
            program_version = None,
            program_updated = None,
            number_format = "DEC",
            util_prt = False,
            util_prt0 = False
        )-> None:

        self.util_prt = util_prt                # printing flag True.
        self.util_prt0 = util_prt0              # printing flag True.
        self.insLogger = insLogger
        self.program_version = program_version
        self.program_updated = program_updated
        self.number_format = number_format
        self.own_serial_number_msg = self.get_own_serial_number_msg ()
#--------------------------------------------------------------
    def get_mac_address(self):
        try:
            mac = ''.join(['{:02x}'.format((getnode() >> elements) & 0xff) for elements in range(0, 2*6, 2)][::-1])
            self.insLogger.log_info(msg=f"[MachineInfo] MAC address retrieved: {mac}")
            return mac
        except Exception as e:
            self.insLogger.log_error(msg=f"[MachineInfo ERROR] Failed to get MAC address: {str(e)}")
            return None
#--------------------------------------------------------------
    def get_unique_client_id(self):
        try:
            mac_hex = uuid4().hex[:12]  # Generate a random MAC-like hex string
            mac_dec = str(int(mac_hex, 16))  # Convert to decimal
            random_number = getrandbits(16)  # Generate random 16-bit number
            client_id = f'{mac_dec}{random_number}'  # Concatenate

            self.insLogger.log_info(msg=f"[MachineInfo] Unique client ID generated: {client_id}")
            return client_id

        except Exception as e:
            self.insLogger.log_error(msg=f"[MachineInfo ERROR] Failed to generate unique client ID: {str(e)}")
            return None
#--------------------------------------------------------------
    def get_own_serial_number(self):
        try:
            if path.exists(self.MAC_ADDRESS_FILE) and path.getsize(self.MAC_ADDRESS_FILE) > 0:
                with open(self.MAC_ADDRESS_FILE, 'r') as f:
                    mac_address = f.read().strip()
                    self.insLogger.log_info(msg=f"[MachineInfo] MAC address loaded from file: {mac_address}")
            else:
                mac_address = hex(getnode())[2:]

                if self.number_format.upper() == "HEX":
                    mac_address = mac_address.zfill(12)
                elif self.number_format.upper() == "DEC":
                    mac_address = str(int(mac_address, 16))

                with open(self.MAC_ADDRESS_FILE, 'w') as f:
                    f.write(mac_address)

                self.insLogger.log_info(msg=f"[MachineInfo] MAC address generated and written to file: {mac_address}")

            return mac_address

        except Exception as e:
            self.insLogger.log_error(msg=f"[MachineInfo ERROR] Failed to get serial number: {str(e)}")
            return None
#--------------------------------------------------------------
    def get_own_serial_number_msg (self):
        own_serial_number = self.get_own_serial_number ()
        return f"s/n:{own_serial_number}"
#--------------------------------------------------------------
    def get_client_id(self):
        try:
            unique_id_bytes = uuid4().bytes
            client_id = str(UUID(bytes=unique_id_bytes).hex)
            self.insLogger.log_info(msg=f"[MachineInfo] Client ID generated: {client_id}")
            return client_id
        except Exception as e:
            self.insLogger.log_error(msg=f"[MachineInfo ERROR] Failed to generate client ID: {str(e)}")
            return None
#--------------------------------------------------------------
    def get_cpu_temperature(self):
        try:
            output = check_output("vcgencmd measure_temp", shell=True).decode()
            match = search(r"temp=([\d\.]+)'C", output)
            if match:
                temperature = float(match.group(1))
                self.insLogger.log_info(msg=f"[MachineInfo] CPU Temperature retrieved: {temperature}°C")
                return temperature
            else:
                self.insLogger.log_error(msg="[MachineInfo ERROR] Temperature pattern not found in vcgencmd output.")
                return None
        except FileNotFoundError:
            self.insLogger.log_info(msg="[MachineInfo] vcgencmd not available. This command is specific to Raspberry Pi.")
            return None
        except CalledProcessError as e:
            self.insLogger.log_error(msg=f"[MachineInfo ERROR] Command failed: {e}")
            return None
        except Exception as e:
            self.insLogger.log_error(msg=f"[MachineInfo ERROR] Unexpected error: {str(e)}")
            return None

#--------------------------------------------------------------------------------------------------------------
    def get_cpu_temperature_pi(self):
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp_str = f.read().strip()
                temperature = float(temp_str) / 1000  # Convert from millidegree to degree
                temperature = round(temperature, 2)
                self.insLogger.log_info(msg=f"[MachineInfo] CPU Temperature (Raspberry Pi 4/5): {temperature:.2f}°C")
                return temperature
        except FileNotFoundError:
            self.insLogger.log_error(msg="[MachineInfo ERROR] Temperature file not found: /sys/class/thermal/thermal_zone0/temp")
            return None
        except Exception as e:
            self.insLogger.log_error(msg=f"[MachineInfo ERROR] Failed to read Pi4/Pi5 CPU temperature: {str(e)}")
            return None

#--------------------------------------------------------------
    def get_cpu_information(self):

        def get_cpu_info():
            cpu_info = {}
            try:
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if ":" in line:
                            key, value = [x.strip() for x in line.split(":", 1)]
                            if key not in cpu_info:  # first occurrence only
                                cpu_info[key] = value
                return cpu_info
            except Exception as e:
                self.insLogger.log_error(msg=f"[MachineInfo--get_cpu_info] Failed to read /proc/cpuinfo: {str(e)}")
                return {}

        info = get_cpu_info()
        try:
            model_name = info.get("model name")
            cpu_cores = info.get("cpu cores")
            vendor_id = info.get("vendor_id")
            return model_name
            # return {
            #     "model_name": model_name,
            #     "cpu_cores": cpu_cores,
            #     "vendor_id": vendor_id
            # }
        except Exception as e:
            self.insLogger.log_error(msg=f"[MachineInfo--get_cpu_information] Failed to extract CPU fields: {str(e)}")
            return "Unknown"

#--------------------------------------------------------------
    def get_cpu_temperature_average(self):
        import psutil
        core_temps = []
        try:
            sensors = psutil.sensors_temperatures()
            for name, entries in sensors.items():
                for entry in entries:
                    core_temps.append(entry.current)
            
            if core_temps:
                average_temp = round(sum(core_temps) / len(core_temps), 2)
                self.insLogger.log_info(msg=f"[MachineInfo -- get_cpu_temperature_average] Average CPU temperature: {average_temp:.2f}°C")
                return average_temp

            else:
                self.insLogger.log_error(msg="[MachineInfo -- get_cpu_temperature_average ERROR] No valid temperature readings found (Tctl/Tdie missing).")
                return None

        except Exception as e:
            self.insLogger.log_error(msg=f"[MachineInfo -- get_cpu_temperature_average ERROR] Failed to read CPU temperature: {str(e)}")
            return None
#--------------------------------------------------------------
    def get_ip_address(self, retries=5, delay=2):
        hostname = gethostname()
        ip_address = None

        for attempt in range(retries):
            sock = socket(AF_INET, SOCK_DGRAM)
            try:
                # Use a dummy address; it doesn't have to be reachable.
                sock.connect(("8.8.8.8", 80))
                ip_address = sock.getsockname()[0]
                self.insLogger.log_info(msg=f"[MachineInfo] Hostname: {hostname}, IP Address: {ip_address}")
                break  # Success
            except OSError as e:
                if e.errno == 101:  # Network unreachable
                    if attempt < retries - 1:
                        sleep(delay)
                    else:
                        self.insLogger.log_error(msg=f"[MachineInfo ERROR] Network unreachable after {retries} retries.")
                        return hostname, None
                else:
                    self.insLogger.log_error(msg=f"[MachineInfo ERROR] Unexpected socket error: {str(e)}")
                    return hostname, None
            finally:
                sock.close()

        return hostname, ip_address
#--------------------------------------------------------------
    def get_raspberry_pi_model(self):
        try:
            cpuinfo = check_output("cat /proc/cpuinfo", shell=True).decode()

            for line in cpuinfo.split('\n'):
                if "Model" in line:
                    model_info = line.split(':')[1].strip()
                    self.insLogger.log_info(msg=f"[MachineInfo] Raspberry Pi model detected: {model_info}")
                    return model_info

            self.insLogger.log_error(msg="[MachineInfo ERROR] Model information not found in /proc/cpuinfo.")
            return None

        except CalledProcessError as e:
            self.insLogger.log_error(msg=f"[MachineInfo ERROR] Failed to execute command to get model: {e}")
            return None
        except Exception as e:
            self.insLogger.log_error(msg=f"[MachineInfo ERROR] Unexpected error while getting model: {str(e)}")
            return None
#--------------------------------------------------------------
    def run_machine_info_methods(self):
        method_names = [
            "get_client_id",
            "get_ip_address",
            "get_mac_address",
            "get_cpu_temperature",
            "get_cpu_information",
            "get_unique_client_id",
            "get_own_serial_number",
            "get_raspberry_pi_model",
            "get_cpu_temperature_pi",
            "get_cpu_temperature_average"
        ]

        for name in method_names:
            try:
                method = getattr(self, name)  # <-- use self, not self.insMachineInfo
                result = method()
                # self.insLogger.log_info(msg=f"[MachineInfo] {name} -> {result}")
            except AttributeError:
                self.insLogger.log_error(msg=f"[MachineInfo ERROR] Method not found: {name}")
            except Exception as e:
                self.insLogger.log_error(msg=f"[MachineInfo ERROR] Failed to execute {name}: {str(e)}")

#--------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    # Example usage   
    insMachineInfo = MachineInfo ()

    serial_number = insMachineInfo.get_own_serial_number ()
    mac_address = insMachineInfo.get_mac_address ()

    print (f"Serial Number: {serial_number}, type: {type(serial_number)}")
    print (f"MAC_address: {mac_address}, type: {type(mac_address)}")
#--------------------------------------------------------------------------------------------------------------