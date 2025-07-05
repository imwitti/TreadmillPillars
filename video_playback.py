import cv2
import asyncio
import time
from ghost_runner_hud import GhostRunnerHUD

async def play_video(video_path, speed_ratio_queue, speed_queue, distance_queue, start_time, ghost_gap_queue, exit_signal):
    cap = cv2.VideoCapture(video_path)
    last_known_speed = 0.0
    last_known_distance = 0.0
    last_ghost_gaps = {}

    speed_ratio = 1.0
    ghost_runner_hud = GhostRunnerHUD()
    confirm_exit = False
    esc_pressed_once = False

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if not speed_ratio_queue.empty():
            speed_ratio = speed_ratio_queue.get()
        if not speed_queue.empty():
            last_known_speed = speed_queue.get()
        if not distance_queue.empty():
            last_known_distance = distance_queue.get()
        if not ghost_gap_queue.empty():
            last_ghost_gaps = ghost_gap_queue.get()

        # HUD
        hud_speed_text = f"{last_known_speed:.1f} km/h"
        cv2.putText(frame, hud_speed_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        hud_distance_text = f"{last_known_distance:.0f} km"
        (text_width, text_height), _ = cv2.getTextSize(hud_distance_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.putText(frame, hud_distance_text, (frame.shape[1] - text_width - 10, text_height + 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        elapsed_time = time.time() - start_time
        hud_time_text = f"Time: {int(elapsed_time // 60)}:{int(elapsed_time % 60):02d}"
        cv2.putText(frame, hud_time_text, (10, frame.shape[0] - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        if last_ghost_gaps:
            y_offset = frame.shape[0] - 30
            for name, gap in sorted(last_ghost_gaps.items(), reverse=True):
                gap_text = f"{name}: {'+' if gap >= 0 else ''}{gap:.1f} m"
                (text_width, _), _ = cv2.getTextSize(gap_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                x_position = frame.shape[1] - text_width - 10
                cv2.putText(frame, gap_text, (x_position, y_offset),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                y_offset -= 25
            ghost_runner_hud.draw_ghost_runners(frame, last_ghost_gaps)

        # Exit confirmation
        if confirm_exit:
            overlay = frame.copy()
            cv2.rectangle(overlay, (200, 200), (600, 400), (0, 0, 0), -1)
            cv2.putText(overlay, "Exit workout?", (250, 270), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            cv2.putText(overlay, "Y = Yes, ESC = No", (250, 320), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            alpha = 0.7
            cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

        # Display
        cv2.namedWindow("Video", cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty("Video", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.imshow("Video", frame)

        key = cv2.waitKey(int(1000 / (30 * speed_ratio))) & 0xFF

        if not confirm_exit and key in [27, 8]:  # ESC or BACK
            confirm_exit = True
            esc_pressed_once = True

        elif confirm_exit:
            if key in [ord('y'), ord('Y'), 13, 10]:  # Y or Enter
                exit_signal.put(True)
                break
            elif key in [ord('n'), ord('N')]:  # N
                confirm_exit = False
            elif key in [27, 8] and esc_pressed_once:  # ESC again = No
                confirm_exit = False
                esc_pressed_once = False

        await asyncio.sleep(0)

    cap.release()
    cv2.destroyAllWindows()
