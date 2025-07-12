import os
import sys
import json
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
from pathlib import Path
import re

def parse_zwo(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()

    # Extract name
    routine_name_elem = root.find('name')
    routine_name = routine_name_elem.text.strip() if routine_name_elem is not None else file_path.stem

    # Extract type
    duration_type_elem = root.find('durationType')
    routine_type = duration_type_elem.text.strip().lower() if duration_type_elem is not None else "time"

    workout = root.find('workout')
    if workout is None:
        raise ValueError("No <workout> element found.")

    segments = []
    for elem in workout:
        tag = elem.tag
        attrib = elem.attrib
        if tag in ['Warmup', 'Cooldown']:
            duration = float(attrib.get('Duration', 0))
            power_low = float(attrib.get('PowerLow', 0))
            power_high = float(attrib.get('PowerHigh', 0))
            segments.append({
                'type': tag,
                'duration': duration,
                'power_low': power_low,
                'power_high': power_high
            })
        elif tag == 'IntervalsT':
            repeat = int(attrib.get('Repeat', 1))
            on_duration = float(attrib.get('OnDuration', 0))
            off_duration = float(attrib.get('OffDuration', 0))
            on_power = float(attrib.get('OnPower', 0))
            off_power = float(attrib.get('OffPower', 0))
            for _ in range(repeat):
                segments.append({'type': 'Interval On', 'duration': on_duration, 'power': on_power})
                segments.append({'type': 'Interval Off', 'duration': off_duration, 'power': off_power})

    return segments, routine_name, routine_type


def parse_json_config(config):
    segments = []
    for duration, power in config:
        segments.append({
            'type': 'Interval',
            'duration': duration * 60,
            'power': power
        })
    return segments


def plot_workout(segments, output_file, routine_type="time"):
    current_time = 0
    colors = []

    for seg in segments:
        duration = seg['duration']
        if seg['type'] in ['Warmup', 'Cooldown']:
            power = (seg['power_low'] + seg['power_high']) / 2
        else:
            power = seg['power']

        if power < 0.9:
            color = 'green'
        elif power < 1.0:
            color = 'yellow'
        elif power < 1.1:
            color = 'orange'
        else:
            color = 'red'

        colors.append((current_time, current_time + duration, power, color))
        current_time += duration

    plt.figure(figsize=(10, 4))
    for start, end, power, color in colors:
        plt.fill_between([start, end], 0, power, step='post', color=color, alpha=0.7)

    # Labels
    plt.xlabel('Time (s)')
    plt.ylabel('Power (FTP)')
    plt.title('Workout Chart')
    plt.grid(True)

    # Add T or D label in top-right
    label = "T" if routine_type == "time" else "D"
    plt.text(0.98, 0.95, label, transform=plt.gca().transAxes,
             fontsize=30, fontweight='bold', color='gray',
             ha='right', va='top', alpha=0.5)

    plt.tight_layout()
    plt.savefig(output_file)
    plt.close()


def generate_thumbnail(zwo_path):
    zwo_file = Path(zwo_path)
    if not zwo_file.is_file() or zwo_file.suffix.lower() != '.zwo':
        print(f"Invalid .zwo file: {zwo_path}")
        return

    try:
        segments, routine_name, routine_type = parse_zwo(zwo_file)
    except Exception as e:
        print(f"Failed to parse {zwo_file.name}: {e}")
        return

    safe_name = re.sub(r'[^A-Za-z0-9_\- ]+', '', routine_name).strip()
    thumbnail_path = Path(f"{safe_name}.png")

    if thumbnail_path.exists():
        print(f"Thumbnail already exists: {thumbnail_path}")
        return

    try:
        plot_workout(segments, thumbnail_path, routine_type)
        print(f"Thumbnail created: {thumbnail_path}")
    except Exception as e:
        print(f"Error generating thumbnail for {zwo_file.name}: {e}")


def generate_thumbnail_from_config(config, name, routine_type):
    safe_name = re.sub(r'[^A-Za-z0-9_\- ]+', '', name).strip()
    thumbnail_path = Path(f"{safe_name}.png")

    if thumbnail_path.exists():
        print(f"Thumbnail already exists: {thumbnail_path}")
        return

    try:
        segments = parse_json_config(config)
        plot_workout(segments, thumbnail_path, routine_type)
        print(f"Thumbnail created: {thumbnail_path}")
    except Exception as e:
        print(f"Error processing {name}: {e}")


def process_directory(directory):
    dir_path = Path(directory)
    for zwo_file in dir_path.glob('*.zwo'):
        generate_thumbnail(zwo_file)


def load_routines_json():
    routines_path = Path(__file__).parent.parent / "Routines.json"
    if not routines_path.exists():
        print(f"Routines.json not found at {routines_path}")
        return {}

    try:
        with open(routines_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading Routines.json: {e}")
        return {}


if __name__ == "__main__":
    if len(sys.argv) > 1:
        generate_thumbnail(sys.argv[1])
    else:
        process_directory('.')

        # Load and process JSON routines from ../Routines.json
        routines = load_routines_json()
        for name, conf in routines.items():
            routine_type = conf.get("type", "time")
            segments = conf.get("segments", [])
            if segments:
                generate_thumbnail_from_config(segments, name, routine_type)
