import asyncio
from treadmill_control import TreadmillControl, parse_treadmill_data
from video_playback import play_video
from tcx_incremental import start_tcx_file, append_tcx_trackpoint, finalize_tcx_file
from virtual_competitors import generate_competitors_with_profiles
import time
from datetime import datetime
import json


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
    shared_state = {"elapsed_time": 0.0}
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
    last_logged_distance = None  # for ghost update throttling
    last_distance = 0.0  # to track the most recent treadmill distance

    def callback(sender, data):
        nonlocal last_logged_distance, last_distance

        speed, distance, incline, elapsed_time = parse_treadmill_data(data)
        if incline is None:
            incline = 0.0
        if speed is None:
            speed = 0.0
        if distance is None:
            distance = 0.0
        if elapsed_time is None:
            elapsed_time = 0.0

        #print(f"[CB] Speed: {speed:.2f} km/h, Distance: {distance:.2f} km, Incline: {incline:.2f} %, Time: {elapsed_time:.1f}s")
        shared_state["elapsed_time"] = elapsed_time



        loop.call_soon_threadsafe(speed_ratio_queue.put_nowait, speed / initial_speed if initial_speed > 0 else 1.0)
        loop.call_soon_threadsafe(speed_queue.put_nowait, speed)
        loop.call_soon_threadsafe(distance_queue.put_nowait, distance)
        loop.call_soon_threadsafe(elapsed_time_queue.put_nowait, elapsed_time)

        timestamp = datetime.utcnow()
        append_tcx_trackpoint(timestamp, speed, distance, incline)
        last_distance = distance  # Update the final known distance

        elapsed = (timestamp - start_time).total_seconds()
        user_distance_m = distance * 1000

        # Throttle ghost gap updates by rounding distance to the nearest 0.1 meter
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
        play_video(video_path, speed_ratio_queue, speed_queue, distance_queue, elapsed_time_queue, ghost_gap_queue, exit_signal)
    )

    try:
        print("[INFO] Starting routine segments...")
        for idx, (duration, speed_increment) in enumerate(routine):
            print(f"[SEGMENT {idx}] Setting speed to {speed_increment:.2f} km/h for {duration:.1f} min")
            await treadmill.set_speed(speed_increment)

            print("[SEGMENT] Waiting for treadmill-reported segment start time...")
            try:
                segment_start_time = shared_state["elapsed_time"]
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
        final_distance = last_distance
        finalize_tcx_file(start_time, end_time, final_distance)

        print("[INFO] Workout complete.")
        return {
            "start_time": start_time,
            "end_time": end_time,
            "final_distance": final_distance
        }
