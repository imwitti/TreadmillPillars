import xml.etree.ElementTree as ET
import os

def parse_zwo_file(file_path, starting_speed):
    """
    Parses a single ZWO file and converts it into a routine format.
    Each interval's speed is calculated as (power * starting_speed),
    and the speed increment is (target_speed - starting_speed).
    """
    tree = ET.parse(file_path)
    root = tree.getroot()

    routine_name = root.find('name').text.strip()
    routine = []

    for block in root.find('workout'):
        duration_sec = int(block.attrib.get('Duration', 0))
        duration_min = duration_sec / 60

        if 'Power' in block.attrib:
            power = float(block.attrib['Power'])
        else:
            power_low = float(block.attrib.get('PowerLow', 0))
            power_high = float(block.attrib.get('PowerHigh', 0))
            power = (power_low + power_high) / 2

        target_speed = power * starting_speed
        speed_increment = target_speed - starting_speed
        routine.append((duration_min, speed_increment))

    return {routine_name: routine}

def load_all_zwo_routines(folder_path, starting_speed):
    """
    Loads all .zwo files in the given folder and returns a dictionary
    of routines using the starting speed as the 5k pace.
    """
    routines = {}
    for file in os.listdir(folder_path):
        if file.lower().endswith('.zwo'):
            full_path = os.path.join(folder_path, file)
            try:
                routines.update(parse_zwo_file(full_path, starting_speed))
            except Exception as e:
                print(f"Failed to parse {file}: {e}")
    return routines
