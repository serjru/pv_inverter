import os
import time
import paho.mqtt.client as mqtt
# import logging
from utils import *

# Set up logging configuration
# Directory where logs will be written
#log_directory = "/logs"
#os.makedirs(log_directory, exist_ok=True)

#logging.basicConfig(
#    level=logging.DEBUG,  # Set the logging level to DEBUG for detailed logs
#    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#    handlers=[
#        logging.FileHandler(os.path.join(log_directory, "inverter.log")),  # Log to a file in /logs
#        logging.StreamHandler()  # Also log to the console
#    ]
#)

# Get a logger for this module
#logger = logging.getLogger(__name__)

DEVICE_FILE = find_inverter_device()
if DEVICE_FILE is None:
    print("Inverter device not found. Exiting.")
    exit(1)

# MQTT configuration
MQTT_BROKER             = "localhost"
MQTT_PORT               = 1883
MQTT_KEEPALIVE          = 60
MQTT_TOPIC_COMMAND      = "homeassistant/inverter/set_mode"
MQTT_TOPIC_DESIRED_MODE = "homeassistant/inverter/desired_mode"
MQTT_TOPIC_ACTUAL_MODE  = "homeassistant/inverter/actual_mode"

# Command to send (example from research)
QPIGS           = b'\x51\x50\x49\x47\x53\xB7\xA9\x0d' # General status inquiry
QPIRI           = b'\x51\x50\x49\x52\x49\xF8\x54\x0D'
QMOD            = b'\x51\x4D\x4F\x44\x49\xC1\x0d'     # Device mode inquiry
COMMAND_BATTERY = b'\x50\x4F\x50\x30\x32\xE2\x0B\x0D' # Set mode to SBU (Battery)
COMMAND_LINE    = b'\x50\x4F\x50\x30\x30\xC2\x48\x0D' # Set mode to SUB (Line)
# See commands definitions in 
# https://forums.aeva.asn.au/uploads/293/HS_MS_MSX_RS232_Protocol_20140822_after_current_upgrade.pdf

# Open the HID device file
fd = open_device(DEVICE_FILE)
if fd is None:
#    logger.error(f"Failed to open HID device file. Exiting")
    exit(1)
close_device(fd)

# Initialize the MQTT client
mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
#        logger.info("Connected to MQTT broker")
        client.subscribe(MQTT_TOPIC_COMMAND)
    else:
        logger.error(f"Failed to connect to MQTT broker. Return code: {rc}")

def on_message(client, userdata, msg):
#    logger.info(f"Received message: {msg.topic} {msg.payload.decode()}")
    fd = open_device(DEVICE_FILE)
#    logger.debug(f"Openinig HID device file {DEVICE_FILE}")
    if fd is not None:
#        logger.debug("HID device file opened successfully")
        desired_mode = msg.payload.decode()
        if desired_mode == "L":
            send_command(fd, COMMAND_LINE)
            client.publish(MQTT_TOPIC_DESIRED_MODE, "L")
        elif desired_mode == "B":
            send_command(fd, COMMAND_BATTERY)
            client.publish(MQTT_TOPIC_DESIRED_MODE, "B")
        close_device(fd)
#    else:
#        logger.error("Failed to open device")

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

# Continuously read and process data
try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
    mqtt_client.loop_start()

    # Main loop to monitor actual mode
    while True:

        # Command 1. General status inquiry
        fd = open_device(DEVICE_FILE)
        if fd is None:
#            logger.error(f"Failed to open HID device file. Exiting")
            exit(1)
        send_command(fd, QPIGS) # General Status inquiry
        time.sleep(1)
        data = read_response(fd)
        if data and is_correct_output(data):
            parsed_qpigs = parse_QPIGS(data)
            if parsed_qpigs:
                # Extract specific parameters
                load_w           = parsed_qpigs['load_w']
                battery_capacity = parsed_qpigs['battery_capacity']
                solar_power      = parsed_qpigs['solar_power']
                battery_current  = parsed_qpigs['battery_current']
                battery_voltage  = parsed_qpigs['battery_voltage']
                battery_charge_current    = parsed_qpigs['battery_charge_current']
                battery_discharge_current = parsed_qpigs['battery_discharge_current']

                # Publish the specific parameters
                publish_data(mqtt_client, "homeassistant/inverter/load_w", load_w)
                publish_data(mqtt_client, "homeassistant/inverter/solar_power", solar_power)
                publish_data(mqtt_client, "homeassistant/inverter/battery_capacity", battery_capacity)
                publish_data(mqtt_client, "homeassistant/inverter/battery_voltage", battery_voltage)
                publish_data(mqtt_client, "homeassistant/inverter/battery_current", battery_current)
                publish_data(mqtt_client, "homeassistant/inverter/battery_charge_current", battery_charge_current)
                publish_data(mqtt_client, "homeassistant/inverter/battery_discharge_current", battery_discharge_current)
        close_device(fd)

        # Pause between commands
        time.sleep(3)

        # Command 2. Mode inquiry
        fd = open_device(DEVICE_FILE)
        if fd is None:
            exit(1)
        send_command(fd, QMOD) # Mode inquiry
        time.sleep(1)
        inverter_mode = read_qmod(fd)
        if inverter_mode:
            publish_data(mqtt_client, "homeassistant/inverter/mode", inverter_mode) # Remove this line when HA config changes to remove this parameter.
            publish_data(mqtt_client, MQTT_TOPIC_ACTUAL_MODE, inverter_mode)
        close_device(fd)

        time.sleep(3)  # Interval between data updates

except Exception as e:
    print(f"Unhandled exception: {e}", exc_info=True)
#    logger.critical(f"Unhandled exception: {e}", exc_info=True)
finally:
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
#    logger.info("Script terminated")
    # Close the device file on exit
    os.close(fd)
