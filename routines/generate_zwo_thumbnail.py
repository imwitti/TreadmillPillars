import os
import sys
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
from pathlib import Path

def parse_zwo(file_path):
    """
    Parses a .zwo file and extracts workout segments.
    Returns a list of segments with their type, duration, and power.
    """
    tree = ET.parse(file_path)
    root = tree.getroot()
    workout = root.find('workout')
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
    return segments

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
    times = []
    powers = []
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

        # Append start and end times and corresponding powers
        times.extend([current_time, current_time + duration])
        powers.extend([power, power])
        colors.append((current_time, current_time + duration, power, color))
        current_time += duration

    # Plot each segment with its corresponding color
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
    Generates a thumbnail image for a given .zwo file.
    """
    zwo_file = Path(zwo_path)
    if not zwo_file.is_file() or zwo_file.suffix.lower() != '.zwo':
        print(f"Invalid .zwo file: {zwo_path}")
        return

    thumbnail_path = zwo_file.with_suffix('.png')
    if thumbnail_path.exists():
        print(f"Thumbnail already exists: {thumbnail_path}")
        return

    try:
        segments = parse_zwo(zwo_file)
        plot_workout(segments, thumbnail_path)
        print(f"Thumbnail created: {thumbnail_path}")
    except Exception as e:
        print(f"Error processing {zwo_file.name}: {e}")

def generate_thumbnail_from_config(config, name):
    """
    Generates a thumbnail image from a JSON-like configuration.
    """
    thumbnail_path = Path(f"{name}.png")
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
            "p1": [
                [5, 0],
                [5, 0.8],
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
                [2, 3.0]
            ]
        }

        for name, config in workout_configs.items():
            generate_thumbnail_from_config(config, name)
