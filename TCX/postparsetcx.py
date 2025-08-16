import xml.etree.ElementTree as ET
import math

# Load TCX file
tree = ET.parse("workout_2025-08-10_03-26-11.tcx.txt")
root = tree.getroot()

# Namespaces
ns = {
    'tcx': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2',
    'ns3': 'http://www.garmin.com/xmlschemas/ActivityExtension/v2'
}
ET.register_namespace('', ns['tcx'])
ET.register_namespace('ns3', ns['ns3'])

# Track center in Port Phillip Bay
center_lat = -38.000
center_lon = 144.900
radius_m = 400 / (2 * math.pi)  # ~63.66 meters

# Helper to convert meters to degrees (approximate)
def meters_to_degrees_lat(m):
    return m / 111320

def meters_to_degrees_lon(m, lat):
    return m / (111320 * math.cos(math.radians(lat)))

# Process Trackpoints
trackpoints = root.findall('.//tcx:Trackpoint', ns)
angle = 0
total_distance = 0

for i, tp in enumerate(trackpoints):
    dist_elem = tp.find('tcx:DistanceMeters', ns)
    if dist_elem is not None:
        try:
            distance = float(dist_elem.text)
            total_distance += distance
            angle = (total_distance / 400) * 2 * math.pi  # full circle every 400m

            lat_offset = radius_m * math.cos(angle)
            lon_offset = radius_m * math.sin(angle)

            lat = center_lat + meters_to_degrees_lat(lat_offset)
            lon = center_lon + meters_to_degrees_lon(lon_offset, center_lat)

            # Create Position element
            pos_elem = ET.Element('Position')
            lat_elem = ET.SubElement(pos_elem, 'LatitudeDegrees')
            lat_elem.text = f"{lat:.6f}"
            lon_elem = ET.SubElement(pos_elem, 'LongitudeDegrees')
            lon_elem.text = f"{lon:.6f}"

            # Insert Position into Trackpoint
            tp.insert(1, pos_elem)
        except Exception as e:
            print(f"Error at Trackpoint {i}: {e}")

# Save modified TCX
tree.write("workout_2025-08-10_modified.tcx", encoding="UTF-8", xml_declaration=True)
