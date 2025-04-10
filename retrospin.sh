#!/bin/bash
SCRIPT_PATH="/media/fat/Scripts/retrospin_launcher.py"
LOG_FILE="/media/fat/Scripts/retrospin_launcher.log"
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "Error: $SCRIPT_PATH not found!"
    exit 1
fi
chmod +x "$SCRIPT_PATH"
echo "Launching RetroSpin Disc Launcher in the background..."
nohup sudo python3 "$SCRIPT_PATH" > "$LOG_FILE" 2>&1 &
PID=$!
echo "RetroSpin Disc Launcher started with PID $PID. Logs at $LOG_FILE"