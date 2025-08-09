import os
import cv2

def convert_all_mp4_to_avi_opencv(folder=".", target_width=640, target_height=360, fps=15, overwrite=False):
    fourcc = cv2.VideoWriter_fourcc(*'MJPG')  # MJPG codec for avi

    for filename in os.listdir(folder):
        if filename.lower().endswith('.mp4'):
            input_path = os.path.join(folder, filename)
            output_path = os.path.join(folder, os.path.splitext(filename)[0] + '.avi')

            if not overwrite and os.path.exists(output_path):
                print(f"✅ Skipping (already exists): {output_path}")
                continue

            print(f"🎞️ Converting: {filename} → {os.path.basename(output_path)}")

            cap = cv2.VideoCapture(input_path)
            if not cap.isOpened():
                print(f"❌ Failed to open {input_path}")
                continue

            out = cv2.VideoWriter(output_path, fourcc, fps, (target_width, target_height))

            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frame_resized = cv2.resize(frame, (target_width, target_height))
                out.write(frame_resized)

            cap.release()
            out.release()
            print(f"✅ Done: {output_path}")

if __name__ == "__main__":
    current_folder = os.path.dirname(os.path.abspath(__file__))
    convert_all_mp4_to_avi_opencv(folder=current_folder, overwrite=False)
