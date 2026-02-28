# HID Device Interaction Analysis

**Date:** 2026-02-28
**Device:** Voltronic inverter, Vendor 0x0665, Product 0x5161, `/dev/hidraw0`

## Benchmark Results

All benchmarks run on the live Raspberry Pi inside the Docker container.

### Device I/O timing

| Operation | Time |
|-----------|------|
| `os.open()` | <0.1ms |
| `os.close()` | <0.1ms |
| `os.write()` (send command) | ~3ms |
| QPIGS full response (112 bytes) | ~450ms from command |
| QMOD full response (5 bytes) | ~500ms from command |

### QPIGS read strategy comparison

| Pre-wait | Poll interval | Total time | Retries |
|----------|---------------|------------|---------|
| 500ms | n/a (data ready) | 503ms | 0 |
| 400ms | 20ms | 440ms | 1-2 |
| 0ms | 100ms | 501ms | 5 |
| 0ms | 50ms | 451ms | 9 |
| 0ms | 20ms | 442ms | 22 |
| 0ms | 10ms | 444ms | 44 |

**Key finding:** The inverter takes ~440ms to generate the QPIGS response regardless of read strategy. Poll-based reading with 20ms interval is optimal — it's as fast as possible (442ms) without excessive CPU usage.

### Back-to-back commands (same fd)

| Gap between QPIGS → QMOD | QPIGS | QMOD | Total |
|---------------------------|-------|------|-------|
| 0ms | OK | OK | 1005ms |
| 50ms | OK | OK | 1056ms |
| 100ms | OK | OK | 1106ms |
| 200ms | FAIL | OK | 1207ms |

**Key finding:** Zero gap between commands works. The device handles immediate back-to-back commands correctly.

### Persistent file descriptor

5 rapid QPIGS cycles (100ms gap) with a single fd: **all 5 succeeded** (503ms each, 112B).

**Key finding:** Persistent fd is stable. No need to open/close per command.

### Concurrent file descriptors

Two fds opened simultaneously, command sent on fd1: **both fd1 and fd2 received the same 112-byte response**.

**Key finding:** HID broadcasts to all open fds. This is a **race condition risk** — if `on_message` (MQTT thread) opens a second fd while the main loop is reading, both see the same response, corrupting the main loop's read.

### Stale data

After opening a fresh fd with no command sent: **errno 11 (no data)**.

**Key finding:** No stale data accumulates. Clean reads after fresh open.

---

## Current Code Timing Breakdown

```
handle_inverter_command():
  open_device()           ~0ms
  send_command()          ~3ms
  time.sleep(1)           1000ms   ← BOTTLENECK: device responds in ~450ms
  read_response()         ~100ms   ← with 100ms poll interval
  close_device()          ~0ms
  Per command:            ~1103ms

Main loop:
  QPIGS cycle             ~1103ms
  time.sleep(3)           3000ms   ← BOTTLENECK
  QMOD cycle              ~1103ms
  time.sleep(3)           3000ms   ← BOTTLENECK
  ─────────────────────────────────
  Total cycle:            ~8206ms  (~8.2 seconds refresh rate)
```

### Wasted time per cycle:
- `time.sleep(1)` × 2 commands: wastes **1100ms** (device needs 450ms, not 1000ms)
- `time.sleep(3)` × 2 gaps: wastes **6000ms** (could be 500ms each)
- 100ms poll vs 20ms poll: wastes **~120ms**
- open/close per command × 2: negligible but unnecessary

**Total waste: ~6220ms per cycle (76% of cycle time is sleeping)**

---

## Issues Found

### CRITICAL: Thread-unsafe HID access

**Files:** `inverter_hid.py:88-107` (on_message) and `inverter_hid.py:120-151` (main loop)

The MQTT `on_message` callback runs in the paho-mqtt network thread. The main `while True` loop runs in the main thread. Both independently open and access `/dev/hidraw0`.

If a mode change command arrives while the main loop is mid-QPIGS:
1. Main thread has fd1 open, waiting for QPIGS response
2. MQTT thread opens fd2, sends COMMAND_BATTERY
3. Both fd1 and fd2 receive responses meant for different commands
4. Main thread may read mode-change ACK instead of QPIGS data → parse failure

This is an intermittent bug that explains some of the "no valid data" warnings seen in logs.

### HIGH: 1000ms pre-read sleep is 2x too long

**File:** `inverter_hid.py:73`

`time.sleep(1)` before reading, but benchmarks show the device responds in ~450ms. This wastes 550ms per command (1100ms per cycle).

### MEDIUM: Open/close per command is unnecessary

**File:** `inverter_hid.py:67-74`

`handle_inverter_command` opens and closes the device for every command. Benchmarks confirm persistent fd works for at least 5 rapid cycles. Persistent fd enables back-to-back commands without re-open overhead.

---

## Optimized Cycle (Achievable)

```
Persistent fd (opened once):
  send QPIGS              ~3ms
  poll-read (20ms interval) ~445ms
  send QMOD               ~3ms
  poll-read (20ms interval) ~500ms
  sleep between cycles     500ms
  ─────────────────────────────────
  Total cycle:            ~1451ms  (~1.5 seconds refresh rate)
```

**Improvement: 8.2s → 1.5s (5.5× faster refresh rate)**
