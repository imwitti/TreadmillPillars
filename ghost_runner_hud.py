import cv2
import numpy as np

class GhostRunnerHUD:
    def __init__(self, sprite_path='Animations/Runners.png', target_width=50, animation_speed=5):
        self.sprite_path = sprite_path
        self.target_width = target_width
        self.animation_speed = animation_speed  # frames to wait before advancing animation frame

        self.frames = []
        self.frame_idx = 0
        self.frame_counter = 0

        self._load_and_process_sprites()

    def _convert_black_on_white_to_white_on_transparent(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        inverted = cv2.bitwise_not(gray)
        _, alpha = cv2.threshold(inverted, 30, 255, cv2.THRESH_BINARY)
        b = np.ones_like(alpha) * 255
        g = np.ones_like(alpha) * 255
        r = np.ones_like(alpha) * 255
        rgba = cv2.merge([b, g, r, alpha])
        return rgba

    def _resize_sprite(self, frame, target_width=None):
        if target_width is None:
            target_width = self.target_width
        h, w = frame.shape[:2]
        scale = target_width / w
        new_size = (target_width, int(h * scale))
        return cv2.resize(frame, new_size, interpolation=cv2.INTER_AREA)

    def _tint_sprite_red(self, sprite):
        tinted = sprite.copy()
        if sprite.shape[2] == 4:
            b, g, r, a = cv2.split(tinted)
            r = np.clip(r.astype(np.int32) + 100, 0, 255).astype(np.uint8)
            g = np.clip(g.astype(np.int32) * 0.3, 0, 255).astype(np.uint8)
            b = np.clip(b.astype(np.int32) * 0.3, 0, 255).astype(np.uint8)
            return cv2.merge([b, g, r, a])
        return tinted

    def _overlay_sprite(self, background, sprite, x, y):
        h, w = sprite.shape[:2]
        if y < 0 or y + h > background.shape[0] or x < 0 or x + w > background.shape[1]:
            return

        if sprite.shape[2] == 4:
            alpha_s = sprite[:, :, 3] / 255.0
            alpha_s = alpha_s[..., None]
            alpha_b = 1.0 - alpha_s
            for c in range(3):
                background[y:y+h, x:x+w, c] = (alpha_s[:, :, 0] * sprite[:, :, c] +
                                               alpha_b[:, :, 0] * background[y:y+h, x:x+w, c])
        else:
            background[y:y+h, x:x+w] = sprite

    def _load_and_process_sprites(self):
        img = cv2.imread(self.sprite_path, cv2.IMREAD_UNCHANGED)
        if img is None:
            raise FileNotFoundError(f"Could not load sprite image '{self.sprite_path}'")

        h, w = img.shape[:2]
        half_h, half_w = h // 2, w // 2

        center_crop_width = 205
        crop_x_start = half_w // 2 - center_crop_width // 2
        crop_x_end = crop_x_start + center_crop_width

        quadrants = [
            img[0:half_h, crop_x_start:crop_x_end],
            img[0:half_h, half_w + crop_x_start:half_w + crop_x_end],
            img[half_h:h, crop_x_start:crop_x_end],
            img[half_h:h, half_w + crop_x_start:half_w + crop_x_end]
        ]

        processed = []
        for f in quadrants:
            rgba = self._convert_black_on_white_to_white_on_transparent(f)
            resized = self._resize_sprite(rgba)
            processed.append(resized)

        self.frames = processed

    def draw_ghost_runners(self, frame, ghost_gaps):
        #print("Received ghost_gaps:")
        if not isinstance(ghost_gaps, dict):
            print("  ghost_gaps is not a dictionary or is None")
            return

        selected_ghosts = sorted(ghost_gaps.items(), reverse=True)[:3]

        # Update animation frame counter
        self.frame_counter += 1
        if self.frame_counter % self.animation_speed == 0:
            self.frame_idx = (self.frame_idx + 1) % len(self.frames)

        base_sprite = self.frames[self.frame_idx]
        sprite_h, sprite_w = base_sprite.shape[:2]

        num_ghost_lines = len(selected_ghosts)
        top_ghost_text_y = frame.shape[0] - 30 - (num_ghost_lines - 1) * 25
        base_y = top_ghost_text_y - sprite_h - 10
        start_x = frame.shape[1] - (sprite_w * 3) - (5 * 2) - 20

        for i, (name, gap) in enumerate(selected_ghosts):
            try:
                gap = float(gap)
                if gap > 50 or gap < -400:
                    continue  # skip ghosts too far behind or ahead

                ratio = max(0.0, min(1.0, 1 + (gap / 400.0)))
                width = max(5, int(self.target_width * ratio))
                sprite = self._resize_sprite(base_sprite, target_width=width)

                if gap > 0:
                    sprite = self._tint_sprite_red(sprite)

                x = start_x + i * (sprite.shape[1] + 5)
                self._overlay_sprite(frame, sprite, x, base_y)
            except Exception as e:
                print(f"Error processing ghost '{name}': {e}")
