import pygame
from datetime import timedelta

def show_post_workout_stats(workout_data, start_time, end_time, tcx_filename=None):

    pygame.init()
    screen = pygame.display.set_mode((800, 600), pygame.FULLSCREEN)
    pygame.display.set_caption("Workout Summary")
    font = pygame.font.Font(None, 48)
    small_font = pygame.font.Font(None, 36)

    # Calculate stats
    duration = end_time - start_time
    total_seconds = duration.total_seconds()
    total_minutes = total_seconds / 60
    total_distance_km = workout_data[-1]["distance"] if workout_data else 0.0
    avg_pace_min_per_km = total_minutes / total_distance_km if total_distance_km > 0 else 0

    # Prepare text lines
    lines = [
        "Workout Summary",
        f"Duration: {str(timedelta(seconds=int(total_seconds)))}",
        f"Distance: {total_distance_km:.2f} km",
        f"Avg Pace: {avg_pace_min_per_km:.2f} min/km",
        "",
        "Press any key to exit..."
    ]

    screen.fill((0, 0, 0))
    y = 100
    for line in lines:
        text = font.render(line, True, (255, 255, 255)) if line else small_font.render(" ", True, (255, 255, 255))
        rect = text.get_rect(center=(screen.get_width() // 2, y))
        screen.blit(text, rect)
        y += 60

    pygame.display.flip()

    # Wait for any key press
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN or event.type == pygame.QUIT:
                waiting = False
                break
    pygame.quit()
