# Changelog

## 1.1.0
- Added more metrics, such as: Battery Discharge Current, Battery Charge Current, Inverter mode.
- Added more sensors to HomeAssistant configuration template file

## 1.2.0
- Added logging
- Added inverter mode control

## 1.3.0
- Logging disabled as it drains free space on device quickly
- Added search for the correct device file in /dev/hidraw*
- Changed inverter.service to add small start delay and shutdown timeout