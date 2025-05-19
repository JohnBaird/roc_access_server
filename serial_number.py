# updated: 2025-05-07 19:47:27
# filename: serial_number.py
# created: 2024-06-23 13:30:00
# file_name: serial_number.py
#-----------------------------------------------------------------------------------------------------------------------------
from uuid import UUID, getnode, uuid4
from random import getrandbits
#-----------------------------------------------------------------------------------------------------------------------------
class SerialNumber (object):
    def __init__(
        self, 
        util_prt = True,
        util_prt0 = False,
        number_format = "dec"
    )-> None:

        self.util_prt  = util_prt
        self.util_prt0 = util_prt0
        self.number_format = number_format
#--------------------------------------------------------------
    def get_mac_address(self):
        return ''.join(['{:02x}'.format((getnode() >> elements) & 0xff) for elements in range(0, 2*6, 2)][::-1])
#--------------------------------------------------------------
    def get_unique_client_id (self):
        mac_hex = uuid4().hex[:12]                              # Generate a random MAC address-like string
        mac_dec = str(int(mac_hex, 16))                         # Convert the MAC address hex string to decimal
        random_number = getrandbits(16)                         # Generate a random 16-bit number
        return f'{mac_dec}{random_number}'                      # Concatenates the MAC address and the random number
#--------------------------------------------------------------
    def get_own_serial_number (self):                           # Currently the serial number for HP Server:  115489332715634
        mac_address = hex(getnode())[2:]                        # Get the MAC address and convert it to hexadecimal
        if self.number_format.upper() == "HEX":
            serial_number = mac_address.zfill(12)               # Ensure the MAC address is 12 characters long
            
        elif self.number_format.upper() == "DEC":    
            serial_number = str(int(mac_address, 16))           # Convert the hexadecimal to decimal
        
        print (f"Calculated Serial Number: {serial_number}") if self.util_prt0 else None
        
        # return serial_number
        return "217588503471049"
#--------------------------------------------------------------
    def get_client_id (self):
        # Get a unique identifier as bytes
        unique_id_bytes = uuid4().bytes
        # Convert the bytes to a hexadecimal representation
        return str(UUID(bytes=unique_id_bytes).hex)
#--------------------------------------------------------------
if __name__ == "__main__":
    print (f"Test Program for serial_number.py")

    import json
    
    insSerialDec = SerialNumber ()

    mac_address = insSerialDec.get_mac_address ()
    print (f"MAC-Address: {mac_address}")

    serial_number = insSerialDec.get_own_serial_number ()
    print (f"Serial Number: {serial_number}")
#--------------------------------------------------------------
