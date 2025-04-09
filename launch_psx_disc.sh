#!/bin/bash

# Path to the Python script
SCRIPT_PATH="/media/fat/Scripts/psx_disc_launcher.py"

# Log file for debugging
LOG_FILE="/media/fat/Scripts/psx_disc_launcher.log"

# Check if the Python script exists
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "Error: $SCRIPT_PATH not found!"
    exit 1
fi

# Ensure the script is executable
chmod +x "$SCRIPT_PATH"

# Launch the Python script with sudo in the background, fully detached
echo "Launching PSX Disc Launcher in the background..."
nohup sudo python3 "$SCRIPT_PATH" > "$LOG_FILE" 2>&1 &

# Print a message with the process ID
PID=$!
echo "PSX Disc Launcher started with PID $PID. Logs at $LOG_FILE"