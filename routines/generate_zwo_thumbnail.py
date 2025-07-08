import os
import sys
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
from pathlib import Path
import re

def parse_zwo(file_path):
    """
    Parses a .zwo file and extracts workout segments and routine name.
    Returns a tuple: (segments_list, routine_name)
    """
    tree = ET.parse(file_path)
    root = tree.getroot()

    # Extract routine name from <name> tag
    routine_name_elem = root.find('name')
    if routine_name_elem is None or not routine_name_elem.text:
        routine_name = file_path.stem  # fallback to filename stem
    else:
        routine_name = routine_name_elem.text.strip()

    workout = root.find('workout')
    if workout is None:
        raise ValueError("No <workout> element found in the file.")

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
                segments.append({
                    'type': 'Interval On',
                    'duration': on_duration,
                    'power': on_power
                })
                segments.append({
                    'type': 'Interval Off',
                    'duration': off_duration,
                    'power': off_power
                })

    return segments, routine_name


def parse_json_config(config):
    """
    Parses a JSON-like configuration and extracts workout segments.
    Returns a list of segments with their type, duration, and power.
    """
    segments = []
    for duration, power in config:
        segments.append({
            'type': 'Interval',
            'duration': duration * 60,  # Convert minutes to seconds
            'power': power
        })
    return segments


def plot_workout(segments, output_file):
    """
    Generates a workout chart from segments and saves it as an image.
    Each segment is color-coded based on power intensity.
    """
    current_time = 0
    colors = []

    for seg in segments:
        duration = seg['duration']
        if seg['type'] in ['Warmup', 'Cooldown']:
            power = (seg['power_low'] + seg['power_high']) / 2
        else:
            power = seg['power']

        # Determine color based on power
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

    plt.xlabel('Time (s)')
    plt.ylabel('Power (FTP)')
    plt.title('Workout Chart')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output_file)
    plt.close()


def generate_thumbnail(zwo_path):
    """
    Generates a thumbnail image for a given .zwo file,
    saving the output as {routine_name}.png, where routine_name
    is extracted from the <name> tag inside the XML.
    """
    zwo_file = Path(zwo_path)
    if not zwo_file.is_file() or zwo_file.suffix.lower() != '.zwo':
        print(f"Invalid .zwo file: {zwo_path}")
        return

    try:
        segments, routine_name = parse_zwo(zwo_file)
    except Exception as e:
        print(f"Failed to parse {zwo_file.name}: {e}")
        return

    # Clean routine name for safe filename
    safe_name = re.sub(r'[^A-Za-z0-9_\- ]+', '', routine_name).strip()
    if not safe_name:
        safe_name = zwo_file.stem

    thumbnail_path = Path(f"{safe_name}.png")

    if thumbnail_path.exists():
        print(f"Thumbnail already exists: {thumbnail_path}")
        return

    try:
        plot_workout(segments, thumbnail_path)
        print(f"Thumbnail created: {thumbnail_path}")
    except Exception as e:
        print(f"Error generating thumbnail for {zwo_file.name}: {e}")


def generate_thumbnail_from_config(config, name):
    """
    Generates a thumbnail image from a JSON-like configuration.
    """
    safe_name = re.sub(r'[^A-Za-z0-9_\- ]+', '', name).strip()
    if not safe_name:
        safe_name = name

    thumbnail_path = Path(f"{safe_name}.png")
    if thumbnail_path.exists():
        print(f"Thumbnail already exists: {thumbnail_path}")
        return

    try:
        segments = parse_json_config(config)
        plot_workout(segments, thumbnail_path)
        print(f"Thumbnail created: {thumbnail_path}")
    except Exception as e:
        print(f"Error processing {name}: {e}")


def process_directory(directory):
    """
    Processes all .zwo files in the given directory.
    """
    dir_path = Path(directory)
    for zwo_file in dir_path.glob('*.zwo'):
        generate_thumbnail(zwo_file)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Called with a specific .zwo file
        generate_thumbnail(sys.argv[1])
    else:
        # No arguments; process all .zwo files in current directory
        process_directory('.')

        # Example JSON-like configurations
        workout_configs = {
    "Basic_pillars": [
        [5, 0],
        [5, 0.5],
        [4, 0],
        [4, 1.0],
        [3, 0],
        [3, 1.5],
        [2, 0],
        [2, 2.0],
        [1, 0],
        [1, 2.5]
    ],
    "long_pillars": [
        [6, 0],
        [6, 0.5],
        [5, 0],
        [5, 1.0],
        [4, 0],
        [4, 1.5],
        [3, 0],
        [3, 2.0],
        [2, 0],
        [2, 2.5],
        [1, 0],
        [2, 3]
    ],
    "Pillars_Buffer": [
        [3.5, 0.5],
        [5, 0.0],
        [5, 0.5],
        [4, 0],
        [4, 1.0],
        [3, 0],
        [3, 1.5],
        [2, 0],
        [2, 2.0],
        [1, 0],
        [1, 2.5]
    ],
    "Test": [
        [0.1, 0.5],
        [0.2, 0.0],
        [0.1, 0.5],
        [0.2, 0],
        [4, 1.0],
        [3, 0],
        [3, 1.5],
        [2, 0],
        [2, 2.0],
        [1, 0],
        [1, 2.5]
    ],
    "plain run": [
        [40, 0]
    ]
}


        for name, config in workout_configs.items():
            generate_thumbnail_from_config(config, name)
