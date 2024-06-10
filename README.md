# Inverter HID Script
![GitHub Release](https://img.shields.io/github/v/release/serjru/pv_inverter)


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
- Docker if want to run as container

## Installation

### Option 1. From source code

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/serjru/pv_inverter.git
   cd inverter-hid-script
   ```

2. **Set Up Virtual Environment**:

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3. **Install Dependencies**:
    ```bash
    pip install paho-mqtt
    ```

### Option 2. As a Docker container

1. **Pull latest image**:
   ```bash
   docker pull serjtf/inverter:latest
   ```

2. **Run the container manually**:
   ```bash
   docker run -d --rm --network="host" --device=/dev/hidraw0 serjtf/inverter:latest
   ```

3. **Run container as a service**:
Create file /etc/systemd/system/inverter.service with the contents equal to the file within this repository.
Run the following commands:
```bash
sudo systemctl daemon-reload
sudo systemctl start inverter.service
sudo systemctl status inverter.service
```

## Configuration

### MQTT Broker Configuration
Ensure you have an MQTT broker running and accessible. If your broker requires authentication, ensure you have the correct username and password.

### Home Assistant Configuration
Add the following lines to your configuration.yaml in Home Assistant to set up MQTT sensors:
**Look file configuration.yaml within this repository**


## Usage
### Not necessary if run as a Docker image

1. **Activate the Virtual Environment**:

```bash
source venv/bin/activate
```

2. **Run the Script**:

```bash
sudo /path/to/venv/bin/python /path/to/inverter_hid.py
```

## Running in Background
To keep the script running independently of your SSH session, use one of the following methods:

### Using nohup

```bash
nohup sudo /path/to/venv/bin/python /path/to/inverter_hid.py &
```

### Using systemd

Create a systemd service file to run the script as a service:

```ini
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
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl start inverter.service
sudo systemctl enable inverter.service
```

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgements

Home Assistant
paho-mqtt


More information could be found at:
https://www.solarweb.net/forosolar/fotovoltaica-sistemas-aislados-la-red/41795-raspberry-e-hibrido-tipo-axpert-3.html