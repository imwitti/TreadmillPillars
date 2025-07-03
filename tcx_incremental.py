import os
import xml.etree.ElementTree as ET
from datetime import datetime

# Global variables to hold the TCX tree and file path
tcx_tree = None
tcx_root = None
tcx_track = None
tcx_filename = None

def start_tcx_file(start_time):
    global tcx_tree, tcx_root, tcx_track, tcx_filename

    tcx_root = ET.Element("TrainingCenterDatabase", xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2")
    activities = ET.SubElement(tcx_root, "Activities")
    activity = ET.SubElement(activities, "Activity", Sport="Running")
    ET.SubElement(activity, "Id").text = start_time.isoformat()

    lap = ET.SubElement(activity, "Lap", StartTime=start_time.isoformat())
    ET.SubElement(lap, "TotalTimeSeconds").text = "0"
    ET.SubElement(lap, "DistanceMeters").text = "0"
    ET.SubElement(lap, "Calories").text = "0"
    ET.SubElement(lap, "Intensity").text = "Active"
    ET.SubElement(lap, "TriggerMethod").text = "Manual"

    tcx_track = ET.SubElement(lap, "Track")
    tcx_tree = ET.ElementTree(tcx_root)

    os.makedirs("TCX", exist_ok=True)
    tcx_filename = f"TCX/workout_{start_time.strftime('%Y-%m-%d_%H-%M-%S')}.tcx"
    tcx_tree.write(tcx_filename, encoding="utf-8", xml_declaration=True)

def append_tcx_trackpoint(timestamp, speed, distance, incline):
    global tcx_tree, tcx_track, tcx_filename

    trackpoint = ET.SubElement(tcx_track, "Trackpoint")
    ET.SubElement(trackpoint, "Time").text = timestamp.isoformat()
    ET.SubElement(trackpoint, "DistanceMeters").text = str(distance * 1000)

    extensions = ET.SubElement(trackpoint, "Extensions")
    tpx = ET.SubElement(extensions, "TPX", xmlns="http://www.garmin.com/xmlschemas/ActivityExtension/v2")
    ET.SubElement(tpx, "Speed").text = str(speed / 3.6)

    # Save the updated tree incrementally
    tcx_tree.write(tcx_filename, encoding="utf-8", xml_declaration=True)

def finalize_tcx_file(start_time, end_time, final_distance):
    global tcx_tree, tcx_root, tcx_filename

    lap = tcx_root.find(".//{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}Lap")
    if lap is not None:
        lap.find("{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}TotalTimeSeconds").text = str((end_time - start_time).total_seconds())
        lap.find("{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}DistanceMeters").text = str(final_distance * 1000)

    tcx_tree.write(tcx_filename, encoding="utf-8", xml_declaration=True)
    print(f"Workout data saved incrementally to {tcx_filename}")
