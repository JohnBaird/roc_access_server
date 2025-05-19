# updated: 2025-04-25 20:38:24
# created: 2024-08-21 15:13:04
# filename: config_update.py
#--------------------------------------------------------------------------------------------------------------
from json import load, dump
#--------------------------------------------------------------------------------------------------------------
class ConfigUpdate (object):
    def __init__(
            self, 
            insMachineInfo,
            filename
        ) -> None:
        
        self.insMachineInfo = insMachineInfo
        self.filename = filename
        self.update_json_config ()
        self.updated = True  # Initialize the updated flag
#--------------------------------------------------------------------------------------------------------------
    def update_json_file (self, section, key_to_update, new_value):
        # Load the JSON config_data from the file
        with open(self.filename, 'r') as file:
            config_data = load(file)

        # Update the key with the new value if it's different from the current value
        def update_key_value(config_data, section, key, value):
            if section in config_data and isinstance(config_data[section], dict):
                if key in config_data[section]:
                    if config_data[section][key] != value:
                        config_data[section][key] = value
                        self.updated = True  # Mark as updated
                    else:
                        self.updated = False # No need to update
                else:
                    # If the key doesn't exist, add it
                    config_data[section][key] = value
                    self.updated = True  # Mark as updated
            else:
                # If the section doesn't exist, create it with the key-value pair
                config_data[section] = {key: value}
                self.updated = True  # Mark as updated

        update_key_value(config_data, section, key_to_update, new_value)

        # Write the updated JSON config_data back to the file only if an update was made
        if self.updated:
            with open(self.filename, 'w') as file:
                dump(config_data, file, indent=4)
#--------------------------------------------------------------------------------------------------------------
    def update_json_config (
            self,
            section = f"system_information"
        ):

        hostname, ip_address = self.insMachineInfo.get_ip_address()
        self.update_json_file (
            section = section, 
            key_to_update = "hostname", 
            new_value = hostname
        )
        
        self.update_json_file (
            section = section, 
            key_to_update = "ip_address", 
            new_value = ip_address
        )
        
        self.update_json_file (
            section = section, 
            key_to_update = "serial_number", 
            new_value = self.insMachineInfo.get_own_serial_number()
        )

        self.update_json_file (
            section = section, 
            key_to_update = "program_version", 
            new_value = self.insMachineInfo.program_version
        )
        
        self.update_json_file (
            section = section, 
            key_to_update = "program_updated", 
            new_value = self.insMachineInfo.program_updated
        )

#--------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    print (f"Test Program for config_update.py")

    insConfigUpdate = ConfigUpdate (
        insMachineInfo = None,
        filename = "config_schema.json"
    )
    insConfigUpdate.update_json_file ()
#--------------------------------------------------------------------------------------------------------------