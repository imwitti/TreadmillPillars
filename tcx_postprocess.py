import xml.etree.ElementTree as ET
from datetime import datetime
from geopy.distance import geodesic
import os

GPX_NS = {'gpx': 'http://www.topografix.com/GPX/1/1'}
TCX_NS = {'tcx': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'}
ET.register_namespace('', TCX_NS['tcx'])

def load_gpx_route_with_distances(gpx_file):
    tree = ET.parse(gpx_file)
    root = tree.getroot()

    route = []
    prev_point = None
    total_dist = 0.0

    for trkpt in root.findall('.//gpx:trkpt', GPX_NS):
        lat = float(trkpt.attrib['lat'])
        lon = float(trkpt.attrib['lon'])
        ele_elem = trkpt.find('gpx:ele', GPX_NS)
        ele = float(ele_elem.text) if ele_elem is not None else 0.0
        point = (lat, lon)

        if prev_point is not None:
            seg_dist = geodesic(prev_point, point).meters
            total_dist += seg_dist
        route.append({'lat': lat, 'lon': lon, 'ele': ele, 'cum_dist': total_dist})
        prev_point = point

    return route

def interpolate_route_point(route, target_dist):
    """
    Given a cumulative distance, interpolate lat, lon, ele along the route.
    """
    for i in range(1, len(route)):
        if route[i]['cum_dist'] >= target_dist:
            r0 = route[i - 1]
            r1 = route[i]
            dist_diff = r1['cum_dist'] - r0['cum_dist']
            if dist_diff == 0:
                frac = 0
            else:
                frac = (target_dist - r0['cum_dist']) / dist_diff

            lat = r0['lat'] + frac * (r1['lat'] - r0['lat'])
            lon = r0['lon'] + frac * (r1['lon'] - r0['lon'])
            ele = r0['ele'] + frac * (r1['ele'] - r0['ele'])
            return lat, lon, ele

    # If target_dist beyond route end, return last point
    return route[-1]['lat'], route[-1]['lon'], route[-1]['ele']

def post_process_tcx_with_gpx(tcx_file_path, gpx_file_path, output_file_path=None):
    if output_file_path is None:
        output_file_path = tcx_file_path  # overwrite by default

    print(f"[INFO] Loading GPX route from {gpx_file_path}...")
    route = load_gpx_route_with_distances(gpx_file_path)

    print(f"[INFO] Parsing TCX file {tcx_file_path}...")
    tree = ET.parse(tcx_file_path)
    root = tree.getroot()

    trackpoints = root.findall('.//tcx:Trackpoint', TCX_NS)
    print(f"[INFO] Found {len(trackpoints)} trackpoints in TCX.")

    updated_count = 0
    for tp in trackpoints:
        dist_elem = tp.find('tcx:DistanceMeters', TCX_NS)
        if dist_elem is None:
            continue
        try:
            dist_m = float(dist_elem.text)
        except Exception:
            continue

        lat, lon, ele = interpolate_route_point(route, dist_m)

        # Find or create Position element
        pos_elem = tp.find('tcx:Position', TCX_NS)
        if pos_elem is None:
            pos_elem = ET.SubElement(tp, f"{{{TCX_NS['tcx']}}}Position")

        lat_elem = pos_elem.find('tcx:LatitudeDegrees', TCX_NS)
        if lat_elem is None:
            lat_elem = ET.SubElement(pos_elem, f"{{{TCX_NS['tcx']}}}LatitudeDegrees")
        lat_elem.text = f"{lat:.6f}"

        lon_elem = pos_elem.find('tcx:LongitudeDegrees', TCX_NS)
        if lon_elem is None:
            lon_elem = ET.SubElement(pos_elem, f"{{{TCX_NS['tcx']}}}LongitudeDegrees")
        lon_elem.text = f"{lon:.6f}"

        # Find or create AltitudeMeters
        alt_elem = tp.find('tcx:AltitudeMeters', TCX_NS)
        if alt_elem is None:
            alt_elem = ET.SubElement(tp, f"{{{TCX_NS['tcx']}}}AltitudeMeters")
        alt_elem.text = f"{ele:.1f}"

        updated_count += 1

    print(f"[INFO] Updated {updated_count} trackpoints with GPS data.")

    tree.write(output_file_path, encoding='utf-8', xml_declaration=True)
    print(f"[INFO] Saved enriched TCX to {output_file_path}")
