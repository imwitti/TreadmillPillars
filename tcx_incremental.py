import os
from datetime import datetime
from typing import Optional

from xml.sax.saxutils import escape

NS_TCX = "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
NS_TPX = "http://www.garmin.com/xmlschemas/ActivityExtension/v2"

tcx_filename = None
track_file = None
lap_start_time = None
lap_start_distance = 0.0
lap_index = 0
gps_track = []  # List of (distance_m, lat, lon)

def load_gpx_track(gpx_path):
    import xml.etree.ElementTree as ET
    tree = ET.parse(gpx_path)
    root = tree.getroot()
    ns = {'default': 'http://www.topografix.com/GPX/1/1'}
    trkpts = root.findall(".//default:trkpt", ns)

    track = []
    last_lat = last_lon = None
    total_distance = 0.0

    def haversine(lat1, lon1, lat2, lon2):
        from math import radians, sin, cos, sqrt, atan2
        R = 6371000  # Earth radius in meters
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
        return R * 2 * atan2(sqrt(a), sqrt(1 - a))

    for pt in trkpts:
        lat = float(pt.attrib['lat'])
        lon = float(pt.attrib['lon'])
        if last_lat is not None:
            total_distance += haversine(last_lat, last_lon, lat, lon)
        track.append((total_distance, lat, lon))
        last_lat, last_lon = lat, lon

    return track

def interpolate_gps(distance_m):
    if not gps_track or distance_m < gps_track[0][0] or distance_m > gps_track[-1][0]:
        return None, None
    for i in range(len(gps_track) - 1):
        d0, lat0, lon0 = gps_track[i]
        d1, lat1, lon1 = gps_track[i + 1]
        if d0 <= distance_m <= d1:
            ratio = (distance_m - d0) / (d1 - d0)
            lat = lat0 + ratio * (lat1 - lat0)
            lon = lon0 + ratio * (lon1 - lon0)
            return lat, lon
    return gps_track[-1][1], gps_track[-1][2]

def start_tcx_file(start_time: datetime, gpx_path: Optional[str] = None):
    global tcx_filename, track_file, lap_index, gps_track

    os.makedirs("TCX", exist_ok=True)
    tcx_filename = f"TCX/workout_{start_time.strftime('%Y-%m-%d_%H-%M-%S')}.tcx"
    lap_index = 0

    if gpx_path and os.path.exists(gpx_path):
        gps_track = load_gpx_track(gpx_path)

    with open(tcx_filename, 'w', encoding='utf-8') as f:
        f.write(f'''<?xml version="1.0" encoding="UTF-8"?>
<TrainingCenterDatabase xmlns="{NS_TCX}" xmlns:ns3="{NS_TPX}">
  <Activities>
    <Activity Sport="VirtualRun">
      <Id>{start_time.isoformat()}</Id>
''')

    track_file = open(tcx_filename, 'a', encoding='utf-8')

def start_new_lap(start_time: datetime, start_distance_km: float):
    global track_file, lap_start_time, lap_start_distance, lap_index
    lap_start_time = start_time
    lap_start_distance = start_distance_km
    lap_index += 1

    track_file.write(f'''      <Lap StartTime="{start_time.isoformat()}">
        <TotalTimeSeconds>0</TotalTimeSeconds>
        <DistanceMeters>0</DistanceMeters>
        <Calories>0</Calories>
        <Intensity>Active</Intensity>
        <TriggerMethod>Manual</TriggerMethod>
        <Track>
''')

def append_tcx_trackpoint(timestamp: datetime, speed_kmh: float, distance_km: float, incline_percent: float):
    global track_file

    time_iso = timestamp.isoformat()
    speed_mps = speed_kmh / 3.6
    dist_m = distance_km * 1000
    lat, lon = interpolate_gps(dist_m)

    track_file.write(f'''          <Trackpoint>
            <Time>{time_iso}</Time>
''')
    if lat is not None and lon is not None:
        track_file.write(f'''            <Position>
              <LatitudeDegrees>{lat:.6f}</LatitudeDegrees>
              <LongitudeDegrees>{lon:.6f}</LongitudeDegrees>
            </Position>
''')
    track_file.write(f'''            <DistanceMeters>{dist_m:.2f}</DistanceMeters>
            <Extensions>
              <ns3:TPX>
                <ns3:Speed>{speed_mps:.3f}</ns3:Speed>
                <ns3:Incline>{incline_percent:.2f}</ns3:Incline>
              </ns3:TPX>
            </Extensions>
          </Trackpoint>
''')

def finalize_lap(end_time: datetime, end_distance_km: float):
    global track_file, lap_start_time, lap_start_distance

    total_time = (end_time - lap_start_time).total_seconds()
    total_distance_m = (end_distance_km - lap_start_distance) * 1000

    track_file.write(f'''        </Track>
        <TotalTimeSeconds>{total_time:.1f}</TotalTimeSeconds>
        <DistanceMeters>{total_distance_m:.1f}</DistanceMeters>
      </Lap>
''')

def finalize_tcx_file():
    global track_file

    track_file.write(f'''    </Activity>
  </Activities>
</TrainingCenterDatabase>
''')
    track_file.close()
    print(f"✅ TCX file written: {tcx_filename}")
