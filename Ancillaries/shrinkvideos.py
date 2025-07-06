import cv2

def convert_video(input_path, output_path, width=640, height=380, codec='MJPG', fps=30):
    # Open the input video
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print("Error: Cannot open the video file.")
        return

    # Get the original frame rate if available
    original_fps = cap.get(cv2.CAP_PROP_FPS)
    if original_fps > 0:
        fps = min(fps, original_fps)

    # Define the codec and create VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*codec)
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Resize the frame
        resized_frame = cv2.resize(frame, (width, height))

        # Write the frame to the output video
        out.write(resized_frame)

    # Release everything
    cap.release()
    out.release()
    print(f"Video conversion complete. Saved to {output_path}")

# Example usage:
convert_video('forestrun_8.33_5.0.mp4', 'forestrun_8.33_5.0.avi')
