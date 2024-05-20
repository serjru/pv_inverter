# Inverter HID Script

This project contains a Python script to interface with a MasterPower Omega UM v4 inverter via a HID (Human Interface Device) connection. The script reads data from the inverter and publishes it to an MQTT broker, making it available for Home Assistant integration.

## Purpose

The main purpose of this project is to monitor the performance of the MasterPower Omega UM v4 inverter in real-time. The script captures key parameters such as load power and solar power and sends this data to an MQTT broker, where it can be visualized and analyzed using Home Assistant.

## Features

- **Real-time Monitoring**: Continuously reads data from the inverter.
- **MQTT Integration**: Publishes inverter data to an MQTT broker for easy integration with Home Assistant.
- **Home Assistant Sensors**: Supports MQTT sensors for displaying inverter load and solar power.

## Requirements

- Raspberry Pi (or any Linux-based system with Python support)
- MasterPower Omega UM v4 inverter
- Python 3.x
- `paho-mqtt` library for MQTT communication
- Home Assistant for monitoring and visualization

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/inverter-hid-script.git
   cd inverter-hid-script

2. **Set Up Virtual Environment**:

    ```bash
    python3 -m venv venv
    source venv/bin/activate

3. **Install Dependencies**:
    ```bash
    pip install paho-mqtt

## Configuration

### MQTT Broker Configuration
Ensure you have an MQTT broker running and accessible. If your broker requires authentication, ensure you have the correct username and password.

### Home Assistant Configuration
Add the following lines to your configuration.yaml in Home Assistant to set up MQTT sensors:

    ```yaml
    mqtt:
    sensor:
        - name: "Inverter Output Power"
        state_topic: "home/inverter/load_w"
        unique_id: "mp_omega_5600_v4_1"
        unit_of_measurement: "W"
        
        - name: "Inverter Solar Power"
        state_topic: "home/inverter/solar_power"
        unique_id: "mp_omega_5600_v4_2"
        unit_of_measurement: "W"


Usage

Activate the Virtual Environment:

bash
Copy code
source venv/bin/activate
Run the Script:

bash
Copy code
sudo /path/to/venv/bin/python /path/to/inverter_hid.py
Running in Background
To keep the script running independently of your SSH session, use one of the following methods:

Using nohup

bash
Copy code
nohup sudo /path/to/venv/bin/python /path/to/inverter_hid.py &
Using tmux

bash
Copy code
tmux new -s inverter_session
sudo /path/to/venv/bin/python /path/to/inverter_hid.py
# Detach by pressing Ctrl+B followed by D
Using screen

bash
Copy code
screen -S inverter_session
sudo /path/to/venv/bin/python /path/to/inverter_hid.py
# Detach by pressing Ctrl+A followed by D
Using systemd

Create a systemd service file to run the script as a service:

ini
Copy code
[Unit]
Description=Inverter HID Script
After=network.target

[Service]
ExecStart=/path/to/venv/bin/python /path/to/inverter_hid.py
WorkingDirectory=/path/to/project
StandardOutput=inherit
StandardError=inherit
Restart=always
User=yourusername

[Install]
WantedBy=multi-user.target
Enable and start the service:

bash
Copy code
sudo systemctl daemon-reload
sudo systemctl start inverter.service
sudo systemctl enable inverter.service
License

This project is licensed under the MIT License. See the LICENSE file for details.

Acknowledgements

Home Assistant
paho-mqtt
typescript
Copy code

### Summary of Changes
- Ensured that the `mqtt` section in the YAML configuration is correctly nested.
- Corrected any misplaced or duplicated sections.
- Simplified some instructions for clarity.

This should now display correctly in GitHub as a single, cohesive document. Replace `/path/to/` with the actual paths in your setup and `yourusername` with your actual username on the Raspberry Pi or the system where you run the script.





# pv_inverter
Data retrieval from Solar inverters

Run as
sudo /home/serj/my_project/venv/bin/python /home/serj/my_project/6inverter_hid.py

More information could be found at:
https://www.solarweb.net/forosolar/fotovoltaica-sistemas-aislados-la-red/41795-raspberry-e-hibrido-tipo-axpert-3.html