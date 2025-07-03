import sys
import asyncio
import pygame
import json
import os
from RunRoutine import exercise_routine
from zwo_parser import load_all_zwo_routines

# Constants
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
HIGHLIGHT = (50, 200, 255)
FONT_SIZE = 36
MAX_VISIBLE = 10

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


def draw_menu(title, items, selected_idx, offset):
    screen.fill(BLACK)
    title_text = font.render(title, True, WHITE)
    screen.blit(title_text, (40, 30))

    for i in range(min(MAX_VISIBLE, len(items))):
        idx = offset + i
        if idx >= len(items):
            break
        color = HIGHLIGHT if idx == selected_idx else WHITE
        text = font.render(f"{idx + 1}. {items[idx]}", True, color)
        screen.blit(text, (60, 100 + i * 40))
    pygame.display.flip()


def display_pb_times(pb_times):
    screen.fill(BLACK)
    y = 60
    for km in ["1", "3", "5", "10", "21"]:
        if km in pb_times:
            txt = font.render(f"PB {km}km: {pb_times[km]:.1f} min", True, WHITE)
            screen.blit(txt, (60, y))
            y += 40
    pygame.display.flip()
    pygame.time.wait(3000)


def menu_select(title, items):
    selected = 0
    offset = 0
    draw_menu(title, items, selected, offset)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return selected
                elif event.key == pygame.K_DOWN:
                    selected = min(selected + 1, len(items) - 1)
                    if selected >= offset + MAX_VISIBLE:
                        offset += 1
                elif event.key == pygame.K_UP:
                    selected = max(selected - 1, 0)
                    if selected < offset:
                        offset = max(0, offset - 1)
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
        draw_menu(title, items, selected, offset)


def select_speed_dynamic(title, start_speed, min_speed=1.0, max_speed=20.0, step=0.1):
    speed = round(start_speed, 1)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return speed
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                elif event.key == pygame.K_UP:
                    speed = min(speed + step, max_speed)
                    speed = round(speed, 1)
                elif event.key == pygame.K_DOWN:
                    speed = max(speed - step, min_speed)
                    speed = round(speed, 1)

        screen.fill(BLACK)
        title_text = font.render(title, True, WHITE)
        screen.blit(title_text, (40, 30))

        speed_text = font.render(f"Speed: {speed:.1f} km/h", True, HIGHLIGHT)
        screen.blit(speed_text, (60, 150))

        info_text = font.render("Use UP/DOWN to change speed, ENTER to confirm, ESC to quit", True, WHITE)
        screen.blit(info_text, (60, 220))

        pygame.display.flip()


def show_status(message):
    screen.fill(BLACK)
    text = font.render(message, True, WHITE)
    screen.blit(text, (60, 300))
    pygame.display.flip()


async def main():
    user_config = load_user_config()
    pb_times = user_config.get("pb_times_minutes", {})
    display_pb_times(pb_times)

    pb_5k = pb_times.get("5", 25.0)
    zwo_speed = (5 * 60) / pb_5k  # speed in km/h

    show_status("Loading routines...")
    json_routines = load_routines('routines.json')
    zwo_routines = load_all_zwo_routines('routines', zwo_speed)
    routines = {**json_routines, **zwo_routines}
    routine_names = list(routines.keys())

    r_idx = menu_select("Select Routine", routine_names)
    routine_name = routine_names[r_idx]

    show_status("Loading videos...")
    videos = list_videos('videos')
    video_labels = [f"{v[1].capitalize()} ({v[2]} km/h {v[3]}km)" for v in videos]
    v_idx = menu_select("Select Video", video_labels)
    video_path = os.path.join('videos', videos[v_idx][0])

    if routine_name in zwo_routines:
        initial_speed = zwo_speed
    else:
        initial_speed = select_speed_dynamic("Select Initial Speed", zwo_speed)

    show_status("Preparing workout...")
    selected_routine = routines[routine_name]

    show_status("Starting video and routine...")
    await exercise_routine(
        initial_speed,
        [(d, initial_speed + inc) for d, inc in selected_routine],
        video_path
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        pygame.quit()
