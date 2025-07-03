import asyncio
from treadmill_control import TreadmillControl, parse_treadmill_data
from video_playback import play_video
from tcx_incremental import start_tcx_file, append_tcx_trackpoint, finalize_tcx_file
from virtual_competitors import generate_competitors_with_profiles
import queue
import time
from datetime import datetime

def simulate_ghost_distance(speed_profile, elapsed_seconds):
    distance = 0.0
    for i in range(len(speed_profile)):
        t_start, speed = speed_profile[i]
        t_end = speed_profile[i + 1][0] if i + 1 < len(speed_profile) else float('inf')
        if elapsed_seconds < t_start:
            break
        duration = min(elapsed_seconds, t_end) - t_start
        distance += (speed * (duration / 3600))  # km/h * hours = km
        if elapsed_seconds < t_end:
            break
    return distance * 1000  # meters

async def exercise_routine(initial_speed, routine, video_path):
    treadmill = TreadmillControl()
    await treadmill.connect()
    await treadmill.request_control()
    await asyncio.sleep(10)
    await treadmill.set_incline(1.0)

    speed_ratio_queue = queue.Queue()
    speed_ratio_queue.put(1.0)
    speed_queue = queue.Queue()
    speed_queue.put(initial_speed)
    distance_queue = queue.Queue()
    distance_queue.put(0.0)
    ghost_gap_queue = queue.Queue()

    start_time = datetime.utcnow()
    workout_data = []

    total_minutes = sum(duration for duration, _ in routine)
    total_distance_km = sum(inc * duration / 60 for duration, inc in routine)
    avg_speed = total_distance_km / (total_minutes / 60)

    ghost_runners = generate_competitors_with_profiles(total_minutes, avg_speed)

    print("\n--- Ghost Runner Profiles ---")
    for ghost in ghost_runners:
        print(f"{ghost['name']} | Duration: {ghost['duration_min']:.2f} min | Avg Speed: {ghost['avg_speed']:.2f} km/h | Strategy: {ghost['strategy']}")
        for t, s in ghost['speed_profile']:
            print(f"    t={t:.1f}s -> speed={s:.2f} km/h")
    print("-----------------------------\n")

    start_tcx_file(start_time)

    def callback(sender, data):
        speed, distance, incline = parse_treadmill_data(data)
        print(f"Speed: {speed:.2f} km/h, Distance: {distance:.2f} km, Incline: {incline:.2f} %")
        speed_ratio = speed / initial_speed if initial_speed > 0 else 1.0
        speed_ratio_queue.put(speed_ratio)
        speed_queue.put(speed)
        distance_queue.put(distance)

        timestamp = datetime.utcnow()
        append_tcx_trackpoint(timestamp, speed, distance, incline)

        workout_data.append({
            "timestamp": timestamp,
            "speed": speed,
            "distance": distance,
            "incline": incline
        })

        elapsed = (timestamp - start_time).total_seconds()
        user_distance_m = distance * 1000
        ghost_gaps = {}
        for ghost in ghost_runners:
            ghost_distance_m = simulate_ghost_distance(ghost["speed_profile"], elapsed)
            gap = user_distance_m - ghost_distance_m
            ghost_gaps[ghost["name"]] = gap
            print(f"[Ghost] {ghost['name']} | Segment Speed: {ghost['speed_profile'][0][1]:.2f} km/h | Distance: {ghost_distance_m:.1f} m | Gap: {gap:+.1f} m")

        ghost_gap_queue.put(ghost_gaps)

    await treadmill.start_monitoring(callback)

    video_task = asyncio.create_task(
        play_video(video_path, speed_ratio_queue, speed_queue, distance_queue, time.time(), ghost_gap_queue)
    )

    for duration, speed_increment in routine:
        await treadmill.set_speed(speed_increment)
        await asyncio.sleep(duration * 60)

    await treadmill.stop_monitoring()
    await treadmill.disconnect()
    await video_task

    end_time = datetime.utcnow()
    final_distance = workout_data[-1]["distance"] if workout_data else 0.0
    finalize_tcx_file(start_time, end_time, final_distance)
