import cv2
import os

# Settings
TARGET_FPS = 15
INPUT_EXT = '.mp4'
OUTPUT_FOLDER = '15fps'

def convert_to_15fps(input_path, output_path):
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print(f"❌ Error: Cannot open video file {input_path}")
        return

    original_fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = int(round(original_fps / TARGET_FPS))
    if frame_interval <= 0:
        frame_interval = 1

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Keep MP4 format

    out = cv2.VideoWriter(output_path, fourcc, TARGET_FPS, (width, height))

    frame_count = 0
    written_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % frame_interval == 0:
            out.write(frame)
            written_count += 1

        frame_count += 1

    cap.release()
    out.release()
    print(f"✅ Converted: {os.path.basename(input_path)} → {os.path.basename(output_path)} "
          f"({written_count} frames at {TARGET_FPS} fps)")

if __name__ == "__main__":
    current_dir = os.getcwd()
    output_dir = os.path.join(current_dir, OUTPUT_FOLDER)
    os.makedirs(output_dir, exist_ok=True)

    mp4_files = [f for f in os.listdir(current_dir) if f.lower().endswith(INPUT_EXT)]
    if not mp4_files:
        print("No MP4 files found in this folder.")
    else:
        print(f"Found {len(mp4_files)} MP4 files. Starting conversion...\n")
        for mp4_file in mp4_files:
            input_path = os.path.join(current_dir, mp4_file)
            output_path = os.path.join(output_dir, mp4_file)
            convert_to_15fps(input_path, output_path)

        print("\n🎯 All conversions complete. Files saved in:", output_dir)
