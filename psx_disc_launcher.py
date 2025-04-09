import os
import time
import re
import subprocess
import csv
import xml.etree.ElementTree as ET

# MiSTer-specific paths
MISTER_CMD = "/dev/MiSTer_cmd"
MISTER_CORE_DIR = "/media/fat/_Console/"
GAME_PATHS = [
    "/media/fat/games/PSX/",
    "/media/usb0/games/PSX/"
]
CSV_PATH = "/media/fat/dla/games.csv"
TMP_MGL_PATH = "/tmp/psx_game.mgl"

def find_psx_core():
    """Find the latest PSX core .rbf file in /media/fat/_Console/."""
    try:
        rbf_files = [f for f in os.listdir(MISTER_CORE_DIR) if f.startswith("PSX_") and f.endswith(".rbf")]
        if not rbf_files:
            print(f"No PSX core found in {MISTER_CORE_DIR}. Please place a PSX_*.rbf file there.")
            return None
        rbf_files.sort(reverse=True)
        latest_core = os.path.join(MISTER_CORE_DIR, rbf_files[0])
        print(f"Found PSX core: {latest_core}")
        if os.path.exists(latest_core):
            print(f"Verified {latest_core} exists and is readable")
        else:
            print(f"Error: {latest_core} reported but not accessible")
            return None
        return latest_core
    except Exception as e:
        print(f"Error finding PSX core: {e}")
        return None

def load_game_titles():
    """Load game ID to title mapping from CSV."""
    game_titles = {}
    try:
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    game_id, title = row[0].strip('"'), row[1].strip('"')
                    game_titles[game_id] = title
        print(f"Loaded {len(game_titles)} game titles from {CSV_PATH}")
    except Exception as e:
        print(f"Error loading game titles from CSV: {e}")
    return game_titles

def get_optical_drive():
    """Detect an optical drive (e.g., /dev/sr0) on MiSTer using lsblk."""
    try:
        result = subprocess.run(['lsblk', '-d', '-o', 'NAME,TYPE'], capture_output=True, text=True, check=True)
        lines = result.stdout.splitlines()
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "rom":
                dev_path = f"/dev/{parts[0]}"
                print(f"Detected optical drive: {dev_path}")
                return dev_path
        print("No optical drive detected.")
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error running lsblk: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error detecting drive: {e}")
        return None

def read_system_cnf(drive_path):
    """Read system.cnf (case-insensitive) from the disc to extract the PSX game ID."""
    try:
        mount_point = "/mnt/cdrom"
        if not os.path.exists(mount_point):
            os.makedirs(mount_point)
        
        mount_cmd = f"mount {drive_path} {mount_point} -t iso9660 -o ro"
        mount_result = os.system(mount_cmd)
        if mount_result != 0:
            print(f"iso9660 mount failed. Trying udf...")
            mount_cmd = f"mount {drive_path} {mount_point} -t udf -o ro"
            mount_result = os.system(mount_cmd)
            if mount_result != 0:
                print(f"Failed to mount {drive_path} with iso9660 or udf. Return code: {mount_result}")
                return None
            else:
                print(f"Successfully mounted {drive_path} with udf")
        else:
            print(f"Successfully mounted {drive_path} with iso9660")
        
        system_cnf_variants = ["system.cnf", "SYSTEM.CNF", "System.cnf"]
        for root, dirs, files in os.walk(mount_point):
            for variant in system_cnf_variants:
                if variant in files:
                    system_cnf_path = os.path.join(root, variant)
                    with open(system_cnf_path, 'r', encoding='latin-1', errors='ignore') as f:
                        file_text = f.read()
                        print(f"Found {variant} at {system_cnf_path}")
                        for line in file_text.splitlines():
                            if "BOOT" in line.upper():
                                raw_id = line.split("=")[1].strip().split("\\")[1].split(";")[0]
                                game_id = raw_id.replace(".", "").replace("_", "-")
                                print(f"Extracted Game ID: {game_id}")
                                return game_id
        print("system.cnf not found on disc (checked all case variations).")
        return None
    except Exception as e:
        print(f"Error reading disc: {e}")
        return None
    finally:
        os.system(f"umount {mount_point}")

def find_game_file(title):
    """Search for the .chd game file using title only."""
    game_filename = f"{title}.chd"
    for base_path in GAME_PATHS:
        game_file = os.path.join(base_path, game_filename)
        if os.path.exists(game_file):
            print(f"Found game file: {game_file}")
            if os.access(game_file, os.R_OK):
                print(f"Game file {game_file} is readable")
            else:
                print(f"Game file {game_file} is not readable")
            return game_file
    print(f"Game file not found: {game_filename}")
    return None

def show_popup(message):
    """Display a popup message on MiSTer using dialog via /dev/MiSTer_cmd."""
    try:
        dialog_cmd = f"dialog --msgbox \"{message}\" 10 40"
        with open(MISTER_CMD, "w") as cmd_file:
            cmd_file.write(dialog_cmd + "\n")
            cmd_file.flush()
        print(f"Displayed popup: {message}")
    except Exception as e:
        print(f"Failed to display popup: {e}")

def create_mgl_file(core_path, game_file, mgl_path):
    """Create a temporary MGL file for the game with correct format."""
    mgl = ET.Element("mistergamedescription")
    rbf = ET.SubElement(mgl, "rbf")
    rbf.text = "_console/psx"  # Relative path as per working example
    file_tag = ET.SubElement(mgl, "file")
    file_tag.set("delay", "1")
    file_tag.set("type", "s")
    file_tag.set("index", "1")
    file_tag.set("path", game_file)  # Full path to .chd
    
    tree = ET.ElementTree(mgl)
    tree.write(mgl_path, encoding="utf-8", xml_declaration=True)
    print(f"Overwrote MGL file at {mgl_path}")

def launch_game_on_mister(game_id, title, core_path):
    """Launch the game on MiSTer using a temporary MGL file."""
    game_file = find_game_file(title)
    if not game_file:
        show_popup(f"Game not found: {title} ({game_id})")
        return
    
    try:
        # Create temporary MGL file (overwrite existing)
        create_mgl_file(core_path, game_file, TMP_MGL_PATH)
        
        # Send 'load_core' command with MGL file path
        command = f"load_core {TMP_MGL_PATH}"
        print(f"Preparing to send command to {MISTER_CMD}: {command}")
        with open(MISTER_CMD, "w") as cmd_file:
            cmd_file.write(command + "\n")
            cmd_file.flush()
            if os.path.exists(MISTER_CMD):
                print(f"Command '{command}' sent successfully")
            else:
                print(f"Failed to write '{command}' to {MISTER_CMD}")
        print(f"MGL file preserved at {TMP_MGL_PATH} for inspection")
    except Exception as e:
        print(f"Failed to launch game on MiSTer: {e}")

def main():
    print("Starting PSX disc launcher on MiSTer...")
    game_titles = load_game_titles()
    core_path = find_psx_core()
    if not core_path:
        show_popup("No PSX core found in /media/fat/_Console/. Please add PSX_*.rbf.")
        print("Cannot proceed without a PSX core. Exiting...")
        return
    
    last_game_id = None
    
    while True:
        drive_path = get_optical_drive()
        if not drive_path:
            print("No optical drive detected. Waiting...")
            time.sleep(10)
            continue
        
        print(f"Checking drive {drive_path}...")
        game_id = read_system_cnf(drive_path)
        
        if game_id:
            if game_id != last_game_id:
                title = game_titles.get(game_id, "Unknown Game")
                print(f"Found PSX game: {title} ({game_id})")
                launch_game_on_mister(game_id, title, core_path)
                last_game_id = game_id
            else:
                print(f"Game {game_id} already launched. Waiting for new disc...")
        else:
            print("No PSX game detected. Waiting...")
            last_game_id = None
        
        time.sleep(10)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nScript stopped by user. Exiting...")