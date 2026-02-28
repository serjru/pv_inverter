# PV Inverter Project Audit

**Date:** 2026-02-28
**Branch:** release/1.3.2
**Version:** 1.3.2

## Project Overview

A Python-based IoT monitoring solution for PV (solar) inverters using HID protocol communication. The system polls inverter metrics every ~6 seconds and publishes them to Home Assistant via MQTT. It runs as a Docker container on a Raspberry Pi.

### Architecture

```
[PV Inverter] --HID/USB--> [Raspberry Pi] --MQTT--> [Home Assistant]
                            (Docker container)        (Dashboard)
```

### Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11 |
| Messaging | MQTT (paho-mqtt 2.1.0) |
| Deployment | Docker (python:3.11-slim) |
| Service Manager | systemd |
| Target Platform | Raspberry Pi (aarch64, Debian Bookworm) |
| Integration | Home Assistant |

---

## Live System Status (Raspberry Pi 192.168.88.138)

- **Container:** `inverter` — running, up 8 days, 0 restarts
- **Image:** `serjtf/inverter:latest`
- **CPU:** 0.01%
- **Memory:** negligible
- **Network:** host mode
- **Device:** `/dev/hidraw0` mapped through
- **Other containers:** Home Assistant, ESPHome, Scrypted, voltronic-mqtt, watchtower (restarting)

### Active Warning in Container Logs

```
DeprecationWarning: Callback API version 1 is deprecated, update to latest version
  mqtt_client = mqtt.Client()
```

This is the ONLY log line ever emitted. The application produces no other output.

---

## File Inventory

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `inverter_hid.py` | 131 | Main entry point, MQTT loop | Active |
| `utils.py` | 158 | HID I/O, parsing, MQTT publish | Active |
| `Dockerfile` | 18 | Container build | Active |
| `requirements.txt` | 1 | Python dependencies | Active |
| `inverter.service` | 50 | systemd unit file | Active |
| `find_inverter.sh` | 56 | Bash HID device finder | Active |
| `configuration.yaml` | 220 | Home Assistant MQTT config | Active |
| `README.md` | 138 | Documentation | Active |
| `CHANGELOG.md` | 53 | Version history | Active |
| `LICENSE` | - | MIT License | Active |
| `temp.py` | 3 | Debug script (prints sys.executable) | **Dead code** |
| `temp_test.py` | 54 | CRC test scratch file | **Dead code** |
| `*.pdf` | - | Protocol spec | Reference |

---

## Issues Found

### CRITICAL

#### 1. No crash recovery in main loop
**File:** `inverter_hid.py:99-131`
The main `while True` loop has a single `try/except` around the entire thing. Any unhandled exception (HID disconnect, malformed data, OS error) kills the process. The Docker `--restart unless-stopped` will restart the container, but this causes a full reconnect cycle and data gap.

#### 2. `on_message` handler doesn't use context manager
**File:** `inverter_hid.py:78-93`
The MQTT message callback opens the device with `open_device()` and closes with `close_device()`, but if `send_command()` raises an exception, the file descriptor leaks. The `InverterConnection` context manager exists but isn't used here.

#### 3. No timeout on HID reads
**File:** `utils.py:47-64`
`read_response()` loops `while '\r' not in response` with 0.1s sleeps but no max iteration count. If the inverter stops responding mid-message, this loops forever, blocking all polling.

### HIGH

#### 4. paho-mqtt v2 API deprecation warning
**File:** `inverter_hid.py:69`
`mqtt.Client()` without a `CallbackAPIVersion` parameter triggers a deprecation warning with paho-mqtt 2.x. The installed version is 2.1.0 but the code uses v1 callback signatures. This will break in a future paho-mqtt release.

#### 5. No MQTT authentication
**File:** `inverter_hid.py:30-31`
MQTT connects to `localhost:1883` with no username/password. While the container uses host networking (so "localhost" is the Pi), any process on the Pi or network can publish commands to change the inverter mode.

#### 6. Logging is completely disabled
**File:** `inverter_hid.py:4-22`
All logging code is commented out. The only output is `print()` statements. There's no way to diagnose issues without attaching to the container. The changelog says logging was disabled because it "drains free space on device quickly" — this should be solved with log rotation, not disabling logging entirely.

#### 7. QPIGS command defined in two places
**File:** `inverter_hid.py:38` and `utils.py:6`
The `QPIGS` constant is defined in both files. The one in `utils.py` is unused (only referenced in a comment inside `read_response`). This is confusing and risks divergence.

### MEDIUM

#### 8. `from utils import *` wildcard import
**File:** `inverter_hid.py:5`
Star imports make it unclear what functions come from `utils.py` and can cause name collisions. Should use explicit imports.

#### 9. Hardcoded MQTT broker configuration
**File:** `inverter_hid.py:30-31`
MQTT broker address, port, and topics are hardcoded. Should be configurable via environment variables (the Docker container already supports env vars).

#### 10. No `.dockerignore` file
The `COPY . .` in the Dockerfile copies everything including `.git/`, `temp.py`, `temp_test.py`, the PDF, `LICENSE`, `README.md`, etc. into the container image. This bloats the image unnecessarily.

#### 11. No health check in Docker
The container has no `HEALTHCHECK` instruction. Docker/watchtower can't determine if the application is actually functioning (vs. stuck in an infinite read loop).

#### 12. Memory limit not applied
The `inverter.service` specifies `--memory=128m` but `docker inspect` shows `"Memory": 0` (unlimited). The memory limit may not be taking effect on this kernel/cgroup configuration.

#### 13. Dead code files
`temp.py` and `temp_test.py` are committed to the repo and deployed in the Docker image. They serve no purpose in production.

#### 14. Unknown QPIGS parameters not documented
**File:** `utils.py:146-148`
Parameters 16-20 from the QPIGS response are labeled `unknown7` through `unknown11`. The protocol PDF is included in the repo — these could likely be identified.

### LOW

#### 15. No pinned dependency version
**File:** `requirements.txt`
`paho-mqtt` has no version pin. A future major version bump could break the build.

#### 16. `find_inverter.sh` outputs debug to stderr
**File:** `find_inverter.sh:19-33`
The bash script outputs verbose debug info to stderr on every run. This clutters systemd journal logs.

#### 17. `configuration.yaml` has stale comment
**File:** `configuration.yaml:63`
Comment says "Should be deleted as new 'Actual mode' sensor is in use" — but the sensor is still there.

#### 18. No `.gitignore` file
There's no `.gitignore` to exclude `__pycache__/`, `.pyc`, IDE files, etc.

#### 19. watchtower container is crash-looping
On the Pi, watchtower is in `Restarting` state. This isn't part of this project but affects the auto-update pipeline.

#### 20. README has placeholder sections
**File:** `README.md:130-131, 137-138`
"[Add your license information here]" and "[Add any acknowledgments here]" remain as placeholders despite having an actual LICENSE file.

---

## Positive Observations

1. **Clean context manager pattern** — `InverterConnection` class is well-designed
2. **Security-conscious deployment** — `no-new-privileges`, resource limits, non-root
3. **Effective device auto-detection** — both Python and bash implementations work
4. **Good HA integration** — template sensors for derived values (grid consumption, mode mismatch) are thoughtful
5. **Stable in production** — 8 days uptime, 0 restarts, 0.01% CPU
6. **Small attack surface** — single dependency, slim base image
