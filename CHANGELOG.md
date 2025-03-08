# Changelog

## [1.3.2] - 2024-03-08

### Added
- New `find_inverter.sh` script for dynamic HID device detection
- Udev rule for automatic device permissions (`/etc/udev/rules.d/99-inverter.rules`)
- New `InverterConnection` class as a context manager for safer device handling
- New `handle_inverter_command` function to reduce code duplication

### Changed
- Improved systemd service file (`inverter.service`) with:
  - Dynamic device detection and mounting
  - Better error handling and recovery
  - Security enhancements (no-new-privileges, memory limits)
  - Proper cleanup of stale containers
  - Increased timeout and retry settings
  - Resource limits (memory: 128MB, CPU shares: 512)
- Simplified the MQTT publishing loop by iterating over parsed values
- Improved error handling and removed redundant device operations
- Removed problematic final device closure that could cause errors

### Fixed
- HID device detection now works with padded vendor/product IDs
- Service properly handles device absence and reconnection
- Container cleanup on service restart
- Permission issues with HID device access
- Resource leaks in device handling through context manager implementation

### Security
- Added `--security-opt=no-new-privileges:true` to prevent privilege escalation
- Added resource limits to container
- Explicit read-write volume mounting
- Improved device file handling security through context manager

### Documentation
- Added service file installation instructions
- Added GitHub repository link in service description
- Added comments explaining service configuration

## [1.3.0]
- Logging disabled as it drains free space on device quickly
- Added search for the correct device file in /dev/hidraw*
- Changed inverter.service to add small start delay and shutdown timeout

## [1.2.0]
- Added logging
- Added inverter mode control

## [1.1.0]
- Added more metrics, such as: Battery Discharge Current, Battery Charge Current, Inverter mode.
- Added more sensors to HomeAssistant configuration template file