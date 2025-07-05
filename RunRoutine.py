import asyncio
from treadmill_control import TreadmillControl, parse_treadmill_data
from video_playback import play_video
from tcx_incremental import start_tcx_file, append_tcx_trackpoint, finalize_tcx_file
from virtual_competitors import generate_competitors_with_profiles
import queue
import time
from datetime import datetime
import json

def check_and_update_pbs(workout_data, pb_times, distances_km=[1, 3, 5, 10, 21]):
    updated = False
    for target_km in distances_km:
        best_time = None
        for i in range(len(workout_data)):
            for j in range(i+1, len(workout_data)):
                dist_diff = workout_data[j]["distance"] - workout_data[i]["distance"]
                if dist_diff >= target_km:
                    time_diff = (workout_data[j]["timestamp"] - workout_data[i]["timestamp"]).total_seconds() / 60
                    if best_time is None or time_diff < best_time:
                        best_time = time_diff
                    break
        if best_time and (str(target_km) not in pb_times or best_time < pb_times[str(target_km)]):
            pb_times[str(target_km)] = round(best_time, 1)
            updated = True
    if updated:
        with open("user_config.json", "w") as f:
            json.dump({"pb_times_minutes": pb_times}, f, indent=2)
        print("🎉 New PBs updated:", pb_times)

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
    exit_signal = queue.Queue()  # 🆕 Added for graceful exit

    start_time = datetime.utcnow()
    workout_data = []

    total_minutes = sum(duration for duration, _ in routine)
    total_distance_km = sum(inc * duration / 60 for duration, inc in routine)
    avg_speed = total_distance_km / (total_minutes / 60)
    ghost_runners = generate_competitors_with_profiles(total_minutes, avg_speed)

    print("\n--- Ghost Runner Profiles ---")
    for ghost in ghost_runners:
        print(f"{ghost['name']}\n Duration: {ghost['duration_min']:.2f} min\n Avg Speed: {ghost['avg_speed']:.2f} km/h\n Strategy: {ghost['strategy']}")
        for t, s in ghost['speed_profile']:
            print(f" t={t:.1f}s -> speed={s:.2f} km/h")
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

        # Check PBs every 10 samples
        if len(workout_data) % 10 == 0:
            try:
                with open("user_config.json", "r") as f:
                    config = json.load(f)
                pb_times = config.get("pb_times_minutes", {})
                check_and_update_pbs(workout_data, pb_times)
            except Exception as e:
                print("PB check failed:", e)

        elapsed = (timestamp - start_time).total_seconds()
        user_distance_m = distance * 1000
        ghost_gaps = {}
        for ghost in ghost_runners:
            ghost_distance_m = simulate_ghost_distance(ghost["speed_profile"], elapsed)
            gap = user_distance_m - ghost_distance_m
            ghost_gaps[ghost["name"]] = gap
            #print(f"[Ghost] {ghost['name']}\n Segment Speed: {ghost['speed_profile'][0][1]:.2f} km/h\n Distance: {ghost_distance_m:.1f} m\n Gap: {gap:+.1f} m")
        ghost_gap_queue.put(ghost_gaps)

    await treadmill.start_monitoring(callback)

    video_task = asyncio.create_task(
        play_video(video_path, speed_ratio_queue, speed_queue, distance_queue, time.time(), ghost_gap_queue, exit_signal)  # 🆕 pass exit_signal
    )

    try:
        for duration, speed_increment in routine:
            await treadmill.set_speed(speed_increment)
            for _ in range(int(duration * 60)):
                await asyncio.sleep(1)
                if not exit_signal.empty():
                    raise asyncio.CancelledError("User requested exit")
    except asyncio.CancelledError:
        print("Workout interrupted by user.")
    finally:
        await treadmill.stop_monitoring()
        await treadmill.disconnect()
        await video_task

        end_time = datetime.utcnow()
        final_distance = workout_data[-1]["distance"] if workout_data else 0.0
        finalize_tcx_file(start_time, end_time, final_distance)

        return {
            "start_time": start_time,
            "end_time": end_time,
            "workout_data": workout_data,
            "final_distance": final_distance
        }
