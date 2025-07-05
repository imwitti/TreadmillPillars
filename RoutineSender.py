import sys
import asyncio
import pygame
import json
import os
import subprocess
from pathlib import Path
from post_workout_stats import show_post_workout_stats
from RunRoutine import exercise_routine
from zwo_parser import load_all_zwo_routines
from menu_ui import run_selection_ui

# Constants
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
FONT_SIZE = 36

pygame.init()
screen = pygame.display.set_mode((800, 600), pygame.FULLSCREEN)
pygame.display.set_caption("Routine Selector")
font = pygame.font.Font(None, FONT_SIZE)


def load_user_config(config_path='user_config.json'):
    try:
        with open(config_path, 'r') as file:
            return json.load(file)
    except Exception:
        return {}


def load_routines(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception:
        return {}


def list_videos(video_folder):
    videos = []
    for file in os.listdir(video_folder):
        if file.lower().endswith('.mp4'):
            name, speed, distance = parse_video_title(file)
            videos.append((file, name, float(speed), float(distance)))
    return videos


def parse_video_title(title):
    base = os.path.splitext(title)[0]
    parts = base.split('_')
    return parts[0].lower(), parts[1], parts[2]


def run_thumbnail_generators():
    print("Generating thumbnails...")
    routines_script = Path('routines') / 'generate_zwo_thumbnail.py'
    if routines_script.exists():
        subprocess.run([sys.executable, str(routines_script.name)], cwd='routines')
    else:
        print("ZWO thumbnail generator not found.")

    videos_script = Path('videos') / 'video_thumbnails.py'
    if videos_script.exists():
        subprocess.run([sys.executable, str(videos_script.name)], cwd='videos')
    else:
        print("Video thumbnail generator not found.")


def display_pb_times(screen, font, pb_times):
    # Load and scale the background image
    background_image = pygame.image.load("assets/background.jpg").convert()
    background_image = pygame.transform.scale(background_image, screen.get_size())

    # Draw the background
    screen.blit(background_image, (0, 0))
    
    y = 100  # starting y-position for text
    screen_width = screen.get_width()

    for km_str in ["1", "3", "5", "10", "21"]:
        if km_str in pb_times:
            km = float(km_str)
            speed = km / (pb_times[km_str] / 60)  # speed in km/h
            
            text_str = f"PB {km_str}km: {pb_times[km_str]:.1f} min Speed: {speed:.1f} kmph"
            txt_surface = font.render(text_str, True, (255, 255, 255))  # white text
            text_rect = txt_surface.get_rect(center=(screen_width // 2, y))
            
            screen.blit(txt_surface, text_rect)
            y += 50  # vertical spacing between lines

    pygame.display.flip()
    pygame.time.wait(5000)



def show_status(screen, font, message):
    screen.fill(BLACK)
    text = font.render(message, True, WHITE)
    rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
    screen.blit(text, rect)
    pygame.display.flip()


async def main():
    user_config = load_user_config()
    pb_times = user_config.get("pb_times_minutes", {})
    display_pb_times(screen, font, pb_times)

    pb_5k = pb_times.get("5", 25.0)
    zwo_speed = (5 * 60) / pb_5k  # speed in km/h

    show_status(screen, font, "Generating thumbnails...")
    run_thumbnail_generators()

    show_status(screen, font, "Loading routines...")
    json_routines = load_routines('routines.json')
    zwo_routines = load_all_zwo_routines('routines', zwo_speed)
    routines = {**json_routines, **zwo_routines}

    show_status(screen, font, "Loading videos...")
    videos = list_videos('videos')
    video_data = [(v[0], f"{v[1].capitalize()} ({v[2]} km/h {v[3]}km)") for v in videos]

    routine_name, video_path, selected_speed = run_selection_ui(screen, routines, video_data, zwo_speed, pb_times=pb_times)

    if not all([routine_name, video_path, selected_speed]):
        pygame.quit()
        return

    show_status(screen, font, "Preparing workout...")
    selected_routine = routines[routine_name]

    show_status(screen, font, "Starting video and routine...")
    result = await exercise_routine(
         selected_speed,
         [(d, selected_speed + inc) for d, inc in selected_routine],
         str(video_path)
    )

    if result:
         show_post_workout_stats(
         workout_data=result["workout_data"],
         start_time=result["start_time"],
         end_time=result["end_time"]
         # tcx_filename=result.get("tcx_filename")  # Optional if you add it later
         )



if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        pygame.quit()
