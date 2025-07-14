import asyncio
from treadmill_control import TreadmillControl, parse_treadmill_data
from video_playback import play_video
from tcx_incremental import start_tcx_file, append_tcx_trackpoint, finalize_tcx_file
from virtual_competitors import generate_competitors_with_profiles
from datetime import datetime
from tcx_postprocess import post_process_tcx_with_gpx


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


async def exercise_routine(initial_speed, routine_type, routine, video_path):
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
            exit_signal
        )
    )

    # Wait briefly to allow video first frame to appear
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
    ghost_runners = generate_competitors_with_profiles(total_minutes, avg_speed)
    start_tcx_file(start_time)

    loop = asyncio.get_event_loop()
    last_logged_distance = None
    last_distance = 0.0

    def callback(sender, data):
        nonlocal last_logged_distance, last_distance

        speed, distance, incline, elapsed_time = parse_treadmill_data(data)
        if incline is None: incline = 0.0
        if speed is None: speed = 0.0
        if distance is None: distance = 0.0
        if elapsed_time is None: elapsed_time = 0.0

        shared_state["elapsed_time"] = elapsed_time
        shared_state["distance"] = distance

        loop.call_soon_threadsafe(speed_ratio_queue.put_nowait, speed / initial_speed if initial_speed > 0 else 1.0)
        loop.call_soon_threadsafe(speed_queue.put_nowait, speed)
        loop.call_soon_threadsafe(distance_queue.put_nowait, distance)
        loop.call_soon_threadsafe(elapsed_time_queue.put_nowait, elapsed_time)

        timestamp = datetime.utcnow()
        append_tcx_trackpoint(timestamp, speed, distance, incline)
        last_distance = distance

        elapsed = (timestamp - start_time).total_seconds()
        user_distance_m = distance * 1000
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

    try:
        print("[INFO] Starting routine segments...")
        for idx, (duration, speed_increment) in enumerate(routine):
            print(f"[SEGMENT {idx}] Setting speed to {speed_increment:.2f} km/h for {duration:.1f} {'min' if routine_type == 'time' else 'km'}")
            await treadmill.set_speed(speed_increment)

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

    except asyncio.CancelledError:
        print("[INFO] Workout interrupted by user.")
    finally:
        print("[INFO] Cleaning up...")

        await video_task

        end_time = datetime.utcnow()
        final_distance = last_distance
        finalize_tcx_file()
        # Derive GPX path from video filename
        finalize_tcx_file()

        video_basename = os.path.splitext(os.path.basename(video_path))[0]
        video_dir = os.path.dirname(video_path)
        gpx_file = os.path.join(video_dir, f"{video_basename}.gpx")

        if os.path.exists(gpx_file):
            print(f"[INFO] Found GPX route at {gpx_file}, post-processing TCX...")
            post_process_tcx_with_gpx(tcx_filename, gpx_file)
        else:
            print(f"[WARN] No GPX route found at {gpx_file}, skipping post-processing.")
        print("[INFO] Workout complete.")
        return {
            "start_time": start_time,
            "end_time": end_time,
            "final_distance": final_distance
        }
