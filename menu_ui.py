import pygame
from pathlib import Path
import os

# Colors
WHITE = (255, 255, 255)
BLACK = (20, 20, 20)
HIGHLIGHT = (50, 200, 255)
LIGHT_HIGHLIGHT = (80, 120, 160)
SHADOW = (10, 10, 10)
GRADIENT_START = (30, 30, 40)
GRADIENT_END = (10, 10, 20)

# Sizes
FONT_SIZE = 18
TITLE_FONT_SIZE = 12
THUMBNAIL_SIZE = (140, 100)
SPEED_THUMBNAIL_SIZE = (120, 15)
ITEM_SPACING = 160
CAROUSEL_Y_POSITIONS = [120, 280, 420]
START_BUTTON_Y = 500

# Load Roboto fonts
def load_fonts():
    fonts = {}
    fonts['regular'] = pygame.font.Font("fonts/Roboto-Regular.ttf", FONT_SIZE)
    fonts['bold'] = pygame.font.Font("fonts/Roboto-Bold.ttf", FONT_SIZE)
    fonts['title'] = pygame.font.Font("fonts/Roboto-Bold.ttf", TITLE_FONT_SIZE)
    fonts['start'] = pygame.font.Font("fonts/Roboto-Bold.ttf", 24)
    return fonts

def load_thumbnail(path, size=THUMBNAIL_SIZE):
    p = Path(path)
    if not p.exists():
        return None
    try:
        img = pygame.image.load(str(p)).convert_alpha()
        return pygame.transform.smoothscale(img, size)
    except Exception:
        return None

def draw_vertical_gradient(surface, color_start, color_end):
    height = surface.get_height()
    for y in range(height):
        ratio = y / height
        r = int(color_start[0] * (1 - ratio) + color_end[0] * ratio)
        g = int(color_start[1] * (1 - ratio) + color_end[1] * ratio)
        b = int(color_start[2] * (1 - ratio) + color_end[2] * ratio)
        pygame.draw.line(surface, (r, g, b), (0, y), (surface.get_width(), y))

def run_selection_ui(screen, routines, videos, start_speed=8.5):
    fonts = load_fonts()

    routine_names = list(routines.keys())
    routine_thumbs = [load_thumbnail(f"routines/{name}.png") for name in routine_names]

    video_files = [v[0] for v in videos]
    video_labels = [v[1] for v in videos]
    video_thumbs = [load_thumbnail(f"videos/{Path(v[0]).with_suffix('.png').name}") for v in videos]

    speeds = [round(x * 0.1, 1) for x in range(10, 201)]
    start_speed = max(1.0, min(start_speed, 20.0))
    speed_idx = min(range(len(speeds)), key=lambda i: abs(speeds[i] - start_speed))

    selections = [0, 0, speed_idx]
    offsets = [0, 0, max(0, speed_idx - 2)]
    focused = 0

    clock = pygame.time.Clock()
    running = True

    # Load and scale background image
    background_path = "assets/background.jpg"
    background_img = pygame.image.load(background_path).convert()
    background_img = pygame.transform.scale(background_img, screen.get_size())

    while running:
        screen.blit(background_img, (0, 0))
        screen_width = screen.get_width()

        for carousel_i in range(3):
            y = CAROUSEL_Y_POSITIONS[carousel_i]
            selected_idx = selections[carousel_i]
            offset = offsets[carousel_i]

            if carousel_i == 0:
                items = routine_names
                thumbs = routine_thumbs
                titles = routine_names
                thumb_size = THUMBNAIL_SIZE
            elif carousel_i == 1:
                items = video_labels
                thumbs = video_thumbs
                titles = video_labels
                thumb_size = THUMBNAIL_SIZE
            else:
                items = [f"{s:.1f} km/h" for s in speeds]
                thumbs = [None] * len(items)
                titles = items
                thumb_size = SPEED_THUMBNAIL_SIZE

            visible_range = range(offset, min(offset + 5, len(items)))
            total_width = (len(visible_range) - 1) * ITEM_SPACING
            start_x = (screen_width - total_width) // 2

            for i, idx in enumerate(visible_range):
                x = start_x + i * ITEM_SPACING
                is_selected = (idx == selected_idx)
                is_focused = (carousel_i == focused)

                label_text = titles[idx]
                font_to_use = fonts['bold'] if is_selected else fonts['regular']
                label_surf = font_to_use.render(label_text, True, WHITE)
                label_rect = label_surf.get_rect(center=(x, y + thumb_size[1] // 2 + 25))

                if is_selected:
                    shadow_rect = pygame.Rect(
                        x - thumb_size[0] // 2 - 15,
                        y - thumb_size[1] // 2 - 15,
                        thumb_size[0] + 30,
                        thumb_size[1] + 70
                    )
                    shadow_surf = pygame.Surface(shadow_rect.size, pygame.SRCALPHA)
                    shadow_surf.fill((*SHADOW, 100))
                    screen.blit(shadow_surf, shadow_rect.topleft)

                    highlight_color = HIGHLIGHT if is_focused else LIGHT_HIGHLIGHT
                    highlight_surf = pygame.Surface((thumb_size[0] + 20, thumb_size[1] + 60), pygame.SRCALPHA)
                    alpha = 180 if is_focused else 100
                    highlight_surf.fill((*highlight_color, alpha))
                    screen.blit(highlight_surf, (x - thumb_size[0] // 2 - 10, y - thumb_size[1] // 2 - 10))

                if carousel_i != 2 and thumbs[idx]:
                    thumb_rect = thumbs[idx].get_rect(center=(x, y))
                    screen.blit(thumbs[idx], thumb_rect)
                elif carousel_i != 2:
                    rect = pygame.Rect(x - thumb_size[0] // 2, y - thumb_size[1] // 2,
                                       thumb_size[0], thumb_size[1])
                    pygame.draw.rect(screen, WHITE, rect, 2)

                screen.blit(label_surf, label_rect)

        # START button
        start_rect = pygame.Rect(screen_width // 2 - 120, START_BUTTON_Y, 240, 60)
        shadow_surf = pygame.Surface((start_rect.width + 10, start_rect.height + 10), pygame.SRCALPHA)
        shadow_surf.fill((*SHADOW, 150))
        screen.blit(shadow_surf, (start_rect.x + 5, start_rect.y + 5))

        if focused == 3:
            pygame.draw.rect(screen, HIGHLIGHT, start_rect, border_radius=8)
            start_text = fonts['start'].render("START", True, BLACK)
        else:
            pygame.draw.rect(screen, WHITE, start_rect, 3, border_radius=8)
            start_text = fonts['start'].render("START", True, WHITE)

        screen.blit(start_text, start_text.get_rect(center=start_rect.center))
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
                        max_idx = (
                            len(routine_names) - 1 if focused == 0 else
                            len(video_labels) - 1 if focused == 1 else
                            len(speeds) - 1
                        )
                        if selections[focused] < max_idx:
                            selections[focused] += 1
                            if selections[focused] >= offsets[focused] + 5:
                                offsets[focused] += 1
                elif event.key == pygame.K_LEFT:
                    if focused < 3 and selections[focused] > 0:
                        selections[focused] -= 1
                        if selections[focused] < offsets[focused]:
                            offsets[focused] = max(0, offsets[focused] - 1)
                elif event.key == pygame.K_RETURN and focused == 3:
                    routine = routine_names[selections[0]]
                    video_file = video_files[selections[1]]
                    speed = speeds[selections[2]]
                    return routine, os.path.join('videos', video_file), speed

        clock.tick(30)
