import cv2
import asyncio
import time
import platform
from ghost_runner_hud import GhostRunnerHUD

def get_screen_resolution():
    if platform.system() == "Windows":
        return 1280, 720  # You can change this as needed
    try:
        import subprocess
        output = subprocess.check_output("xrandr | grep '*' | awk '{print $1}'", shell=True)
        width, height = output.decode().strip().split('x')
        return int(width), int(height)
    except Exception as e:
        print("Could not determine screen resolution:", e)
        return 1280, 720

async def play_video(video_path, speed_ratio_queue, speed_queue, distance_queue, elapsed_time_queue, ghost_gap_queue, exit_signal):
    cap = cv2.VideoCapture(video_path)
    last_known_speed = 0.0
    last_known_distance = 0.0
    elapsed_time_seconds = 0
    last_ghost_gaps = {}
    speed_ratio = 1.0
    ghost_runner_hud = GhostRunnerHUD()
    confirm_exit = False
    esc_pressed_once = False

    screen_width, screen_height = get_screen_resolution()

    # Create fullscreen window once
    cv2.namedWindow("Video", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("Video", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        try:
            speed_ratio = speed_ratio_queue.get_nowait()
        except asyncio.QueueEmpty:
            pass

        try:
            last_known_speed = speed_queue.get_nowait()
        except asyncio.QueueEmpty:
            pass

        try:
            last_known_distance = distance_queue.get_nowait()
        except asyncio.QueueEmpty:
            pass

        try:
            last_ghost_gaps = ghost_gap_queue.get_nowait()
        except asyncio.QueueEmpty:
            pass

        # HUD: Speed
        hud_speed_text = f"{last_known_speed:.1f} km/h"
        cv2.putText(frame, hud_speed_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # HUD: Distance
        hud_distance_text = f"{last_known_distance:.2f} km"
        (text_width, text_height), _ = cv2.getTextSize(hud_distance_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.putText(frame, hud_distance_text, (frame.shape[1] - text_width - 10, text_height + 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # HUD: Elapsed Time
        try:
            elapsed_time_seconds = elapsed_time_queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
        hud_time_text = f"Time: {int(elapsed_time_seconds // 60)}:{int(elapsed_time_seconds % 60):02d}"
        cv2.putText(frame, hud_time_text, (10, frame.shape[0] - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # HUD: Ghost Gaps (split left/right)
        if last_ghost_gaps:
            left_labels = []
            right_labels = []

            for name, gap in last_ghost_gaps.items():
                if name.startswith("PB") or name.startswith("Goal"):
                    left_labels.append((name, gap))
                else:
                    right_labels.append((name, gap))

            
            # Draw left-aligned labels (above time label)
            y_offset_left = frame.shape[0] - 60  # 30 for time label + 30 buffer
            for name, gap in sorted(left_labels, key=lambda x: x[1], reverse=True):
                gap_text = f"{name}: {'+' if gap >= 0 else ''}{gap:.1f} m"
                cv2.putText(frame, gap_text, (10, y_offset_left),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                y_offset_left -= 25



            # Draw right-aligned labels
            y_offset_right = frame.shape[0] - 30
            for name, gap in sorted(right_labels, key=lambda x: x[1], reverse=True):
                gap_text = f"{name}: {'+' if gap >= 0 else ''}{gap:.1f} m"
                (text_width, _), _ = cv2.getTextSize(gap_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                x_position = frame.shape[1] - text_width - 10
                cv2.putText(frame, gap_text, (x_position, y_offset_right),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                y_offset_right -= 25

            ghost_runner_hud.draw_ghost_runners(frame, last_ghost_gaps)


        # Exit Confirmation Overlay
        if confirm_exit:
            overlay = frame.copy()
            cv2.rectangle(overlay, (200, 200), (600, 400), (0, 0, 0), -1)
            cv2.putText(overlay, "Exit workout?", (250, 270), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            cv2.putText(overlay, "Y = Yes, ESC = No", (250, 320), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            alpha = 0.7
            cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

        # Resize to screen resolution
        frame = cv2.resize(frame, (screen_width, screen_height))

        # Show frame
        cv2.imshow("Video", frame)
        fps = cap.get(cv2.CAP_PROP_FPS) or 15

        safe_ratio = max(speed_ratio, 0.1)  # prevent zero or too slow
        key = cv2.waitKey(int(1000 / (fps * safe_ratio))) & 0xFF


        if not confirm_exit and key in [27, 8, 38]:  # ESC or BACK
            confirm_exit = True
            esc_pressed_once = True
        elif confirm_exit:
            if key in [ord('y'), ord('Y'), 13, 10]:  # Y or Enter
                await exit_signal.put(True)
                break
            elif key in [ord('n'), ord('N')]:
                confirm_exit = False
            elif key in [27, 8, 38] and esc_pressed_once:
                confirm_exit = False
                esc_pressed_once = False

        await asyncio.sleep(0)

    cap.release()
    cv2.destroyAllWindows()
