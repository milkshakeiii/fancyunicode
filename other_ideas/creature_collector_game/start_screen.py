#!/usr/bin/env python3
"""
Start screen for Creature Collector game.
Uses the Yendor scene with animated text reveal and lighting effects.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame
import pyunicodegame
from pyunicodegame._sprites import Animation

# Import from generated files
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'generated_files'))
from staff import SPRITE_DEFS as staff_SPRITES, create_sprite as staff_create_sprite


# Screen dimensions
WIDTH = 60
HEIGHT = 21
BG_COLOR = (10, 10, 20, 255)

# Text data - (x, y, char) for each character
LINE1_CHARS = [
    (15, 1, '𝐈'), (16, 1, '𝐭'), (18, 1, '𝐢'), (19, 1, '𝐬'),
    (21, 1, '𝐬'), (22, 1, '𝐚'), (23, 1, '𝐢'), (24, 1, '𝐝'),
    (26, 1, '𝐭'), (27, 1, '𝐡'), (28, 1, '𝐚'), (29, 1, '𝐭'),
    (31, 1, '𝐭'), (32, 1, '𝐡'), (33, 1, '𝐞'), (34, 1, '𝐫'), (35, 1, '𝐞'),
    (37, 1, '𝐢'), (38, 1, '𝐬'),
    (40, 1, '𝓜'), (41, 1, '𝓪'), (42, 1, '𝓰'), (43, 1, '𝓲'), (44, 1, '𝓬'), (45, 1, '𝓴'),
]

LINE2_CHARS = [
    (12, 2, '𝐂'), (13, 2, '𝐨'), (14, 2, '𝐧'), (15, 2, '𝐭'), (16, 2, '𝐚'),
    (17, 2, '𝐢'), (18, 2, '𝐧'), (19, 2, '𝐞'), (20, 2, '𝐝'),
    (22, 2, '𝐰'), (23, 2, '𝐢'), (24, 2, '𝐭'), (25, 2, '𝐡'), (26, 2, '𝐢'), (27, 2, '𝐧'),
    (29, 2, '𝐭'), (30, 2, '𝐡'), (31, 2, '𝐞'),
    (33, 2, '𝓢'), (34, 2, '𝓽'), (35, 2, '𝓪'), (36, 2, '𝓯'), (37, 2, '𝓯'),
    (39, 2, '𝓸'), (40, 2, '𝓯'),
    (42, 2, '𝓨'), (43, 2, '𝓮'), (44, 2, '𝓷'), (45, 2, '𝓭'), (46, 2, '𝓸'), (47, 2, '𝓻'),
]

LINE3_CHARS = [
    (10, 18, '𝐖'), (11, 18, '𝐡'), (12, 18, '𝐢'), (13, 18, '𝐜'), (14, 18, '𝐡'),
    (16, 18, '𝐡'), (17, 18, '𝐚'), (18, 18, '𝐬'),
    (20, 18, '𝐭'), (21, 18, '𝐡'), (22, 18, '𝐞'),
    (24, 18, '𝐩'), (25, 18, '𝐨'), (26, 18, '𝐰'), (27, 18, '𝐞'), (28, 18, '𝐫'),
    (30, 18, '𝐭'), (31, 18, '𝐨'),
    (33, 18, '𝐫'), (34, 18, '𝐞'), (35, 18, '𝐜'), (36, 18, '𝐨'), (37, 18, '𝐦'),
    (38, 18, '𝐦'), (39, 18, '𝐞'), (40, 18, '𝐧'), (41, 18, '𝐝'),
    (43, 18, '𝓡'), (44, 18, '𝓮'), (45, 18, '𝓪'), (46, 18, '𝓼'), (47, 18, '𝓸'), (48, 18, '𝓷'),
]

LINE4_CHARS = [
    (15, 19, '𝐓'), (16, 19, '𝐨'),
    (18, 19, '𝐚'),
    (20, 19, '𝐝'), (21, 19, '𝐚'), (22, 19, '𝐫'), (23, 19, '𝐤'),
    (25, 19, '𝐚'), (26, 19, '𝐧'), (27, 19, '𝐝'),
    (29, 19, '𝐭'), (30, 19, '𝐫'), (31, 19, '𝐮'), (32, 19, '𝐭'), (33, 19, '𝐡'),
    (34, 19, '𝐥'), (35, 19, '𝐞'), (36, 19, '𝐬'), (37, 19, '𝐬'),
    (39, 19, '𝐰'), (40, 19, '𝐨'), (41, 19, '𝐫'), (42, 19, '𝐥'), (43, 19, '𝐝'),
]


class StartScreen:
    def __init__(self):
        self.root = pyunicodegame.init(
            "The Staff of Yendor",
            width=WIDTH,
            height=HEIGHT,
            bg=BG_COLOR,
            font_name="unifont"
        )

        # Start in fullscreen
        pyunicodegame._toggle_fullscreen()

        # Animation state
        self.phase = 0  # 0=line1, 1=line2, 2=staff_anim, 3=bottom_text, 4=done
        self.char_index = 0
        self.time_accumulator = 0.0
        self.char_reveal_speed = 0.06  # seconds per character

        # Track revealed characters for each line
        self.line1_revealed = 0
        self.line2_revealed = 0
        self.line3_revealed = 0
        self.line4_revealed = 0

        # Staff sprite (created but hidden initially)
        self.staff_sprite = None
        self.staff_visible = False
        self.staff_animation_started = False
        self.staff_animation_done = False

        # Staff top light (appears after animation)
        self.staff_light = None

        # Cover sprite for text reveal effect
        self.cover_sprites = []
        self._create_cover_sprites()

        # Enable lighting system
        self.root.set_lighting(enabled=True, ambient=(50, 50, 55))

        # Enable bloom for emissive glow
        self.root.set_bloom(enabled=True, threshold=220, blur_scale=1, intensity=0.2)

        # Ambient corner lights (dim initially)
        self.corner_lights = []
        self._create_corner_lights()

        # Magic word sprites (white emissive)
        self.magic_sprites = {'line1': [], 'line2': [], 'line3': []}
        self._create_magic_word_sprites()

    def _create_magic_word_sprites(self):
        """Create emissive sprites for the magic words."""
        white_color = (255, 255, 255)

        # Line 1: "Magick" - indices 19-24 (white emissive)
        for i in range(19, len(LINE1_CHARS)):
            x, y, char = LINE1_CHARS[i]
            sprite = pyunicodegame.create_sprite(char, x=x, y=y, fg=white_color, emissive=True)
            sprite.visible = False
            self.root.add_sprite(sprite)
            self.magic_sprites['line1'].append(sprite)

        # Line 2: "Staff of Yendor" - indices 18-30 (white emissive)
        for i in range(18, len(LINE2_CHARS)):
            x, y, char = LINE2_CHARS[i]
            sprite = pyunicodegame.create_sprite(char, x=x, y=y, fg=white_color, emissive=True)
            sprite.visible = False
            self.root.add_sprite(sprite)
            self.magic_sprites['line2'].append(sprite)

        # Line 3: "Reason" - indices 27-32 (white emissive)
        for i in range(27, len(LINE3_CHARS)):
            x, y, char = LINE3_CHARS[i]
            sprite = pyunicodegame.create_sprite(char, x=x, y=y, fg=white_color, emissive=True)
            sprite.visible = False
            self.root.add_sprite(sprite)
            self.magic_sprites['line3'].append(sprite)

    def _create_cover_sprites(self):
        """Create cover sprites that hide text until revealed."""
        # Create a single-cell dark cover pattern
        cover_char = '█'  # Full block character

        # We'll manage reveal by simply not drawing characters until revealed
        # The cover sprite approach: create wide covers for each line
        pass  # Actually, we'll use a simpler approach - just draw chars as they're revealed

    def _create_corner_lights(self):
        """Create ambient lights at the four corners."""
        corners = [
            (5, 4),           # top-left
            (WIDTH - 6, 4),   # top-right
            (5, HEIGHT - 5),  # bottom-left
            (WIDTH - 6, HEIGHT - 5),  # bottom-right
        ]

        for x, y in corners:
            light = pyunicodegame.create_light(
                x=x, y=y,
                radius=30,
                color=(60, 40, 100),  # Dim purple ambient
                intensity=0.3,
                falloff=1.5,
                casts_shadows=False
            )
            self.root.add_light(light)
            self.corner_lights.append(light)

    def _create_staff_sprite(self):
        """Create the staff sprite with a non-looping animation."""
        self.staff_sprite = staff_create_sprite('yendor', 27, 5)
        self.staff_sprite.visible = False
        self.root.add_sprite(self.staff_sprite)

        # Create a non-looping version of the animation
        # Original animation: frames [(1,0,0), (2,0,0), (3,0,0), (4,0,0), (5,0,0), (7,0,0), (7,0,0), (0,0,0)]
        # These are (frame_index, offset_x, offset_y) tuples, we just need frame indices
        anim = Animation(
            name="appear",
            frame_indices=[1, 2, 3, 4, 5, 6, 7, 0],  # Staff appearance sequence
            frame_duration=0.35,
            loop=False  # Play once
        )
        self.staff_sprite.add_animation(anim)

    def _create_staff_light(self):
        """Create the light at the top of the staff."""
        # Staff is at (27, 5), top of staff visual is around y=6-7
        self.staff_light = pyunicodegame.create_light(
            x=29, y=7,  # Position at staff top
            radius=15,
            color=(255, 220, 150),  # Warm golden light
            intensity=0.0,  # Start invisible, fade in
            falloff=1.2,
            casts_shadows=True
        )
        self.root.add_light(self.staff_light)

    def update(self, dt):
        """Update animation state."""
        self.time_accumulator += dt

        if self.phase == 0:
            # Reveal line 1
            while self.time_accumulator >= self.char_reveal_speed and self.line1_revealed < len(LINE1_CHARS):
                self.time_accumulator -= self.char_reveal_speed
                self.line1_revealed += 1

            if self.line1_revealed >= len(LINE1_CHARS):
                self.phase = 1
                self.time_accumulator = 0

        elif self.phase == 1:
            # Reveal line 2
            while self.time_accumulator >= self.char_reveal_speed and self.line2_revealed < len(LINE2_CHARS):
                self.time_accumulator -= self.char_reveal_speed
                self.line2_revealed += 1

            if self.line2_revealed >= len(LINE2_CHARS):
                self.phase = 2
                self.time_accumulator = 0
                # Create and show staff
                self._create_staff_sprite()
                self.staff_sprite.visible = True
                self.staff_sprite.play_animation("appear")
                self.staff_animation_started = True

        elif self.phase == 2:
            # Wait for staff animation to finish
            if self.staff_sprite and self.staff_sprite.is_animation_finished():
                self.phase = 3
                self.time_accumulator = 0
                # Create staff light
                self._create_staff_light()

        elif self.phase == 3:
            # Fade in staff light and reveal bottom text
            if self.staff_light and self.staff_light.intensity < 1.0:
                self.staff_light.intensity = min(1.0, self.staff_light.intensity + dt * 0.5)

            # Reveal line 3
            while self.time_accumulator >= self.char_reveal_speed and self.line3_revealed < len(LINE3_CHARS):
                self.time_accumulator -= self.char_reveal_speed
                self.line3_revealed += 1

            if self.line3_revealed >= len(LINE3_CHARS):
                self.phase = 4
                self.time_accumulator = 0

        elif self.phase == 4:
            # Reveal line 4
            while self.time_accumulator >= self.char_reveal_speed and self.line4_revealed < len(LINE4_CHARS):
                self.time_accumulator -= self.char_reveal_speed
                self.line4_revealed += 1

            if self.line4_revealed >= len(LINE4_CHARS):
                self.phase = 5  # Done

        # Keep fading in staff light if needed
        if self.phase >= 3 and self.staff_light and self.staff_light.intensity < 1.0:
            self.staff_light.intensity = min(1.0, self.staff_light.intensity + dt * 0.5)

    def render(self):
        """Render the scene."""
        # Draw revealed characters from line 1
        # "Magick" is indices 19-24 (last 6 chars) - handled by sprites
        for i in range(self.line1_revealed):
            x, y, char = LINE1_CHARS[i]
            if i >= 19:  # Magick - show sprite instead
                self.magic_sprites['line1'][i - 19].visible = True
            else:
                self.root.put(x, y, char, (255, 255, 255))

        # Draw revealed characters from line 2
        # "Staff of Yendor" is indices 18-30 (last 13 chars) - handled by sprites
        for i in range(self.line2_revealed):
            x, y, char = LINE2_CHARS[i]
            if i >= 18:  # Staff of Yendor - show sprite instead
                self.magic_sprites['line2'][i - 18].visible = True
            else:
                self.root.put(x, y, char, (255, 255, 255))

        # Draw revealed characters from line 3
        # "Reason" is indices 27-32 (last 6 chars) - handled by sprites
        for i in range(self.line3_revealed):
            x, y, char = LINE3_CHARS[i]
            if i >= 27:  # Reason - show sprite instead
                self.magic_sprites['line3'][i - 27].visible = True
            else:
                self.root.put(x, y, char, (255, 255, 255))

        # Draw revealed characters from line 4
        for i in range(self.line4_revealed):
            x, y, char = LINE4_CHARS[i]
            self.root.put(x, y, char, (255, 255, 255))

    def on_key(self, key):
        """Handle key input."""
        if key == pygame.K_q or key == pygame.K_ESCAPE:
            pyunicodegame.quit()
        elif key == pygame.K_SPACE or key == pygame.K_RETURN:
            # Skip to end if not done
            if self.phase < 5:
                self.line1_revealed = len(LINE1_CHARS)
                self.line2_revealed = len(LINE2_CHARS)
                self.line3_revealed = len(LINE3_CHARS)
                self.line4_revealed = len(LINE4_CHARS)
                if not self.staff_sprite:
                    self._create_staff_sprite()
                self.staff_sprite.visible = True
                self.staff_sprite.current_frame = 0
                if not self.staff_light:
                    self._create_staff_light()
                self.staff_light.intensity = 1.0
                self.phase = 5

    def run(self):
        """Run the start screen."""
        pyunicodegame.run(
            update=self.update,
            render=self.render,
            on_key=self.on_key
        )


def main():
    screen = StartScreen()
    screen.run()


if __name__ == "__main__":
    main()
