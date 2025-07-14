import os
from datetime import datetime

# TCX and TPX namespaces
NS_TCX = "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
NS_TPX = "http://www.garmin.com/xmlschemas/ActivityExtension/v2"

tcx_filename = None
track_file = None
start_iso = None
lap_data = {
    'start_time': None,
    'last_time': None,
    'total_distance_km': 0.0
}

def start_tcx_file(start_time: datetime):
    global tcx_filename, track_file, start_iso, lap_data

    os.makedirs("TCX", exist_ok=True)
    tcx_filename = f"TCX/workout_{start_time.strftime('%Y-%m-%d_%H-%M-%S')}.tcx"
    start_iso = start_time.isoformat()
    lap_data['start_time'] = start_time

    with open(tcx_filename, 'w', encoding='utf-8') as f:
        f.write(f'''<?xml version="1.0" encoding="UTF-8"?>
<TrainingCenterDatabase xmlns="{NS_TCX}" xmlns:ns3="{NS_TPX}">
  <Activities>
    <Activity Sport="Running">
      <Id>{start_iso}</Id>
      <Lap StartTime="{start_iso}">
        <TotalTimeSeconds>0</TotalTimeSeconds>
        <DistanceMeters>0</DistanceMeters>
        <Calories>0</Calories>
        <Intensity>Active</Intensity>
        <TriggerMethod>Manual</TriggerMethod>
        <Track>
''')

    track_file = open(tcx_filename, 'a', encoding='utf-8')

def append_tcx_trackpoint(timestamp: datetime, speed_kmh: float, distance_km: float, incline_percent: float):
    global track_file, lap_data

    time_iso = timestamp.isoformat()
    speed_mps = speed_kmh / 3.6
    dist_m = distance_km * 1000

    # Update lap stats
    lap_data['last_time'] = timestamp
    lap_data['total_distance_km'] = max(lap_data['total_distance_km'], distance_km)

    track_file.write(f'''    <Trackpoint>
      <Time>{time_iso}</Time>
      <DistanceMeters>{dist_m:.2f}</DistanceMeters>
      <Extensions>
        <ns3:TPX>
          <ns3:Speed>{speed_mps:.3f}</ns3:Speed>
          <ns3:Incline>{incline_percent:.2f}</ns3:Incline>
        </ns3:TPX>
      </Extensions>
    </Trackpoint>
''')

def finalize_tcx_file():
    global tcx_filename, track_file, lap_data

    # Finish the <Track> and patch lap summary
    track_file.write(f'''    </Track>
        <TotalTimeSeconds>{(lap_data['last_time'] - lap_data['start_time']).total_seconds():.1f}</TotalTimeSeconds>
        <DistanceMeters>{lap_data['total_distance_km'] * 1000:.1f}</DistanceMeters>
      </Lap>
    </Activity>
  </Activities>
</TrainingCenterDatabase>
''')
    track_file.close()
    print(f"✅ TCX file written: {tcx_filename}")
