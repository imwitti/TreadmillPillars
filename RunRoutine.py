import asyncio
import os
import json
from datetime import datetime
from treadmill_control import TreadmillControl, parse_treadmill_data
from video_playback import play_video
from virtual_competitors import generate_competitors_with_profiles
from tcx_incremental import (
    start_tcx_file,
    start_new_lap,
    append_tcx_trackpoint,
    finalize_lap,
    finalize_tcx_file
)

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

def get_current_ghost_speed(speed_profile, elapsed_seconds):
    for i in range(len(speed_profile) - 1):
        t0, s0 = speed_profile[i]
        t1, s1 = speed_profile[i + 1]
        if t0 <= elapsed_seconds < t1:
            ratio = (elapsed_seconds - t0) / (t1 - t0)
            return s0 + ratio * (s1 - s0)
    return speed_profile[-1][1]

async def exercise_routine(initial_speed, routine_type, routine, video_path):
    def load_user_config(config_path='user_config.json'):
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    shared_state = {"elapsed_time": 0.0, "distance": 0.0}
    treadmill = TreadmillControl()
    await treadmill.connect()
    await treadmill.request_control()

    speed_ratio_queue = asyncio.Queue(maxsize=1)
    await speed_ratio_queue.put(1.0)
    speed_queue = asyncio.Queue(maxsize=1)
    await speed_queue.put(initial_speed)
    distance_queue = asyncio.Queue(maxsize=1)
    await distance_queue.put(0.0)
    elapsed_time_queue = asyncio.Queue(maxsize=1)
    heart_rate_queue = asyncio.Queue(maxsize=1)
    ghost_gap_queue = asyncio.Queue(maxsize=1)
    exit_signal = asyncio.Queue(maxsize=1)

    print("[INFO] Launching video playback...")
    video_task = asyncio.create_task(
        play_video(
            video_path,
            speed_ratio_queue,
            speed_queue,
            distance_queue,
            elapsed_time_queue,
            ghost_gap_queue,
            heart_rate_queue,  # ✅ Add this
            exit_signal
        )
    )


    await asyncio.sleep(2.0)
    print("[INFO] Sending FTMS 'Start or Resume' command...")
    await treadmill.start_or_resume()
    print("[INFO] Waiting for treadmill's 5-second countdown...")
    await asyncio.sleep(5)

    print(f"[INFO] Setting initial speed = {initial_speed:.2f} km/h and incline = 1.0%")
    await treadmill.set_speed(initial_speed)
    await treadmill.set_incline(1.0)

    start_time = datetime.utcnow()
    total_minutes = sum(duration for duration, _ in routine)
    total_distance_km = sum(inc * duration / 60 for duration, inc in routine)
    avg_speed = total_distance_km / (total_minutes / 60)

    user_config = load_user_config()
    use_video_filename_speed = user_config.get("use_video_filename_speed", False)

    # Extract speed from video filename
    video_basename = os.path.basename(video_path)
    try:
        parts = os.path.splitext(video_basename)[0].split("_")
        video_speed = float(parts[1])
    except Exception:
        video_speed = initial_speed

    baseline_speed = video_speed if use_video_filename_speed else initial_speed

    pb_times = user_config.get("pb_times_minutes", {})
    goal_times = user_config.get("goal_times_minutes", {})

    pb_keys = set(map(int, pb_times.keys()))
    goal_keys = set(map(int, goal_times.keys()))
    available_keys = sorted(pb_keys | goal_keys)

    selected_key = None
    for key in reversed(available_keys):
        if total_distance_km >= key:
            selected_key = str(key)
            break

    ghost_runners = generate_competitors_with_profiles(total_minutes, avg_speed)

    for label, source in [("PB", pb_times), ("Goal", goal_times)]:
        minutes = source.get(selected_key)
        if minutes:
            distance_km = int(selected_key)
            speed = distance_km / (minutes / 60)
            ghost_runners.append({
                "base_name": f"{label} {selected_key}km",
                "speed_profile": [(0, speed)]
            })

    print(f"[DEBUG] Selected key: {selected_key}")
    print(f"[DEBUG] PB time: {pb_times.get(selected_key)} min")
    print(f"[DEBUG] Goal time: {goal_times.get(selected_key)} min")
    print(f"[DEBUG] Ghost runners: {[g['base_name'] for g in ghost_runners]}")

    start_tcx_file(start_time)

    loop = asyncio.get_event_loop()
    last_logged_distance = None
    last_distance = 0.0

    def callback(sender, data):
        nonlocal last_logged_distance, last_distance

        speed, distance, incline, elapsed_time, heart_rate = parse_treadmill_data(data, hr_value=treadmill.latest_hr)
        if incline is None: incline = 0.0
        if speed is None: speed = 0.0
        if distance is None: distance = 0.0
        if elapsed_time is None: elapsed_time = 0.0
        shared_state["elapsed_time"] = elapsed_time
        shared_state["distance"] = distance

        def safe_put(q, val):
            try: q.get_nowait()
            except asyncio.QueueEmpty: pass
            try: q.put_nowait(val)
            except asyncio.QueueFull: pass

        loop.call_soon_threadsafe(safe_put, speed_ratio_queue, speed / baseline_speed if baseline_speed > 0 else 1.0)
        loop.call_soon_threadsafe(safe_put, speed_queue, speed)
        loop.call_soon_threadsafe(safe_put, distance_queue, distance)
        loop.call_soon_threadsafe(safe_put, elapsed_time_queue, elapsed_time)
        loop.call_soon_threadsafe(safe_put, heart_rate_queue, heart_rate)


        timestamp = datetime.utcnow()
        append_tcx_trackpoint(timestamp, speed, distance, incline, heart_rate)
        last_distance = distance

        elapsed = (timestamp - start_time).total_seconds()
        user_distance_m = distance * 1000
        distance_rounded = round(user_distance_m, 1)

        if last_logged_distance != distance_rounded:
            last_logged_distance = distance_rounded
            ghost_gaps = {}
            for ghost in ghost_runners:
                ghost_distance_m = simulate_ghost_distance(ghost["speed_profile"], elapsed)
                current_speed = get_current_ghost_speed(ghost["speed_profile"], elapsed)
                ghost_name = f"{ghost['base_name']} ({current_speed:.1f} km/h)"
                gap = user_distance_m - ghost_distance_m
                ghost_gaps[ghost_name] = gap
            loop.call_soon_threadsafe(ghost_gap_queue.put_nowait, ghost_gaps)

    print("[INFO] Starting treadmill monitoring...")
    await treadmill.start_monitoring(callback)

    try:
        print("[INFO] Starting routine segments...")
        for idx, (duration, speed_increment) in enumerate(routine):
            print(f"[SEGMENT {idx}] Setting speed to {speed_increment:.2f} km/h for {duration:.1f} {'min' if routine_type == 'time' else 'km'}")
            await treadmill.set_speed(speed_increment)

            lap_start_time = datetime.utcnow()
            lap_start_distance = shared_state["distance"]
            start_new_lap(lap_start_time, lap_start_distance)

            if routine_type == "time":
                segment_start = shared_state["elapsed_time"]
                target = segment_start + duration * 60
                print(f"[SEGMENT] Time-based: {segment_start:.1f}s → {target:.1f}s")
            else:
                segment_start = shared_state["distance"]
                target = segment_start + duration
                print(f"[SEGMENT] Distance-based: {segment_start:.2f}km → {target:.2f}km")

            while True:
                await asyncio.sleep(0.2)
                current = shared_state["elapsed_time"] if routine_type == "time" else shared_state["distance"]
                if not exit_signal.empty():
                    print("[INFO] User exit detected.")
                    raise asyncio.CancelledError("User requested exit")
                if current >= target:
                    print("[SEGMENT] Segment complete.")
                    break

            lap_end_time = datetime.utcnow()
            lap_end_distance = shared_state["distance"]
            finalize_lap(lap_end_time, lap_end_distance)

    except asyncio.CancelledError:
        print("[INFO] Workout interrupted by user.")
    finally:
        print("[INFO] Cleaning up...")
        await video_task
        end_time = datetime.utcnow()
        final_distance = last_distance
        finalize_tcx_file()

        print("[INFO] Workout complete.")
        return {
            "start_time": start_time,
            "end_time": end_time,
            "final_distance": final_distance
        }
