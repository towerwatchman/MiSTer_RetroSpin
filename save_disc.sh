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
RIPDISC_PATH="/media/fat/retrospin/cdrdao"

# Ensure directory exists
mkdir -p "$BASE_DIR"

# Popup to ask user
dialog --yesno "Game file not found: $TITLE. Save disc as .bin/.cue to USB?" 10 40
RESPONSE=$?

if [ $RESPONSE -eq 0 ]; then  # Yes
    BIN_FILE="$BASE_DIR/$TITLE.bin"
    CUE_FILE="$BASE_DIR/$TITLE.cue"
    TOC_FILE="$BASE_DIR/$TITLE.toc"
    echo "Saving disc to: $BIN_FILE..."

    # Try to get actual disc size, fall back to 700MB if it fails
    DISC_SIZE=$(blockdev --getsize64 "$DRIVE_PATH" 2>/dev/null || echo $((700 * 1024 * 1024)))
    echo "Disc size detected: $DISC_SIZE bytes"

    # Start cdrdao in background, redirecting output to /dev/null
    ${RIPDISC_PATH}/cdrdao read-cd --read-raw --datafile "$BIN_FILE" --device "$DRIVE_PATH" --driver generic-mmc-raw "$TOC_FILE" > /dev/null 2>&1 &

    # Get cdrdao process ID
    CDRDAO_PID=$!

    # Progress gauge
    (
        while kill -0 $CDRDAO_PID 2>/dev/null; do
            if [ -f "$BIN_FILE" ]; then
                CURRENT_SIZE=$(stat -c %s "$BIN_FILE" 2>/dev/null || echo 0)
                PERCENT=$((CURRENT_SIZE * 100 / DISC_SIZE))
                if [ $PERCENT -gt 100 ]; then PERCENT=100; fi
                echo "XXX"
                echo "$PERCENT"
                echo "Saving $TITLE... $PERCENT% complete"
                echo "XXX"
            fi
            sleep 10  # Update every 10 seconds
        done
    ) | dialog --gauge "Saving $TITLE to USB..." 10 50 0

    # Wait for cdrdao to finish and check status
    wait $CDRDAO_PID
    CDRDAO_STATUS=$?
    if [ $CDRDAO_STATUS -eq 0 ]; then
        echo "Save to USB complete"

        # Convert .toc to .cue
        ${RIPDISC_PATH}/toc2cue "$TOC_FILE" "$CUE_FILE" > /dev/null 2>&1
        echo "Converted .toc to .cue: $CUE_FILE"

        # Clean up .toc file
        rm -f "$TOC_FILE"
        FINAL_MESSAGE="Disc saved successfully. Please close this dialog to restart the launcher and load $TITLE."
    else
        echo "Error occurred during disc save. Check $BIN_FILE and $TOC_FILE for partial data."
        FINAL_MESSAGE="Disc save failed. Partial data saved at $BIN_FILE. Close to restart launcher."
    fi
    
    # Prompt user to close and restart launcher
    dialog --msgbox "$FINAL_MESSAGE" 10 50
    /media/fat/Scripts/launch_psx_disc.sh
else
    echo "User declined to save disc image"
fi