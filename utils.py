def open_device(device_file):
    """Open the HID device file."""
    try:
        fd = os.open(device_file, os.O_RDWR | os.O_NONBLOCK)
        return fd
    except OSError as e:
        print(f"Unable to open the device file: {e}")
        return None

def send_command(fd, command):
    """Send a command to the HID device."""
    try:
        os.write(fd, command)
        #print(f"Sent command: {command}")
    except OSError as e:
        print(f"Error sending command: {e}")

def read_response(fd):
    # Read the response from the HID device.
    try:
        response = os.read(fd, 8).decode('utf-8', errors='ignore')  # Attempt to read up to 8 bytes
        while '\r' not in response:
            time.sleep(0.1)
            response = response + os.read(fd, 8).decode('utf-8', errors='ignore')
        s = response.split("\\")
        if response:
            return response
    except OSError as e:
        if e.errno == 11:
            send_command(fd, QPIGS)  # Send a new request
            time.sleep(0.1)  # Sleep briefly and try again
        else:
            print(f"Error reading data: {e}")
    return None

def publish_data(mqtt_client, topic, data):
    # Publish data to the MQTT broker.
    mqtt_client.publish(topic, data)
    print(f"Published data to {topic}: {data}")

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
        
        # Map the parameters to their respective values
        parsed_values = {
            'utility_voltage': parameters[0],  # V
            'utility_frequency': parameters[1],  # Hz
            'output_voltage': parameters[2],  # V
            'output_frequency': parameters[3],  # Hz
            'load_va': parameters[4],  # VA
            'load_w': parameters[5],  # W
            'load_percent': parameters[6],  # %
            'bus_voltage': parameters[7],  # V
            'battery_voltage': parameters[8],  # V
            'battery_charge_current': parameters[9],  # A
            'battery_capacity': parameters[10],  # %
            'heatsink_temperature': parameters[11],  # Celsium
            'solar_current': parameters[12],  # A
            'solar_voltage': parameters[13],  # V
            'battery_voltage_scc': parameters[14],  # V
            'battery_discharge_current': parameters[15],  # A
            'unknown7': parameters[16],  # Unknown parameter
            'unknown8': parameters[17],  # Unknown parameter
            'unknown9': parameters[18],  # Unknown parameter
            'unknown10': parameters[19],  # Unknown parameter
            'unknown11': parameters[20],  # Unknown parameter
            #'unknown12': parameters[21],  # Unknown parameter
        }

        return parsed_values
    except Exception as e:
        print(f"Error parsing data: {e}")
        return None