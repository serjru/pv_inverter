# PV Inverter Monitor

A Python-based monitoring solution for PV inverters that communicate via HID protocol. This project provides real-time monitoring of inverter metrics and integration with Home Assistant via MQTT.

## Features

- Real-time monitoring of inverter metrics:
  - Battery voltage, current, and capacity
  - Solar voltage, current, and power
  - Load metrics (VA, watts, percentage)
  - Utility and output parameters
  - Inverter operating mode
- MQTT integration with Home Assistant
- Automatic device detection and handling
- Secure containerized deployment
- Systemd service for automatic startup and recovery
- Resource-efficient operation

## Prerequisites

- Linux-based system (tested on Raspberry Pi)
- Docker
- Python 3.x
- MQTT broker (e.g., Mosquitto)
- Home Assistant (for dashboard integration)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/serjtf/pv_inverter.git
cd pv_inverter
```

### 2. Set Up Device Detection

1. Install the device detection script:
```bash
sudo cp find_inverter.sh /usr/local/bin/
sudo chmod 755 /usr/local/bin/find_inverter.sh
```

2. Create udev rule for device permissions:
```bash
echo 'KERNEL=="hidraw*", ATTRS{idVendor}=="0665", ATTRS{idProduct}=="5161", MODE="0666"' | sudo tee /etc/udev/rules.d/99-inverter.rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### 3. Install the Service

1. Copy the service file:
```bash
sudo cp inverter.service /etc/systemd/system/
```

2. Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable inverter
sudo systemctl start inverter
```

## Configuration

### Docker Container Settings

The service is configured with the following security and resource limits:
- Memory limit: 128MB
- CPU shares: 512
- No privilege escalation allowed
- Host network access for MQTT communication
- Read-write access to logs directory

### MQTT Configuration

Default MQTT settings:
- Broker: localhost
- Port: 1883
- Topics:
  - Command: homeassistant/inverter/set_mode
  - Desired Mode: homeassistant/inverter/desired_mode
  - Actual Mode: homeassistant/inverter/actual_mode
  - Metrics: homeassistant/inverter/{metric_name}

## Monitoring and Maintenance

### Check Service Status
```bash
sudo systemctl status inverter
```

### View Logs
```bash
journalctl -fu inverter
```

### Manual Device Detection
```bash
/usr/local/bin/find_inverter.sh
```

## Troubleshooting

1. If the device is not detected:
   - Check physical connection
   - Verify device permissions: `ls -l /dev/hidraw*`
   - Check udev rules: `udevadm monitor --property`

2. If the service fails to start:
   - Check logs: `journalctl -xeu inverter.service`
   - Verify Docker is running: `systemctl status docker`
   - Check device detection: `/usr/local/bin/find_inverter.sh`

## Security Features

- Container runs with limited privileges
- Resource limits prevent resource exhaustion
- Automatic device permission management
- Safe device handling through context managers
- Proper cleanup of stale containers

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[Add your license information here]

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a detailed list of changes.

## Acknowledgments

[Add any acknowledgments here]