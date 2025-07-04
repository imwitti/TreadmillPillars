import pygame
from pathlib import Path
import os

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
HIGHLIGHT = (50, 200, 255)
LIGHT_HIGHLIGHT = (80, 80, 120)
FONT_SIZE = 36
TITLE_FONT_SIZE = 18
THUMBNAIL_SIZE = (120, 90)
ITEM_SPACING = 150
CAROUSEL_Y_POSITIONS = [120, 260, 400]
START_BUTTON_Y = 520

def load_thumbnail(path, size=THUMBNAIL_SIZE):
    p = Path(path)
    if not p.exists():
        return None
    try:
        img = pygame.image.load(str(p)).convert_alpha()
        return pygame.transform.smoothscale(img, size)
    except Exception:
        return None

def run_selection_ui(screen, font, routines, videos, start_speed=8.5):
    title_font = pygame.font.Font(None, TITLE_FONT_SIZE)

    routine_names = list(routines.keys())
    routine_thumbs = [load_thumbnail(f"Routines/{name}.png") for name in routine_names]

    video_files = [v[0] for v in videos]
    video_labels = [v[1] for v in videos]
    video_thumbs = [load_thumbnail(f"Videos/{Path(v[0]).with_suffix('.png').name}") for v in videos]

    speeds = [round(x * 0.1, 1) for x in range(10, 201)]
    start_speed = max(1.0, min(start_speed, 20.0))
    speed_idx = min(range(len(speeds)), key=lambda i: abs(speeds[i] - start_speed))

    selections = [0, 0, speed_idx]  # routine, video, speed
    offsets = [0, 0, max(0, speed_idx - 2)]
    focused = 0  # 0=routine, 1=video, 2=speed, 3=start

    clock = pygame.time.Clock()
    running = True

    while running:
        screen.fill(BLACK)
        screen_width = screen.get_width()

        for carousel_i in range(3):
            y = CAROUSEL_Y_POSITIONS[carousel_i]
            selected_idx = selections[carousel_i]
            offset = offsets[carousel_i]

            if carousel_i == 0:
                items = routine_names
                thumbs = routine_thumbs
                titles = routine_names
            elif carousel_i == 1:
                items = video_labels
                thumbs = video_thumbs
                titles = video_labels
            else:
                items = [f"{s:.1f} km/h" for s in speeds]
                thumbs = [None] * len(items)
                titles = items

            visible_range = range(offset, min(offset + 5, len(items)))
            total_width = (len(visible_range) - 1) * ITEM_SPACING
            start_x = (screen_width - total_width) // 2

            for i, idx in enumerate(visible_range):
                x = start_x + i * ITEM_SPACING
                is_selected = (idx == selected_idx)
                is_focused = (carousel_i == focused)

                label_text = titles[idx]
                label_surf = title_font.render(label_text, True, WHITE)
                label_rect = label_surf.get_rect(center=(x, y + THUMBNAIL_SIZE[1] // 2 + 20))

                if is_selected:
                    if carousel_i == 2:
                        # Speed background highlight behind label
                        bg_color = HIGHLIGHT if is_focused else LIGHT_HIGHLIGHT
                        padding = 10
                        bg_rect = pygame.Rect(
                            label_rect.left - padding,
                            label_rect.top - padding,
                            label_rect.width + 2 * padding,
                            label_rect.height + 2 * padding
                        )
                        pygame.draw.rect(screen, bg_color, bg_rect)
                    else:
                        # Routine/Video background highlight behind thumb + label
                        thumb_h = THUMBNAIL_SIZE[1]
                        full_rect = pygame.Rect(
                            x - THUMBNAIL_SIZE[0] // 2 - 10,
                            y - thumb_h // 2 - 10,
                            THUMBNAIL_SIZE[0] + 20,
                            thumb_h + 20 + 30  # padding + label space
                        )
                        bg_color = HIGHLIGHT if is_focused else LIGHT_HIGHLIGHT
                        pygame.draw.rect(screen, bg_color, full_rect)

                if carousel_i != 2:
                    if thumbs[idx]:
                        thumb_rect = thumbs[idx].get_rect(center=(x, y))
                        screen.blit(thumbs[idx], thumb_rect)
                    else:
                        rect = pygame.Rect(x - THUMBNAIL_SIZE[0] // 2, y - THUMBNAIL_SIZE[1] // 2,
                                           THUMBNAIL_SIZE[0], THUMBNAIL_SIZE[1])
                        pygame.draw.rect(screen, WHITE, rect, 2)

                screen.blit(label_surf, label_rect)

        # Draw START button
        start_rect = pygame.Rect(screen_width // 2 - 100, START_BUTTON_Y, 200, 50)
        if focused == 3:
            pygame.draw.rect(screen, HIGHLIGHT, start_rect)
            start_text = font.render("START", True, BLACK)
        else:
            pygame.draw.rect(screen, WHITE, start_rect, 2)
            start_text = font.render("START", True, WHITE)
        start_text_rect = start_text.get_rect(center=start_rect.center)
        screen.blit(start_text, start_text_rect)

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return None, None, None
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return None, None, None
                elif event.key == pygame.K_DOWN:
                    focused = (focused + 1) % 4
                elif event.key == pygame.K_UP:
                    focused = (focused - 1) % 4
                elif event.key == pygame.K_RIGHT:
                    if focused < 3:
                        max_idx = (len(routine_names) - 1 if focused == 0 else
                                   len(video_labels) - 1 if focused == 1 else
                                   len(speeds) - 1)
                        if selections[focused] < max_idx:
                            selections[focused] += 1
                            if selections[focused] >= offsets[focused] + 5:
                                offsets[focused] += 1
                elif event.key == pygame.K_LEFT:
                    if focused < 3 and selections[focused] > 0:
                        selections[focused] -= 1
                        if selections[focused] < offsets[focused]:
                            offsets[focused] = max(0, offsets[focused] - 1)
                elif event.key == pygame.K_RETURN:
                    if focused == 3:
                        routine = routine_names[selections[0]]
                        video_file = video_files[selections[1]]
                        speed = speeds[selections[2]]
                        return routine, os.path.join('videos', video_file), speed

        clock.tick(30)
