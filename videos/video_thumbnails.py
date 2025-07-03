import cv2
from pathlib import Path

def generate_video_thumbnail(video_path, timestamp=1.0):
    """
    Generates a thumbnail image for a given .mp4 video file at a specified timestamp.
    """
    video_file = Path(video_path)
    if not video_file.is_file() or video_file.suffix.lower() != '.mp4':
        print(f"Invalid .mp4 file: {video_path}")
        return

    thumbnail_path = video_file.with_suffix('.png')
    if thumbnail_path.exists():
        print(f"Thumbnail already exists: {thumbnail_path}")
        return

    # Open the video file
    cap = cv2.VideoCapture(str(video_file))
    if not cap.isOpened():
        print(f"Error opening video file: {video_path}")
        return

    # Calculate the frame number at the specified timestamp
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_number = int(fps * timestamp)

    # Set the video to the desired frame
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

    # Read the frame
    ret, frame = cap.read()
    if ret:
        # Save the frame as an image
        cv2.imwrite(str(thumbnail_path), frame)
        print(f"Thumbnail created: {thumbnail_path}")
    else:
        print(f"Error reading frame at {timestamp} seconds")

    # Release the video capture object
    cap.release()

if __name__ == "__main__":
    current_dir = Path(".")
    mp4_files = list(current_dir.glob("*.mp4"))

    if not mp4_files:
        print("No .mp4 files found in the current directory.")
    else:
        for video_file in mp4_files:
            generate_video_thumbnail(video_file)
