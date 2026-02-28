import os
import time
import logging
import threading
from logging.handlers import RotatingFileHandler
import paho.mqtt.client as mqtt
from utils import (
    find_inverter_device, open_device, close_device,
    send_command, read_response, read_qmod,
    publish_data, is_correct_output, parse_QPIGS,
    flush_device,
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
MQTT_TOPIC_AVAILABILITY = "homeassistant/inverter/availability"

# Polling configuration (overridable via environment variables)
POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL", "1.0"))  # seconds between cycles

# Command bytes (see protocol spec)
# https://forums.aeva.asn.au/uploads/293/HS_MS_MSX_RS232_Protocol_20140822_after_current_upgrade.pdf
QPIGS           = b'\x51\x50\x49\x47\x53\xB7\xA9\x0d' # General status inquiry
QPIRI           = b'\x51\x50\x49\x52\x49\xF8\x54\x0D'
QMOD            = b'\x51\x4D\x4F\x44\x49\xC1\x0d'     # Device mode inquiry
COMMAND_BATTERY = b'\x50\x4F\x50\x30\x32\xE2\x0B\x0D' # Set mode to SBU (Battery)
COMMAND_LINE    = b'\x50\x4F\x50\x30\x30\xC2\x48\x0D' # Set mode to SUB (Line)

# Thread lock for serializing HID device access between main loop and MQTT callback
device_lock = threading.Lock()

# Persistent file descriptor for HID device
device_fd = None

def ensure_device_open():
    """Open the device if not already open. Returns fd or None."""
    global device_fd
    if device_fd is not None:
        return device_fd
    device_fd = open_device(DEVICE_FILE)
    if device_fd is not None:
        logger.info(f"Opened HID device: {DEVICE_FILE}")
    return device_fd

def close_device_fd():
    """Close the persistent device fd."""
    global device_fd
    if device_fd is not None:
        close_device(device_fd)
        device_fd = None

def reopen_device():
    """Close and reopen the device (for recovery after errors)."""
    close_device_fd()
    time.sleep(0.1)
    return ensure_device_open()

def send_and_read(command, read_func=read_response):
    """Send a command and read the response using the persistent fd.
    Must be called while holding device_lock."""
    fd = ensure_device_open()
    if fd is None:
        logger.error("Failed to open HID device")
        return None
    flush_device(fd)
    send_command(fd, command)
    response = read_func(fd)
    if response is None:
        # First retry: just flush and resend (device fd is likely fine)
        logger.debug("First read failed, flushing and retrying")
        flush_device(fd)
        send_command(fd, command)
        response = read_func(fd)
    if response is None:
        # Second retry: reopen the device (fd may be broken)
        logger.warning("Second read failed, reopening device")
        fd = reopen_device()
        if fd is None:
            return None
        send_command(fd, command)
        response = read_func(fd)
    return response

# Initialize the MQTT client with v2 callback API
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.will_set(MQTT_TOPIC_AVAILABILITY, "offline", retain=True)

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        logger.error(f"Failed to connect to MQTT broker: {reason_code}")
    else:
        logger.info("Connected to MQTT broker")
        client.subscribe(MQTT_TOPIC_COMMAND)
        client.publish(MQTT_TOPIC_AVAILABILITY, "online", retain=True)

def on_message(client, userdata, msg):
    try:
        desired_mode = msg.payload.decode()
        logger.info(f"Received mode change command: {desired_mode}")
        with device_lock:
            fd = ensure_device_open()
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

    logger.info(f"Starting poll loop (interval={POLL_INTERVAL}s)")

    while True:
        with device_lock:
            # Command 1: General status inquiry
            try:
                data = send_and_read(QPIGS)
                if data and is_correct_output(data):
                    parsed_qpigs = parse_QPIGS(data)
                    if parsed_qpigs:
                        for key, value in parsed_qpigs.items():
                            publish_data(mqtt_client, f"homeassistant/inverter/{key}", value)
                        consecutive_errors = 0
                else:
                    consecutive_errors += 1
                    if data is None:
                        logger.warning(f"QPIGS: read timeout (attempt {consecutive_errors})")
                    else:
                        logger.warning(f"QPIGS: invalid response [{len(data)}B] (attempt {consecutive_errors})")
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Error in QPIGS cycle ({consecutive_errors}): {e}")

            # Command 2: Mode inquiry (back-to-back, no gap needed)
            try:
                inverter_mode = send_and_read(QMOD, read_qmod)
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

        # If too many consecutive errors, try reopening device
        if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
            logger.critical(f"Too many consecutive errors ({consecutive_errors}), exiting for container restart")
            break

        time.sleep(POLL_INTERVAL)

except Exception as e:
    logger.critical(f"Unhandled exception: {e}", exc_info=True)
finally:
    mqtt_client.publish(MQTT_TOPIC_AVAILABILITY, "offline", retain=True)
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    close_device_fd()
    logger.info("Script terminated")
