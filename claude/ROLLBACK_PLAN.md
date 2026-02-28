# Rollback Plan

## Overview

The old v1.3.2 image is preserved on the Raspberry Pi as `serjtf/inverter:v1.3.2-fallback`. If the new release causes problems, you can roll back in under 30 seconds.

## Quick Rollback (copy-paste)

```bash
ssh serj@192.168.88.138

docker stop inverter && docker rm inverter

docker run -d \
  --name inverter \
  --network=host \
  --device=/dev/hidraw0 \
  --security-opt=no-new-privileges:true \
  --memory=128m \
  --cpu-shares=512 \
  -v /var/log:/logs:rw \
  --restart unless-stopped \
  serjtf/inverter:v1.3.2-fallback
```

## Verify After Rollback

```bash
# Container should be running
docker ps --filter name=inverter

# Should show the deprecation warning (expected for v1.3.2)
docker logs inverter 2>&1 | head -5

# Data should flow to Home Assistant
timeout 8 mosquitto_sub -h localhost -t 'homeassistant/inverter/#' -v
```

## When to Roll Back

- Container enters a restart loop (`docker ps` shows `Restarting`)
- No MQTT data reaching Home Assistant for more than 2 minutes
- Container exits with consecutive error limit (`Too many consecutive errors`)
- Any unexpected behavior in inverter mode switching

## Restoring to v1.4.0 After Rollback

If you fixed the issue and want to go back to v1.4.0:

```bash
docker stop inverter && docker rm inverter

docker run -d \
  --name inverter \
  --network=host \
  --device=/dev/hidraw0 \
  --security-opt=no-new-privileges:true \
  --memory=128m \
  --cpu-shares=512 \
  -v /var/log:/logs:rw \
  --restart unless-stopped \
  serjtf/inverter:latest
```

## Cleaning Up the Fallback Image

Once v1.4.0 has been stable for a few days, you can remove the fallback image to free disk space:

```bash
docker rmi serjtf/inverter:v1.3.2-fallback
```

## Images on the Pi

| Tag | Image ID | Description |
|-----|----------|-------------|
| `latest` | `0ef9d19864fd` | v1.4.0 (current) |
| `v1.3.2-fallback` | `7cfbc106d413` | v1.3.2 (previous stable) |
