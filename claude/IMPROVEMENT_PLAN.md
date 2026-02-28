# PV Inverter Improvement Plan

**Date:** 2026-02-28
**Based on:** [PROJECT_AUDIT.md](PROJECT_AUDIT.md)

## Priority Levels
- **P0** — Fix now (bugs, data loss risk)
- **P1** — Fix soon (deprecations, reliability)
- **P2** — Improve when convenient (code quality, maintainability)
- **P3** — Nice to have (polish)

---

## Phase 1: Reliability & Bug Fixes (P0)

### 1.1 Add per-iteration error handling in main loop
**File:** `inverter_hid.py`
**Issue:** #1 from audit

Wrap each command (QPIGS, QMOD) in its own try/except so a failure in one doesn't crash the process or skip the other. Add a short backoff on repeated failures.

```python
while True:
    try:
        data = handle_inverter_command(DEVICE_FILE, QPIGS)
        if data and is_correct_output(data):
            parsed_qpigs = parse_QPIGS(data)
            if parsed_qpigs:
                for key, value in parsed_qpigs.items():
                    if key.startswith('unknown'):
                        continue
                    publish_data(mqtt_client, f"homeassistant/inverter/{key}", value)
    except Exception as e:
        print(f"Error in QPIGS cycle: {e}")

    time.sleep(3)

    try:
        inverter_mode = handle_inverter_command(DEVICE_FILE, QMOD, read_qmod)
        if inverter_mode:
            publish_data(mqtt_client, "homeassistant/inverter/mode", inverter_mode)
            publish_data(mqtt_client, MQTT_TOPIC_ACTUAL_MODE, inverter_mode)
    except Exception as e:
        print(f"Error in QMOD cycle: {e}")

    time.sleep(3)
```

### 1.2 Use context manager in `on_message` callback
**File:** `inverter_hid.py`
**Issue:** #2 from audit

Replace raw `open_device`/`close_device` with `InverterConnection` to prevent fd leaks.

### 1.3 Add timeout to `read_response()`
**File:** `utils.py`
**Issue:** #3 from audit

Add a max retry count (e.g., 50 iterations = 5 seconds) to prevent infinite blocking.

```python
def read_response(fd, max_retries=50):
    try:
        response = os.read(fd, 8).decode('utf-8', errors='ignore')
        retries = 0
        while '\r' not in response and retries < max_retries:
            time.sleep(0.1)
            response += os.read(fd, 8).decode('utf-8', errors='ignore')
            retries += 1
        if '\r' in response:
            return response
        print("Read timeout: no carriage return received")
        return None
    except OSError as e:
        ...
```

---

## Phase 2: Deprecation & Compatibility Fixes (P1)

### 2.1 Update paho-mqtt to v2 callback API
**File:** `inverter_hid.py`
**Issue:** #4 from audit

```python
# Before:
mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    ...

# After:
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        print(f"Failed to connect: {reason_code}")
    else:
        client.subscribe(MQTT_TOPIC_COMMAND)
```

### 2.2 Pin paho-mqtt version in requirements.txt
**File:** `requirements.txt`
**Issue:** #15 from audit

```
paho-mqtt>=2.1.0,<3.0.0
```

### 2.3 Re-enable logging with rotation
**File:** `inverter_hid.py`
**Issue:** #6 from audit

Use Python's `RotatingFileHandler` to cap log size (e.g., 5 MB, 2 backups). This solves the "drains free space" problem.

```python
import logging
from logging.handlers import RotatingFileHandler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler("/logs/inverter.log", maxBytes=5*1024*1024, backupCount=2),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
```

---

## Phase 3: Code Quality (P2)

### 3.1 Replace wildcard import
**File:** `inverter_hid.py`
**Issue:** #8 from audit

```python
from utils import (
    find_inverter_device, open_device, close_device,
    send_command, read_response, read_qmod,
    publish_data, is_correct_output, parse_QPIGS
)
```

### 3.2 Make MQTT config configurable via env vars
**File:** `inverter_hid.py`
**Issue:** #9 from audit

```python
MQTT_BROKER = os.environ.get("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
```

### 3.3 Remove duplicate QPIGS constant
**File:** `utils.py:6`
**Issue:** #7 from audit

Delete the unused `QPIGS` import in utils.py.

### 3.4 Add `.dockerignore`
**Issue:** #10 from audit

```
.git
.gitignore
*.md
*.pdf
LICENSE
temp.py
temp_test.py
claude/
```

### 3.5 Add `.gitignore`
**Issue:** #18 from audit

```
__pycache__/
*.pyc
*.pyo
.env
.venv/
.idea/
.vscode/
*.swp
```

### 3.6 Delete dead code files
**Issue:** #13 from audit

Remove `temp.py` and `temp_test.py` from the repository.

### 3.7 Add Docker HEALTHCHECK
**File:** `Dockerfile`
**Issue:** #11 from audit

A simple approach — check that the process is running:
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD pgrep -f inverter_hid.py || exit 1
```

A better approach (Phase 4) would be to expose a simple health endpoint or write a heartbeat file.

---

## Phase 4: Enhancements (P3)

### 4.1 Identify unknown QPIGS parameters
**Issue:** #14 from audit

Cross-reference with the protocol PDF to label parameters 16-20 properly. Based on standard inverter protocols, these are likely:
- param 16: Device status flags (binary)
- param 17: Battery voltage offset for fans
- param 18: EEPROM version
- param 19: PV1 charging power
- param 20: Device status flags 2

### 4.2 Fix README placeholders
**Issue:** #20 from audit

Update "[Add your license information here]" to "MIT License" and remove the acknowledgments placeholder.

### 4.3 Clean up `configuration.yaml` stale comment
**Issue:** #17 from audit

Either remove the deprecated "Inverter Mode" sensor or remove the "Should be deleted" comment.

### 4.4 Reduce `find_inverter.sh` verbosity
**Issue:** #16 from audit

Remove or gate debug `echo` statements behind a `-v` flag.

### 4.5 Add MQTT availability/LWT (Last Will and Testament)
When the container stops, Home Assistant sensors go stale with no indication. Adding an MQTT LWT would allow HA to show the inverter as "unavailable" when the container disconnects.

```python
mqtt_client.will_set("homeassistant/inverter/availability", "offline", retain=True)
# On connect:
mqtt_client.publish("homeassistant/inverter/availability", "online", retain=True)
```

### 4.6 Investigate watchtower crash loop
The watchtower container on the Pi is in restart loop. This prevents automated image updates.

---

## Implementation Order

| Step | Phase | Effort | Risk |
|------|-------|--------|------|
| 1 | 1.1 Per-iteration error handling | Small | Low |
| 2 | 1.2 Context manager in on_message | Small | Low |
| 3 | 1.3 Read timeout | Small | Low |
| 4 | 2.1 paho-mqtt v2 API | Medium | Medium (test needed) |
| 5 | 2.2 Pin dependency version | Trivial | None |
| 6 | 2.3 Re-enable logging | Small | Low |
| 7 | 3.1-3.6 Code quality batch | Small | Low |
| 8 | 3.7 Docker HEALTHCHECK | Trivial | None |
| 9 | 4.1-4.5 Enhancements | Medium | Low |

**Total estimated changes:** ~100 lines modified across 5-6 files, 3 new files (.dockerignore, .gitignore, claude/), 2 files deleted (temp.py, temp_test.py).
