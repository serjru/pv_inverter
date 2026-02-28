# Architecture Overview

## System Diagram

```
                          Raspberry Pi (Debian Bookworm, aarch64)
                         ┌──────────────────────────────────────────────────┐
                         │                                                  │
  ┌──────────────┐       │  ┌─────────────────────────────────────────────┐ │
  │ PV Inverter  │       │  │  Docker: inverter (python:3.11-slim)       │ │
  │ (Voltronic)  │──USB──│──│  ┌─────────────────┐   ┌───────────────┐  │ │
  │              │       │  │  │ inverter_hid.py  │──>│   utils.py    │  │ │
  │ Vendor: 0665 │       │  │  │  - Main loop     │   │  - HID I/O    │  │ │
  │ Product: 5161│       │  │  │  - MQTT client   │   │  - Parsing    │  │ │
  └──────────────┘       │  │  │  - Command rx    │   │  - Publishing │  │ │
                         │  │  └────────┬─────────┘   └───────────────┘  │ │
                         │  │           │ MQTT (localhost:1883)           │ │
                         │  └───────────┼────────────────────────────────┘ │
                         │              │ (host networking)                │
                         │  ┌───────────▼────────────────────────────────┐ │
                         │  │  Docker: homeassistant                     │ │
                         │  │  - MQTT sensors (8)                        │ │
                         │  │  - MQTT switch (mode control)              │ │
                         │  │  - Template sensors (4 derived)            │ │
                         │  │  - Integration sensors (5 energy totals)   │ │
                         │  └────────────────────────────────────────────┘ │
                         └──────────────────────────────────────────────────┘
```

## Data Flow

### Polling Cycle (every ~6 seconds)

```
1. QPIGS command ──> Inverter ──> Raw response (~100 bytes)
   │
   ├── parse_QPIGS() ──> 21 parameters + 2 calculated
   │
   └── MQTT publish ──> homeassistant/inverter/{metric_name}
       (16 topics per cycle, skipping unknowns)

2. [3 sec sleep]

3. QMOD command ──> Inverter ──> Mode letter (P/S/L/B/F/H)
   │
   └── MQTT publish ──> homeassistant/inverter/mode
                     ──> homeassistant/inverter/actual_mode

4. [3 sec sleep]

5. Repeat from 1
```

### Mode Control Flow

```
Home Assistant UI ──> MQTT "homeassistant/inverter/set_mode" (B or L)
       │
       └──> on_message callback
            │
            ├── Open HID device
            ├── Send COMMAND_BATTERY or COMMAND_LINE
            ├── Publish desired_mode
            └── Close HID device
```

## Key Files

```
pv_inverter/
├── inverter_hid.py      # Entry point: MQTT loop + command handling
├── utils.py             # HID device I/O, response parsing, MQTT publish
├── Dockerfile           # Container build (python:3.11-slim)
├── requirements.txt     # Dependencies (paho-mqtt)
├── inverter.service     # systemd unit for auto-start
├── find_inverter.sh     # Bash HID device finder (used by systemd)
├── configuration.yaml   # Home Assistant MQTT sensor definitions
├── CHANGELOG.md         # Version history
├── README.md            # Installation & usage guide
└── LICENSE              # MIT
```

## MQTT Topics

| Topic | Direction | Payload |
|-------|-----------|---------|
| `homeassistant/inverter/utility_voltage` | Publish | float (V) |
| `homeassistant/inverter/utility_frequency` | Publish | float (Hz) |
| `homeassistant/inverter/output_voltage` | Publish | float (V) |
| `homeassistant/inverter/output_frequency` | Publish | float (Hz) |
| `homeassistant/inverter/load_va` | Publish | int (VA) |
| `homeassistant/inverter/load_w` | Publish | int (W) |
| `homeassistant/inverter/load_percent` | Publish | int (%) |
| `homeassistant/inverter/bus_voltage` | Publish | float (V) |
| `homeassistant/inverter/battery_voltage` | Publish | float (V) |
| `homeassistant/inverter/battery_charge_current` | Publish | int (A) |
| `homeassistant/inverter/battery_capacity` | Publish | int (%) |
| `homeassistant/inverter/heatsink_temperature` | Publish | int (C) |
| `homeassistant/inverter/solar_current` | Publish | float (A) |
| `homeassistant/inverter/solar_voltage` | Publish | float (V) |
| `homeassistant/inverter/battery_voltage_scc` | Publish | float (V) |
| `homeassistant/inverter/battery_discharge_current` | Publish | int (A) |
| `homeassistant/inverter/solar_power` | Publish | float (W) |
| `homeassistant/inverter/battery_current` | Publish | float (A) |
| `homeassistant/inverter/mode` | Publish | char (L/B/P/S/F/H) |
| `homeassistant/inverter/actual_mode` | Publish | char |
| `homeassistant/inverter/desired_mode` | Publish | char (L/B) |
| `homeassistant/inverter/set_mode` | Subscribe | char (L/B) |

## Docker Container Configuration

| Setting | Value |
|---------|-------|
| Base image | python:3.11-slim |
| Network | host |
| Device | /dev/hidraw0 (auto-detected) |
| Security | no-new-privileges |
| Memory limit | 128MB (configured, see audit note) |
| CPU shares | 512 |
| Restart | unless-stopped |
| Volume | /var/log:/logs:rw |
