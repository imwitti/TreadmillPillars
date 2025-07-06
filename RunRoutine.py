import asyncio
from treadmill_control import TreadmillControl, parse_treadmill_data
from video_playback import play_video
from tcx_incremental import start_tcx_file, append_tcx_trackpoint, finalize_tcx_file
from virtual_competitors import generate_competitors_with_profiles
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

    speed_ratio_queue = asyncio.Queue()
    await speed_ratio_queue.put(1.0)
    speed_queue = asyncio.Queue()
    await speed_queue.put(initial_speed)
    distance_queue = asyncio.Queue()
    await distance_queue.put(0.0)
    elapsed_time_queue = asyncio.Queue()
    ghost_gap_queue = asyncio.Queue()
    exit_signal = asyncio.Queue()

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

    loop = asyncio.get_event_loop()
    last_logged_distance = None  # <-- initialize here for throttling

    def callback(sender, data):
        nonlocal last_logged_distance  # make sure to access outer variable

        speed, distance, incline, elapsed_time = parse_treadmill_data(data)
        print(f"[CB] Speed: {speed:.2f} km/h, Distance: {distance:.2f} km, Incline: {incline if incline is not None else 0:.2f} %, Time: {elapsed_time:.1f}s")

        loop.call_soon_threadsafe(speed_ratio_queue.put_nowait, speed / initial_speed if initial_speed > 0 else 1.0)
        loop.call_soon_threadsafe(speed_queue.put_nowait, speed)
        loop.call_soon_threadsafe(distance_queue.put_nowait, distance)
        loop.call_soon_threadsafe(elapsed_time_queue.put_nowait, elapsed_time)

        timestamp = datetime.utcnow()
        append_tcx_trackpoint(timestamp, speed, distance, incline)
        workout_data.append({
            "timestamp": timestamp,
            "speed": speed,
            "distance": distance,
            "incline": incline
        })

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

        # Throttle ghost gap updates by rounding distance to 0.1m granularity
        distance_rounded = round(user_distance_m, 1)

        if last_logged_distance != distance_rounded:
            last_logged_distance = distance_rounded
            ghost_gaps = {}
            for ghost in ghost_runners:
                ghost_distance_m = simulate_ghost_distance(ghost["speed_profile"], elapsed)
                gap = user_distance_m - ghost_distance_m
                ghost_gaps[ghost["name"]] = gap
            loop.call_soon_threadsafe(ghost_gap_queue.put_nowait, ghost_gaps)

    print("[INFO] Starting treadmill monitoring...")
    await treadmill.start_monitoring(callback)

    print("[INFO] Launching video task...")
    video_task = asyncio.create_task(
        play_video(video_path, speed_ratio_queue, speed_queue, distance_queue, time.time(), ghost_gap_queue, exit_signal)
    )

    try:
        print("[INFO] Starting routine segments...")
        for idx, (duration, speed_increment) in enumerate(routine):
            print(f"[SEGMENT {idx}] Setting speed to {speed_increment:.2f} km/h for {duration:.1f} min")
            await treadmill.set_speed(speed_increment)

            print("[SEGMENT] Waiting for treadmill-reported segment start time...")
            try:
                segment_start_time = await asyncio.wait_for(elapsed_time_queue.get(), timeout=10)
                print(f"[SEGMENT] Segment started at treadmill time: {segment_start_time}s")
            except asyncio.TimeoutError:
                print("[ERROR] Timeout waiting for elapsed_time_queue (start of segment)")
                break

            target_time = segment_start_time + duration * 60
            print(f"[SEGMENT] Target end time: {target_time}s")

            while True:
                await asyncio.sleep(0.2)

                try:
                    current_time = await asyncio.wait_for(elapsed_time_queue.get(), timeout=2)
                except asyncio.TimeoutError:
                    print("[WARN] Waiting for treadmill time update...")
                    continue

                print(f"[SEGMENT] Current treadmill time: {current_time:.1f}s / Target: {target_time:.1f}s")

                if not exit_signal.empty():
                    print("[INFO] User exit detected.")
                    raise asyncio.CancelledError("User requested exit")

                if current_time >= target_time:
                    print("[SEGMENT] Segment complete.")
                    break

    except asyncio.CancelledError:
        print("[INFO] Workout interrupted by user.")
    finally:
        print("[INFO] Cleaning up...")
        await treadmill.stop_monitoring()
        await treadmill.disconnect()
        await video_task

        end_time = datetime.utcnow()
        final_distance = workout_data[-1]["distance"] if workout_data else 0.0
        finalize_tcx_file(start_time, end_time, final_distance)

        print("[INFO] Workout complete.")
        return {
            "start_time": start_time,
            "end_time": end_time,
            "workout_data": workout_data,
            "final_distance": final_distance
        }
