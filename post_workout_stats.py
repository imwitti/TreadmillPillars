import pygame
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import os
import json

TCX_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'TCX'))
CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), 'user_config.json'))
PB_DISTANCES = [1, 3, 5, 10, 21]  # in km

def find_latest_tcx_file(directory):
    try:
        tcx_files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith('.tcx')]
        return max(tcx_files, key=os.path.getmtime) if tcx_files else None
    except FileNotFoundError:
        print(f"ERROR: TCX directory not found: {directory}")
        return None

def parse_tcx_trackpoints(tcx_filename):
    tree = ET.parse(tcx_filename)
    root = tree.getroot()
    ns = {'ns': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'}
    trackpoints = root.findall('.//ns:Trackpoint', ns)

    points = []
    for tp in trackpoints:
        dist_elem = tp.find('ns:DistanceMeters', ns)
        time_elem = tp.find('ns:Time', ns)
        if dist_elem is not None and time_elem is not None:
            dist_km = float(dist_elem.text) / 1000
            timestamp = datetime.fromisoformat(time_elem.text.replace("Z", "+00:00"))
            points.append((timestamp, dist_km))
    return points

def load_user_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {"pb_times_minutes": {}}

def save_user_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def check_for_pbs(trackpoints, user_config):
    pb_updates = {}
    pb_times = user_config.get("pb_times_minutes", {})
    reached = set()

    for i in range(1, len(trackpoints)):
        t0, d0 = trackpoints[0]
        ti, di = trackpoints[i]

        for target_km in PB_DISTANCES:
            if target_km in reached:
                continue
            if di >= target_km:
                elapsed = (ti - t0).total_seconds() / 60  # minutes
                prev_pb = pb_times.get(str(target_km), float('inf'))
                if elapsed < prev_pb:
                    print("new PB")
                    pb_times[str(target_km)] = elapsed
                    pb_updates[target_km] = elapsed
                reached.add(target_km)

    return pb_updates

def show_post_workout_stats():
    print("loading workout stats")
    pygame.init()
    screen = pygame.display.set_mode((800, 600), pygame.FULLSCREEN)
    pygame.display.set_caption("Workout Summary")
    font = pygame.font.Font(None, 48)
    small_font = pygame.font.Font(None, 36)

    latest_tcx = find_latest_tcx_file(TCX_DIR)
    if not latest_tcx:
        lines = ["No TCX files found.", "", "Press any key to exit..."]
    else:
        points = parse_tcx_trackpoints(latest_tcx)
        if not points:
            lines = ["No valid data in TCX.", "", "Press any key to exit..."]
        else:
            start_time = points[0][0]
            end_time = points[-1][0]
            total_distance_km = points[-1][1]
            duration = end_time - start_time
            total_minutes = duration.total_seconds() / 60
            avg_pace = total_minutes / total_distance_km if total_distance_km > 0 else 0

            # Load config and check PBs
            config = load_user_config()
            pb_updates = check_for_pbs(points, config)
            if pb_updates:
                save_user_config(config)

            # Summary + PB lines
            lines = [
                "Workout Summary",
                f"Duration: {str(timedelta(seconds=int(duration.total_seconds())))}",
                f"Distance: {total_distance_km:.2f} km",
                f"Avg Pace: {avg_pace:.2f} min/km",
                ""
            ]
            if pb_updates:
                lines.append("🏆 New PBs:")
                for dist in sorted(pb_updates.keys()):
                    lines.append(f"  {dist} km: {pb_updates[dist]:.1f} min")
            else:
                lines.append("No PBs this time. Keep going!")

            lines.append("")
            lines.append("Press any key to exit...")

    # Render screen
    screen.fill((0, 0, 0))
    y = 80
    for line in lines:
        text = font.render(line, True, (255, 255, 255)) if line else small_font.render(" ", True, (255, 255, 255))
        rect = text.get_rect(center=(screen.get_width() // 2, y))
        screen.blit(text, rect)
        y += 60

    pygame.display.flip()

    # Wait for any key
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN or event.type == pygame.QUIT:
                waiting = False
                break
    pygame.quit()
