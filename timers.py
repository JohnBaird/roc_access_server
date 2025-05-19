# updated: 2025-05-05 15:15:22
# created: 2024-06-20 20:00:30
# filename: timers.py
#-----------------------------------------------------------------------------------------------------------------------------
from uuid import uuid4
from time import monotonic
from datetime import datetime, date
from csv_writer import TemperatureHeader        # from a @dataclass
#-----------------------------------------------------------------------------------------------------------------------------
class MasterTimers (object):
    def __init__ (
            self,
            name,
            constant_value
        ) -> None:
        
        self.name               = name
        self.constant_value     = constant_value 
        self.timer_value_count  = monotonic ()
        self.previous           = self.timer_value_count
#---------------------------------------------------------------------------------------------------  
class ServiceTimers (object):
    def __init__ (
            self,
            dtt,
            insLogger,
            insMQTTbroker,
            insMongoConfig,
            insMachineInfo,
            insCSVtemperature,
            util_prt = False,
            util_prt0 = False
        ) -> None:

        self.insLogger = insLogger
        self.insMQTTbroker = insMQTTbroker
        self.insMongoConfig = insMongoConfig
        self.insMachineInfo = insMachineInfo
        self.insCSVtemperature = insCSVtemperature

        hostname, ip_address = insMachineInfo.get_ip_address()
        self.own_hostname = hostname
        self.own_ip_address = ip_address
        self.own_serial_number = insMachineInfo.get_own_serial_number()

        self.util_prt = util_prt
        self.util_prt0 = util_prt0

        mqtt_settings_dict = insMongoConfig.query_config_mqtt_settings() # derived from mongo database
        self.mqtt_status_reporting_enable = mqtt_settings_dict.get("status_reporting_enable")

        general_settings_dict = insMongoConfig.query_config_general_settings() # derived from mongo database
        self.time_format = general_settings_dict.get("time_format")
        self.raspberry_pi = general_settings_dict.get("raspberry_pi")
        self.gen_datim_format = general_settings_dict.get("datim_format")
        self.sys_name = insMachineInfo.get_raspberry_pi_model () if self.raspberry_pi else insMachineInfo.get_cpu_information ()
        
        self.once_scan_and_execute_minute_0 = dtt.minute + 2
        self.once_scan_and_execute_minute_1 = dtt.minute + 2

        print (f"init dtt.minute={self.once_scan_and_execute_minute_0}") if self.util_prt0 else None
        print (f"init dtt.minute={self.once_scan_and_execute_minute_1}") if self.util_prt0 else None

        self.timer_constant_value_dict = {
            "MasterTimer_0 - 1 ms":   0.001,
            "MasterTimer_1 - 100 ms": 0.1,
            "MasterTimer_2 - 500 ms": 0.5,
            "MasterTimer_3 - 1 s":    1,
            "MasterTimer_4 - 30 s":   30,
            "MasterTimer_5 - 1 m":    60
        }

        print (f"master_timer_constant_value_dict={self.timer_constant_value_dict}") if self.util_prt0 else None

        # create master_timers instances
        self.master_timers = []
        for key, value in self.timer_constant_value_dict.items ():
            self.master_timers.append (
                MasterTimers (
                    name = key,  # eg. timer_name = "MasterTimer_0 - 1 ms"
                    constant_value = value
                )
            )

            print (f"{key}: {value}") if self.util_prt0 else None

        if self.util_prt0:
            print (f"time_format: {self.time_format}")
            print (f"raspberry_pi: {self.raspberry_pi}")
            print (f"gen_datim_format: {self.gen_datim_format}")
            print (f"int_master_timer_len={len(self.master_timers)}")
#-----------------------------------------------------------------------------------------------------------------------------
    def get_repeat_timer_counter_value (self, entry: str) -> int:
        for i, key in enumerate (self.repeat_timers_dict.keys()):
            if key == entry:
                print (f"repeat_timer_counters_list[{i}]: {self.repeat_timer_counters_list[i]}") if self.util_prt0 else None
                return self.repeat_timer_counters_list[i]
#-----------------------------------------------------------------
    def set_repeat_timer_counter_value (self, entry: str):
        for i, key in enumerate (self.repeat_timers_dict.keys()):
            if key == entry:
                self.repeat_timer_counters_list [i] = self.repeat_timers_dict[entry]
#-----------------------------------------------------------------                
    def convert_schedule_start_end_dict_to_epoch_tuple (self, schedule_start_end_dict):
        # Convert the dictionary to a list of tuples
        # From: schedule_start_end_dict: {'zone_1': '06:00, 06:15', 'zone_2': '06:15, 06:30'}
        # To:   schedule_start_end_tuple: (('06:00', '06:15'), ('06:15', '06:30'))
        schedule_start_end_list = []
        for value in schedule_start_end_dict.values():
            parts = value.split(',')
            if len(parts) == 2:
                start, end = parts
                schedule_start_end_list.append((start.strip(), end.strip()))
        # To:   epoch_times_tuples: ((1694512800, 1694513700), (1694513700, 1694514600))
        schedule_start_end_tuple = tuple(schedule_start_end_list)
        print (f"schedule_start_end_tuple: {schedule_start_end_tuple}") if self.util_prt0 else None
        epoch_times_list = []
        for start_time_str, end_time_str in schedule_start_end_tuple:
            start_epoch = self.time_to_epoch(None, start_time_str)
            end_epoch = self.time_to_epoch(None, end_time_str)
            epoch_times_list.append((start_epoch, end_epoch))
        print (f"epoch_times_list: {epoch_times_list}") if self.util_prt0 else None
        return tuple (epoch_times_list)
#-----------------------------------------------------------------------------------------------------------------------------
    def time_to_epoch (self, dtt: datetime, time_str: str) -> int:
        dtt = dtt if dtt is not None else datetime.now()
        # Parse the time string
        parsed_time = datetime.strptime(time_str, self.time_format).time()
        # Combine the current date with the parsed time
        combined_datetime = datetime.combine(dtt.date(), parsed_time)
        # Get the epoch time in seconds
        epoch_time = int(combined_datetime.timestamp())
        print (f"time_str={time_str}, epoch_time={epoch_time}") if self.util_prt0 else None
        return epoch_time
#-----------------------------------------------------------------------------------------------------------------------------
    def convert_epoch_times_tuples_to_start_end_boolen_tuple (self, dtt, epoch_times_tuples):
        # From: epoch_times_tuples=((1694491200, 1694491200), (1694491200, 1694491200))
        # To:   start_end_boolen_tuple=(True, True)
        dtt = dtt if dtt is not None else datetime.now()
        start_end_boolen_list = []
        for epoch_times in epoch_times_tuples:
            start_end_boolen_list.append(True) if self.is_current_time_between(dtt, epoch_times) else start_end_boolen_list.append(False)
        return tuple (start_end_boolen_list)
#-----------------------------------------------------------------------------------------------------------------------------
    def is_current_time (self, cts: int, time_seconds: int) -> bool:
        # cts = int(time.time() - time.mktime(datetime.date.today().timetuple()))      #cts current time seconds
        return int (cts) == time_seconds
#-----------------------------------------------------------------------------------------------------------------------------
    def is_current_time_between (self, dtt, epoch_times_tuple: tuple) -> bool:
        dtt = dtt if dtt is not None else datetime.now()
        current_time_epoch = self.current_time_to_epoch (dtt)
        epoch_start_time, epoch_end_time = epoch_times_tuple
        return epoch_start_time <= current_time_epoch < epoch_end_time
#-----------------------------------------------------------------------------------------------------------------------------
    def current_time_to_epoch (self, dtt: datetime) -> int:
        dtt = dtt if dtt is not None else datetime.now()
        # Get the current time in seconds since the epoch
        current_time_str = f"{dtt.strftime(self.time_format)}"
        return self.time_to_epoch (dtt, current_time_str)
#----------------------------------------------------------------------------------------------------------------------------
    def service_timer_ticks(self, dtt: datetime):
        dtt = dtt if dtt is not None else datetime.now()
        dtts = dtt.strftime(self.gen_datim_format)
        time_now = monotonic()

        for i, value in enumerate(self.timer_constant_value_dict.values()):
            if (time_now - self.master_timers[i].previous) > value:
                timer_ticks = (time_now - self.master_timers[i].previous) // value

                if i == 0:
                    pass  # MasterTimer_0 = 0.001 seconds

                elif i == 1:
                    pass  # MasterTimer_1 = 0.1 seconds

                elif i == 2:
                    # MasterTimer_2 = 0.5 seconds
                    if dtt.second <= 5 and dtt.minute ^ self.once_scan_and_execute_minute_0:
                        self.once_scan_and_execute_minute_0 = dtt.minute

                        if self.raspberry_pi:
                            sensor_value = self.insMachineInfo.get_cpu_temperature_pi()
                        else:
                            sensor_value = self.insMachineInfo.get_cpu_temperature_average()

                        # Creating an instance of TemperatureHeader
                        temperature_data = TemperatureHeader(       # from a @dataclass
                            _iD          = uuid4().hex[:24],
                            dateTime     = dtts,
                            serialSource = self.own_serial_number,
                            hostName     = self.own_hostname,
                            ipAddress    = self.own_ip_address,
                            sensorName   = 'CPU_temp',
                            tempValue    = sensor_value
                        )
                        self.insCSVtemperature.write_temperature_to_csv_file(temperature_data)

                        if self.mqtt_status_reporting_enable and sensor_value:
                            self.insMQTTbroker.mqtt_publish_cpu_temp_sensor(
                                sensor_name = self.sys_name,
                                sensor_value = sensor_value
                            )

                        log_message = (
                            f"[ServiceTimers--service_timer_ticks] server_cpu_sensor: "
                            f"serial_source={self.own_serial_number}, sensor_name={self.sys_name}, temperature={sensor_value}"
                        )
                        self.insLogger.log_info(msg=log_message)


                        if dtt.hour == 0 and dtt.minute == 0 and self.util_prt:
                            print("Every 1-Hour")

                        if dtt.minute % 5 == 0 and self.util_prt:
                            print(f"{dtts}: {self.master_timers[i].name}, Every 5-minutes")

                    if 5 < dtt.second <= 10 and dtt.minute ^ self.once_scan_and_execute_minute_1:
                        self.once_scan_and_execute_minute_1 = dtt.minute

                elif i == 3:
                    # MasterTimer_3 = 1 second
                    if self.util_prt0:
                        print(f"{i}: {self.master_timers[i].name}, Every second")

                elif i == 4:
                    # MasterTimer_4 = 30 seconds
                    if self.util_prt0:
                        print(f"{i}: {self.master_timers[i].name}, Every 30-seconds")

                elif i == 5:
                    # MasterTimer_5 = 60 seconds
                    if self.util_prt0:
                        print(f"{dtts}: {self.master_timers[i].name}, Every 1-minute")
                    if self.mqtt_status_reporting_enable:
                        self.insMQTTbroker.mqtt_publish_status_request()

                elif i >= 6:
                    pass  # Invalid Timer Index

                self.master_timers[i].previous += timer_ticks * value

#-----------------------------------------------------------------------------------------------------------------------------
