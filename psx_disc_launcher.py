import os
import time
import re
import subprocess
import csv
import xml.etree.ElementTree as ET

# MiSTer-specific paths
MISTER_CMD = "/dev/MiSTer_cmd"
MISTER_CORE_DIR = "/media/fat/_Console/"
PSX_GAME_PATHS = [
    "/media/fat/games/PSX/",
    "/media/usb0/games/PSX/"
]
SATURN_GAME_PATHS = [
    "/media/fat/games/Saturn/",
    "/media/usb0/games/Saturn/"
]
CSV_PATH = "/media/fat/dla/games.csv"
TMP_MGL_PATH = "/tmp/game.mgl"
SAVE_SCRIPT = "/media/fat/Scripts/save_disc.sh"

def find_core(system):
    """Find the latest core .rbf file for the given system in /media/fat/_Console/."""
    prefix = "PSX_" if system == "PSX" else "Saturn_"
    try:
        rbf_files = [f for f in os.listdir(MISTER_CORE_DIR) if f.startswith(prefix) and f.endswith(".rbf")]
        if not rbf_files:
            print(f"No {system} core found in {MISTER_CORE_DIR}. Please place a {prefix}*.rbf file there.")
            return None
        rbf_files.sort(reverse=True)
        latest_core = os.path.join(MISTER_CORE_DIR, rbf_files[0])
        print(f"Found {system} core: {latest_core}")
        if os.path.exists(latest_core):
            print(f"Verified {latest_core} exists and is readable")
        else:
            print(f"Error: {latest_core} reported but not accessible")
            return None
        return latest_core
    except Exception as e:
        print(f"Error finding {system} core: {e}")
        return None

def load_game_titles():
    """Load game ID to title mapping from CSV."""
    game_titles = {}
    try:
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)  # Skip header
            print(f"CSV Header: {header}")
            for row in reader:
                if len(row) >= 4:  # Minimum required: game_id, title, region, system
                    game_id, title = row[0].strip(), row[1].strip()
                    system = row[3].strip() if len(row) > 3 else "Unknown"
                    key = (game_id, system)
                    game_titles[key] = title
            print(f"Successfully loaded {len(game_titles)} game titles from {CSV_PATH}")
    except Exception as e:
        print(f"Error loading game titles from CSV: {e}")
    return game_titles

def get_optical_drive():
    """Detect an optical drive on MiSTer using lsblk."""
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
    except Exception as e:
        print(f"Error detecting drive: {e}")
        return None

def read_psx_game_id(drive_path):
    """Read PSX game ID from system.cnf."""
    try:
        mount_point = "/mnt/cdrom"
        if not os.path.exists(mount_point):
            os.makedirs(mount_point)
        
        mount_cmd = f"mount {drive_path} {mount_point} -t iso9660 -o ro"
        mount_result = os.system(mount_cmd)
        if mount_result != 0:
            print(f"PSX iso9660 mount failed. Trying udf...")
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
                                print(f"Extracted PSX Game ID: {game_id}")
                                return game_id
        print("system.cnf not found on disc (checked all case variations).")
        return None
    except Exception as e:
        print(f"Error reading PSX disc: {e}")
        return None
    finally:
        os.system(f"umount {mount_point}")

def read_saturn_game_id(drive_path):
    """Read Saturn game ID from disc header at offset 0x20-0x2A."""
    try:
        with open(drive_path, 'rb') as f:
            f.seek(0)  # Sector 0
            sector = f.read(2048)
            game_id = sector[32:42].decode('ascii', errors='ignore').strip()  # Offset 0x20 to 0x2A
            print(f"Extracted Saturn Game ID: {game_id}")
            return game_id
    except Exception as e:
        print(f"Error reading Saturn disc: {e}")
        return None

def find_game_file(title, system):
    """Search for the .chd game file based on system."""
    game_filename = f"{title}.chd"
    paths = PSX_GAME_PATHS if system == "PSX" else SATURN_GAME_PATHS
    for base_path in paths:
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
    """Display a popup message on MiSTer."""
    try:
        dialog_cmd = f"dialog --msgbox \"{message}\" 10 40"
        with open(MISTER_CMD, "w") as cmd_file:
            cmd_file.write(dialog_cmd + "\n")
            cmd_file.flush()
        print(f"Displayed popup: {message}")
    except Exception as e:
        print(f"Failed to display popup: {e}")

def create_mgl_file(core_path, game_file, mgl_path, system):
    """Create a temporary MGL file for the game."""
    mgl = ET.Element("mistergamedescription")
    rbf = ET.SubElement(mgl, "rbf")
    rbf.text = "_console/psx" if system == "PSX" else "_console/saturn"
    file_tag = ET.SubElement(mgl, "file")
    file_tag.set("delay", "1")
    file_tag.set("type", "s")
    file_tag.set("index", "1" if system == "PSX" else "0")
    file_tag.set("path", game_file)
    
    tree = ET.ElementTree(mgl)
    tree.write(mgl_path, encoding="utf-8", xml_declaration=True)
    print(f"Overwrote MGL file at {mgl_path}")

def launch_game_on_mister(game_id, title, core_path, system, drive_path):
    """Launch the game on MiSTer using a temporary MGL file."""
    if title == "Unknown Game":
        print(f"Skipping launch for unknown game: {game_id}")
        return
    
    game_file = find_game_file(title, system)
    if not game_file:
        print(f"Game file not found for {title} ({game_id}). Triggering save script...")
        save_cmd = f"{SAVE_SCRIPT} \"{drive_path}\" \"{title}\" {system}"
        # Wait for save script to complete
        subprocess.run(save_cmd, shell=True, check=True)
        return
    
    try:
        create_mgl_file(core_path, game_file, TMP_MGL_PATH, system)
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
    print("Starting disc launcher on MiSTer...")
    game_titles = load_game_titles()
    
    psx_core = find_core("PSX")
    saturn_core = find_core("SATURN")
    if not psx_core and not saturn_core:
        show_popup("No PSX or Saturn cores found in /media/fat/_Console/.")
        print("Cannot proceed without cores. Exiting...")
        return
    
    last_game_id = None
    
    while True:
        drive_path = get_optical_drive()
        if not drive_path:
            print("No optical drive detected. Waiting...")
            time.sleep(10)
            continue
        
        print(f"Checking drive {drive_path}...")
        
        # Try PSX first
        psx_game_id = read_psx_game_id(drive_path)
        if psx_game_id:
            if (psx_game_id, "PSX") != last_game_id:
                title = game_titles.get((psx_game_id, "PSX"), "Unknown Game")
                print(f"Found PSX game: {title} ({psx_game_id})")
                if psx_core:
                    launch_game_on_mister(psx_game_id, title, psx_core, "PSX", drive_path)
                else:
                    print("No PSX core available to launch game")
                last_game_id = (psx_game_id, "PSX")
            else:
                print(f"PSX game {psx_game_id} already launched. Waiting for new disc...")
            time.sleep(10)
            continue
        
        # Try Saturn if PSX fails
        saturn_game_id = read_saturn_game_id(drive_path)
        if saturn_game_id:
            if (saturn_game_id, "SATURN") != last_game_id:
                title = game_titles.get((saturn_game_id, "SATURN"), "Unknown Game")
                print(f"Found Saturn game: {title} ({saturn_game_id})")
                if saturn_core:
                    launch_game_on_mister(saturn_game_id, title, saturn_core, "SATURN", drive_path)
                else:
                    print("No Saturn core available to launch game")
                last_game_id = (saturn_game_id, "SATURN")
            else:
                print(f"Saturn game {saturn_game_id} already launched. Waiting for new disc...")
        else:
            print("No game detected. Waiting...")
            last_game_id = None
        
        time.sleep(10)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nScript stopped by user. Exiting...")