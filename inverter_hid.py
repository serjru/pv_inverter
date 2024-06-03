import os
import time
import paho.mqtt.client as mqtt
from utils import *


# Path to the HID device file
DEVICE_FILE = '/dev/hidraw0'

# Command to send (example from your research)
#COMMAND = b"QPI\xbe\xac\r"
QPIGS = b'\x51\x50\x49\x47\x53\xB7\xA9\x0d'
QPIRI = b'\x51\x50\x49\x52\x49\xF8\x54\x0D'
COMMAND = b"QPIRI\xF8\x54"
# See commands definitions in 
# https://forums.aeva.asn.au/uploads/293/HS_MS_MSX_RS232_Protocol_20140822_after_current_upgrade.pdf

# Open the HID device file
fd = open_device(DEVICE_FILE)
if fd is None:
    exit(1)

# Initialize the MQTT client
mqtt_client = mqtt.Client()
mqtt_client.connect("localhost", 1883, 60)

# Continuously read and process data
try:
    while True:
        send_command(fd, QPIGS)
        time.sleep(0.1)
        data = read_response(fd)
        if data and is_correct_output(data):
            #print(data)
            parsed_qpigs = parse_QPIGS(data)
            if parsed_qpigs:
                # Extract specific parameters
                load_w           = parsed_qpigs['load_w']
                battery_capacity = parsed_qpigs['battery_capacity']
                solar_power      = parsed_qpigs['solar_power']
                battery_current  = parsed_qpigs['battery_current']
                battery_voltage  = parsed_qpigs['battery_voltage']

                # Publish the specific parameters
                publish_data(mqtt_client, "homeassistant/inverter/load_w", load_w)
                publish_data(mqtt_client, "homeassistant/inverter/solar_power", solar_power)
                publish_data(mqtt_client, "homeassistant/inverter/battery_capacity", battery_capacity)
                publish_data(mqtt_client, "homeassistant/inverter/battery_voltage", battery_voltage)
                publish_data(mqtt_client, "homeassistant/inverter/battery_current", battery_current)
        time.sleep(2)  # Adjust sleep time as needed
finally:
    # Close the device file on exit
    os.close(fd)
