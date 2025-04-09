#!/bin/bash

# Arguments from Python: drive_path, title, system
DRIVE_PATH="$1"
TITLE="$2"
SYSTEM="$3"

# USB paths
USB_PSX_PATH="/media/usb0/games/PSX"
USB_SATURN_PATH="/media/usb0/games/Saturn"
BASE_DIR="$USB_SATURN_PATH"
if [ "$SYSTEM" == "PSX" ]; then
    BASE_DIR="$USB_PSX_PATH"
fi

# Ensure directory exists
mkdir -p "$BASE_DIR"

# Popup to ask user
dialog --yesno "Game file not found: $TITLE. Save disc as .bin/.cue to USB?" 10 40
RESPONSE=$?

if [ $RESPONSE -eq 0 ]; then  # Yes
    BIN_FILE="$BASE_DIR/$TITLE.bin"
    CUE_FILE="$BASE_DIR/$TITLE.cue"
    echo "Saving disc to $BIN_FILE..."

    # Try to get actual disc size, fall back to 700MB if it fails
    DISC_SIZE=$(blockdev --getsize64 "$DRIVE_PATH" 2>/dev/null || echo $((700 * 1024 * 1024)))
    echo "Disc size detected: $DISC_SIZE bytes"

    # Start dd in background with larger block size
    dd if="$DRIVE_PATH" of="$BIN_FILE" bs=64k &

    # Get dd process ID
    DD_PID=$!

    # Progress gauge
    (
        while kill -0 $DD_PID 2>/dev/null; do
            if [ -f "$BIN_FILE" ]; then
                CURRENT_SIZE=$(stat -c %s "$BIN_FILE" 2>/dev/null || echo 0)
                PERCENT=$((CURRENT_SIZE * 100 / DISC_SIZE))
                if [ $PERCENT -gt 100 ]; then PERCENT=100; fi
                echo "XXX"
                echo "$PERCENT"
                echo "Saving $TITLE... $PERCENT% complete"
                echo "XXX"
            fi
            sleep 10  # Increased to 10 seconds to reduce overhead
        done
    ) | dialog --gauge "Saving $TITLE to USB..." 10 50 0

    # Wait for dd to finish
    wait $DD_PID
    echo "Save complete"

    # Create .cue file
    echo "FILE \"$TITLE.bin\" BINARY" > "$CUE_FILE"
    echo "  TRACK 01 MODE2/2352" >> "$CUE_FILE"
    echo "    INDEX 01 00:00:00" >> "$CUE_FILE"
    echo "Saved .bin and .cue files: $BIN_FILE, $CUE_FILE"
    
    # Prompt user to close and restart launcher
    dialog --msgbox "Disc saved successfully. Please close this dialog to restart the launcher and load $TITLE." 10 50
    /media/fat/Scripts/launch_psx_disc.sh
else
    echo "User declined to save disc image"
fi