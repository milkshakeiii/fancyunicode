#!/usr/bin/env python3
"""
Demo script to display spritesheets using pyunicodegame.

Usage:
    python demo_spritesheet.py spritesheet.png

Spritesheet format:
    - Multiple rows, each row is a different animation
    - First row (row 0) is treated as "idle" and plays on startup
    - All frames in a row should have the same width

Controls:
    Up/Down arrows: Cycle through animations (rows)
    L or Space: Toggle loop/one-shot mode
    Q or ESC: Quit
"""

import argparse
import json
import sys
from pathlib import Path

# Add pyunicodegame to path if not installed
pyunicodegame_path = Path("/home/henry/Documents/github/pyunicodegame/src")
if pyunicodegame_path.exists():
    sys.path.insert(0, str(pyunicodegame_path))

import pygame
import pyunicodegame
from PIL import Image


def main():
    parser = argparse.ArgumentParser(description="Demo spritesheet animation")
    parser.add_argument(
        "spritesheet",
        nargs="?",
        default="output/spritesheet.png",
        help="Path to spritesheet PNG (default: output/spritesheet.png)",
    )
    parser.add_argument(
        "--frame-width",
        type=int,
        default=None,
        help="Frame width in pixels (default: auto-detect from metadata or 20)",
    )
    parser.add_argument(
        "--frame-height",
        type=int,
        default=None,
        help="Frame height in pixels (default: auto-detect from metadata or 20)",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=4.0,
        help="Animation frames per second (default: 4)",
    )
    parser.add_argument(
        "--names",
        type=str,
        default=None,
        help="Comma-separated animation names for each row (default: idle,row1,row2,...)",
    )
    args = parser.parse_args()

    spritesheet_path = Path(args.spritesheet)
    if not spritesheet_path.exists():
        print(f"Error: Spritesheet not found: {spritesheet_path}")
        sys.exit(1)

    # Load image to get dimensions
    img = Image.open(spritesheet_path)
    sheet_width, sheet_height = img.size

    # Determine frame dimensions and animation names from metadata
    metadata_path = spritesheet_path.parent / "metadata.json"
    metadata = {}
    if metadata_path.exists():
        with open(metadata_path) as f:
            metadata = json.load(f)
        frame_width = args.frame_width or metadata.get("frame_width", 20)
        frame_height = args.frame_height or metadata.get("frame_height", 20)
    else:
        frame_width = args.frame_width or 20
        frame_height = args.frame_height or 20

    # Calculate grid
    cols = sheet_width // frame_width
    rows = sheet_height // frame_height

    print(f"Spritesheet: {sheet_width}x{sheet_height}")
    print(f"Frame size: {frame_width}x{frame_height}")
    print(f"Grid: {cols} columns x {rows} rows")

    # Animation names (prefer: CLI arg > metadata > defaults)
    if args.names:
        anim_names = args.names.split(",")
        # Pad with default names if needed
        while len(anim_names) < rows:
            anim_names.append(f"row{len(anim_names)}")
    elif "animations" in metadata:
        anim_names = metadata["animations"]
        while len(anim_names) < rows:
            anim_names.append(f"row{len(anim_names)}")
    else:
        anim_names = ["idle"] + [f"row{i}" for i in range(1, rows)]

    anim_names = anim_names[:rows]  # Trim if too many
    print(f"Animations: {', '.join(anim_names)}")

    # Use 10x20 font so 20x20 sprites are 2x1 cells
    cell_width = 10
    cell_height = 20

    # Window size in cells
    window_width = 25
    window_height = 10

    # State
    current_row = 0
    is_looping = True

    # Initialize pyunicodegame with 10x20 font
    pyunicodegame.init(
        "Spritesheet Demo",
        width=window_width,
        height=window_height,
        bg=(30, 30, 40, 255),
        font_name="10x20",
    )

    root = pyunicodegame.get_window("root")

    # Load sprite sheet
    sheet = pyunicodegame.create_sprite_sheet(
        str(spritesheet_path),
        frame_width=frame_width,
        frame_height=frame_height,
        rows=rows,
        cols=cols,
    )

    # Create sprites for each row (animation)
    sprite_cells_wide = frame_width // cell_width
    sprite_cells_tall = frame_height // cell_height
    sprite_x = window_width // 2 - sprite_cells_wide // 2
    sprite_y = window_height // 2 - sprite_cells_tall // 2

    sprites = []
    for row in range(rows):
        # Frame indices for this row
        start_frame = row * cols
        frame_indices = list(range(start_frame, start_frame + cols))

        sprite = pyunicodegame.create_pixel_sprite(
            sheet,
            frames=frame_indices,
            x=sprite_x,
            y=sprite_y,
        )

        # Create loop and one-shot animations
        loop_anim = pyunicodegame.create_animation(
            "loop",
            frame_indices=list(range(cols)),  # Local indices within sprite's frames
            frame_duration=1.0 / args.fps,
            loop=True,
        )
        oneshot_anim = pyunicodegame.create_animation(
            "oneshot",
            frame_indices=list(range(cols)),
            frame_duration=1.0 / args.fps,
            loop=False,
        )
        sprite.add_animation(loop_anim)
        sprite.add_animation(oneshot_anim)

        sprites.append(sprite)

    # Add first sprite (idle) to window and start playing
    root.add_sprite(sprites[0])
    sprites[0].play_animation("loop")

    def switch_animation(new_row):
        nonlocal current_row
        if new_row == current_row:
            return

        # Remove old sprite
        root.remove_sprite(sprites[current_row])

        # Add new sprite
        current_row = new_row
        root.add_sprite(sprites[current_row])

        # Play appropriate animation
        anim_name = "loop" if is_looping else "oneshot"
        sprites[current_row].play_animation(anim_name)

    def toggle_loop():
        nonlocal is_looping
        is_looping = not is_looping
        anim_name = "loop" if is_looping else "oneshot"
        sprites[current_row].play_animation(anim_name)

    def update(dt):
        pass  # Animation is handled by the sprite

    def render():
        sprite = sprites[current_row]

        # Animation name and frame info
        mode = "LOOP" if is_looping else "ONCE"
        name = anim_names[current_row]
        root.put(1, 0, f"{name} ({current_row + 1}/{rows})", (200, 200, 200))
        root.put(1, 1, f"Frame {sprite.current_frame + 1}/{cols} [{mode}]", (150, 150, 150))

    def on_key(key):
        if key in (pygame.K_q, pygame.K_ESCAPE):
            pyunicodegame.quit()
        elif key == pygame.K_DOWN:
            new_row = (current_row + 1) % rows
            switch_animation(new_row)
        elif key == pygame.K_UP:
            new_row = (current_row - 1) % rows
            switch_animation(new_row)
        elif key in (pygame.K_l, pygame.K_SPACE):
            toggle_loop()
        elif pygame.K_1 <= key <= pygame.K_9:
            # Number keys 1-9 switch to that animation row
            new_row = key - pygame.K_1  # 0-indexed
            if new_row < rows:
                switch_animation(new_row)

    print(f"\nStarting demo...")
    print(f"  FPS: {args.fps}")
    print(f"\nControls:")
    print(f"  Up/Down: Cycle animations (rows)")
    print(f"  L or Space: Toggle loop/one-shot")
    print(f"  Q or ESC: Quit\n")

    pyunicodegame.run(update=update, render=render, on_key=on_key)


if __name__ == "__main__":
    main()
