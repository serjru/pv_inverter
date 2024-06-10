import os
import time
import paho.mqtt.client as mqtt

QPIGS = b'\x51\x50\x49\x47\x53\xB7\xA9\x0d' # General status inquiry


def open_device(device_file):
    """Open the HID device file."""
    try:
        fd = os.open(device_file, os.O_RDWR | os.O_NONBLOCK)
        return fd
    except OSError as e:
        print(f"Unable to open the device file: {e}")
        return None

def close_device(fd):
    try:
        os.close(fd)
    except OSError as e:
        print(f"Error closing device file: {e}")

def send_command(fd, command):
    """Send a command to the HID device."""
    try:
        os.write(fd, command)
        #print(f"Sent command: {command}")
    except OSError as e:
        print(f"Error sending command: {e}")

def read_response(fd):
    # Only use for QPIGS response read!
    # Read the response from the HID device.
    try:
        response = os.read(fd, 8).decode('utf-8', errors='ignore')  # Attempt to read up to 8 bytes
        while '\r' not in response:
            time.sleep(0.1)
            response = response + os.read(fd, 8).decode('utf-8', errors='ignore')
        if response:
            return response
    except OSError as e:
        if e.errno == 11:
            print("Error 11, device not ready")
            #send_command(fd, QPIGS)  # Send a new request
            time.sleep(0.1)  # Sleep briefly and try again
        else:
            print(f"Error reading data: {e}")
    return None

def read_qmod(fd):
    # Read the response from the HID device after QMOD command.
    try:
        response = os.read(fd, 3).decode('utf-8', errors='ignore')  # Attempt to read up to 3 bytes
        # Define the valid letters
        valid_letters = {'P', 'S', 'L', 'B', 'F', 'H'}
        # Check if the string has the correct format
        if response[0] == '(':
            letter = response[1]
            if letter in valid_letters:
                return letter
        return None
        #if response:
        #    print("Debug. Returning QMOD response")
        #    return response
    except OSError as e:
        if e.errno == 11:
            #send_command(fd, QMOD)  # Send a new request
            time.sleep(0.1)  # Sleep briefly and try again
        else:
            print(f"Error reading data: {e}")
    return None

def publish_data(mqtt_client, topic, data):
    # Publish data to the MQTT broker.
    mqtt_client.publish(topic, data)
    #print(f"Published data to {topic}: {data}")

def is_correct_output(data):
    # Check if the data follows the expected correct format.
    if data.startswith('('):
        # Remove the start and end characters for further validation
        stripped_data = data[1:-3].strip()
        # Split the data into parameters
        parameters = stripped_data.split()
        
        # Check if the number of parameters matches the expected count
        expected_parameter_count = 21  # Adjust this based on actual data
        #print(len(parameters))
        if len(parameters) == expected_parameter_count:
            # Further checks can be added here if needed
            return True
    return False

def parse_QPIGS(data):
    # Parse the raw data into structured parameter values.
    try:
        # Remove the start '(' and end '\r\x00\x00' characters
        stripped_data = data[1:-3].strip()
        # Split the data into parameters
        parameters = stripped_data.split()
        
        # Ensure there are exactly 21 parameters
        if len(parameters) != 21:
            raise ValueError("Unexpected number of parameters")
        
        # Convert parameters to appropriate types and handle errors
        parsed_values = {
            'utility_voltage': round(float(parameters[0]), 2),
            'utility_frequency': round(float(parameters[1]), 2),
            'output_voltage': round(float(parameters[2]), 2),
            'output_frequency': round(float(parameters[3]), 2),
            'load_va': int(parameters[4]),
            'load_w': int(parameters[5]),
            'load_percent': int(parameters[6]),
            'bus_voltage': round(float(parameters[7]), 2),
            'battery_voltage': round(float(parameters[8]), 2),
            'battery_charge_current': int(parameters[9]),
            'battery_capacity': int(parameters[10]),
            'heatsink_temperature': int(parameters[11]),
            'solar_current': round(float(parameters[12]), 2),
            'solar_voltage': round(float(parameters[13]), 2),
            'battery_voltage_scc': round(float(parameters[14]), 2),
            'battery_discharge_current': int(parameters[15]),
            'unknown7': parameters[16],  # Keeping as string until further understanding
            'unknown8': parameters[17],  # Keeping as string until further understanding
            'unknown9': parameters[18],  # Keeping as string until further understanding
            'unknown10': parameters[19], # Keeping as string until further understanding
            'unknown11': parameters[20], # Keeping as string until further understanding
        }

        # Calculate additional values
        parsed_values['solar_power'] = round(parsed_values['solar_voltage'] * parsed_values['solar_current'], 2)
        parsed_values['battery_current'] = round(parsed_values['battery_charge_current'] - parsed_values['battery_discharge_current'], 2)

        return parsed_values
    except (IndexError, ValueError) as e:
        print(f"Error parsing data: {e}")
        return None