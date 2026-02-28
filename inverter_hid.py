import os
import time
import logging
from logging.handlers import RotatingFileHandler
import paho.mqtt.client as mqtt
from utils import (
    find_inverter_device, open_device, close_device,
    send_command, read_response, read_qmod,
    publish_data, is_correct_output, parse_QPIGS,
)

# Set up logging with rotation to prevent disk space exhaustion
log_directory = "/logs"
os.makedirs(log_directory, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            os.path.join(log_directory, "inverter.log"),
            maxBytes=5*1024*1024,  # 5 MB per file
            backupCount=2
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DEVICE_FILE = find_inverter_device()
if DEVICE_FILE is None:
    logger.critical("Inverter device not found. Exiting.")
    exit(1)
logger.info(f"Found inverter device: {DEVICE_FILE}")

# MQTT configuration (overridable via environment variables)
MQTT_BROKER             = os.environ.get("MQTT_BROKER", "localhost")
MQTT_PORT               = int(os.environ.get("MQTT_PORT", "1883"))
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

class InverterConnection:
    def __init__(self, device_file):
        self.device_file = device_file
        self.fd = None

    def __enter__(self):
        self.fd = open_device(self.device_file)
        return self.fd

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.fd is not None:
            close_device(self.fd)

def handle_inverter_command(device_file, command, read_func=read_response):
    with InverterConnection(device_file) as fd:
        if fd is None:
            logger.error("Failed to open HID device file")
            return None
        send_command(fd, command)
        time.sleep(1)
        return read_func(fd)

# Initialize the MQTT client with v2 callback API
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        logger.error(f"Failed to connect to MQTT broker: {reason_code}")
    else:
        logger.info("Connected to MQTT broker")
        client.subscribe(MQTT_TOPIC_COMMAND)

def on_message(client, userdata, msg):
    try:
        desired_mode = msg.payload.decode()
        logger.info(f"Received mode change command: {desired_mode}")
        with InverterConnection(DEVICE_FILE) as fd:
            if fd is None:
                logger.error("Failed to open HID device for mode change")
                return
            if desired_mode == "L":
                send_command(fd, COMMAND_LINE)
                client.publish(MQTT_TOPIC_DESIRED_MODE, "L")
                logger.info("Mode set to Line")
            elif desired_mode == "B":
                send_command(fd, COMMAND_BATTERY)
                client.publish(MQTT_TOPIC_DESIRED_MODE, "B")
                logger.info("Mode set to Battery")
            else:
                logger.warning(f"Unknown mode command: {desired_mode}")
    except Exception as e:
        logger.error(f"Error handling mode change command: {e}")

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

# Continuously read and process data
try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
    mqtt_client.loop_start()

    consecutive_errors = 0
    MAX_CONSECUTIVE_ERRORS = 10

    while True:
        # Command 1: General status inquiry
        try:
            data = handle_inverter_command(DEVICE_FILE, QPIGS)
            if data and is_correct_output(data):
                parsed_qpigs = parse_QPIGS(data)
                if parsed_qpigs:
                    for key, value in parsed_qpigs.items():
                        if key.startswith('unknown'):
                            continue
                        publish_data(mqtt_client, f"homeassistant/inverter/{key}", value)
                    consecutive_errors = 0
            else:
                consecutive_errors += 1
                logger.warning(f"QPIGS: no valid data (attempt {consecutive_errors})")
        except Exception as e:
            consecutive_errors += 1
            logger.error(f"Error in QPIGS cycle ({consecutive_errors}): {e}")

        time.sleep(3)

        # Command 2: Mode inquiry
        try:
            inverter_mode = handle_inverter_command(DEVICE_FILE, QMOD, read_qmod)
            if inverter_mode:
                publish_data(mqtt_client, "homeassistant/inverter/mode", inverter_mode)
                publish_data(mqtt_client, MQTT_TOPIC_ACTUAL_MODE, inverter_mode)
                consecutive_errors = 0
            else:
                consecutive_errors += 1
                logger.warning(f"QMOD: no valid data (attempt {consecutive_errors})")
        except Exception as e:
            consecutive_errors += 1
            logger.error(f"Error in QMOD cycle ({consecutive_errors}): {e}")

        # If too many consecutive errors, re-detect device and reset
        if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
            logger.critical(f"Too many consecutive errors ({consecutive_errors}), exiting for container restart")
            break

        time.sleep(3)

except Exception as e:
    logger.critical(f"Unhandled exception: {e}", exc_info=True)
finally:
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    logger.info("Script terminated")
