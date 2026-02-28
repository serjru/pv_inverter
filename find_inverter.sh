#!/bin/bash
# This file should be located in /usr/local/bin/

VERBOSE=0
[ "$1" = "-v" ] && VERBOSE=1

log() {
    [ "$VERBOSE" -eq 1 ] && echo "$@" >&2
}

# Function to find the inverter device by vendor and product ID
find_inverter_device() {
    if ! [ -d /sys/class/hidraw ]; then
        echo "HID subsystem not available" >&2
        return 1
    fi

    # Check if any hidraw devices exist
    if ! ls /sys/class/hidraw/hidraw* >/dev/null 2>&1; then
        echo "No HID devices found" >&2
        return 1
    fi

    for device in /sys/class/hidraw/hidraw*; do
        if [ -f "$device/device/uevent" ]; then
            log "Checking device: $device"
            log "Device uevent content:"
            [ "$VERBOSE" -eq 1 ] && cat "$device/device/uevent" >&2

            # Get the HID_ID line specifically
            HID_ID=$(grep "HID_ID=" "$device/device/uevent")
            log "HID_ID line: $HID_ID"

            # Match the format with leading zeros: 0003:00000665:00005161
            if grep -q "HID_ID=.*:0*665:0*5161" "$device/device/uevent"; then
                log "Found matching device: $device"
                basename "$device"
                return 0
            else
                log "Device does not match required IDs (0665:5161)"
            fi
        fi
    done
    echo "No matching device found" >&2
    return 1
}

# Find the device
device=$(find_inverter_device)

if [ -n "$device" ]; then
    # Verify the device file exists
    if [ -c "/dev/$device" ]; then
        echo "/dev/$device"
        exit 0
    else
        echo "Device file /dev/$device does not exist" >&2
        exit 1
    fi
else
    echo "Inverter device not found" >&2
    exit 1
fi
