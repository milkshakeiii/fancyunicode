#!/usr/bin/env python3
"""
Demo script to display spritesheets using pyunicodegame.

Usage:
    python demo_spritesheet.py [spritesheet.png]

If no spritesheet is provided, uses output/spritesheet.png
"""

import argparse
import json
import sys
from pathlib import Path

# Add pyunicodegame to path if not installed
pyunicodegame_path = Path("/home/henry/Documents/github/pyunicodegame/src")
if pyunicodegame_path.exists():
    sys.path.insert(0, str(pyunicodegame_path))

import pyunicodegame


def main():
    parser = argparse.ArgumentParser(description="Demo spritesheet animation")
    parser.add_argument(
        "spritesheet",
        nargs="?",
        default="output/spritesheet.png",
        help="Path to spritesheet PNG (default: output/spritesheet.png)",
    )
    parser.add_argument(
        "--metadata",
        default=None,
        help="Path to metadata JSON (default: same dir as spritesheet)",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=4.0,
        help="Animation frames per second (default: 4)",
    )
    parser.add_argument(
        "--scale",
        type=int,
        default=4,
        help="Scale factor for display (default: 4)",
    )
    args = parser.parse_args()

    spritesheet_path = Path(args.spritesheet)
    if not spritesheet_path.exists():
        print(f"Error: Spritesheet not found: {spritesheet_path}")
        sys.exit(1)

    # Load metadata
    metadata_path = args.metadata
    if metadata_path is None:
        metadata_path = spritesheet_path.parent / "metadata.json"
    else:
        metadata_path = Path(metadata_path)

    if metadata_path.exists():
        with open(metadata_path) as f:
            metadata = json.load(f)
        frame_width = metadata["frame_width"]
        frame_height = metadata["frame_height"]
        frame_count = metadata["frame_count"]
        print(f"Loaded metadata: {frame_width}x{frame_height}, {frame_count} frames")
    else:
        print(f"Warning: No metadata found at {metadata_path}")
        print("Using defaults: 20x20, will auto-detect frame count")
        frame_width = 20
        frame_height = 20
        # Auto-detect frame count from image width
        from PIL import Image
        img = Image.open(spritesheet_path)
        frame_count = img.width // frame_width
        print(f"Auto-detected {frame_count} frames")

    # Use 10x20 font so 20x20 sprites are 2x1 cells
    cell_width = 10
    cell_height = 20

    # Window size in cells
    window_width = 20
    window_height = 10

    # Initialize pyunicodegame with 10x20 font
    pyunicodegame.init(
        f"Spritesheet Demo - {spritesheet_path.name}",
        width=window_width,
        height=window_height,
        bg=(30, 30, 40, 255),
        font_name="10x20",
    )

    # Load sprite sheet
    sheet = pyunicodegame.create_sprite_sheet(
        str(spritesheet_path),
        frame_width=frame_width,
        frame_height=frame_height,
        rows=1,
        cols=frame_count,
    )

    # Create pixel sprite from sheet
    # Position: center of window, accounting for sprite size in cells
    sprite_cells_wide = frame_width // cell_width  # 20/10 = 2 cells
    sprite_cells_tall = frame_height // cell_height  # 20/20 = 1 cell
    sprite = pyunicodegame.create_pixel_sprite(
        sheet,
        frames=list(range(frame_count)),
        x=window_width // 2 - sprite_cells_wide // 2,
        y=window_height // 2 - sprite_cells_tall // 2,
    )

    # Add sprite to window
    root = pyunicodegame.get_window("root")
    root.add_sprite(sprite)

    # Create and register animation
    anim = pyunicodegame.create_animation(
        "loop",
        frame_indices=list(range(frame_count)),
        frame_duration=1.0 / args.fps,
        loop=True,
    )
    sprite.add_animation(anim)
    sprite.play_animation("loop")

    def update(dt):
        pass  # Animation is handled by the sprite

    def render():
        root = pyunicodegame.get_window("root")
        # Draw minimal info text
        root.put(1, 0, f"{sprite.current_frame + 1}/{frame_count}", (150, 150, 150))

    def on_key(key):
        if key in ("q", "escape"):
            pyunicodegame.quit()

    print(f"\nStarting demo...")
    print(f"  Spritesheet: {spritesheet_path}")
    print(f"  Frame size: {frame_width}x{frame_height}")
    print(f"  Frames: {frame_count}")
    print(f"  FPS: {args.fps}")
    print(f"\nPress Q or ESC to quit\n")

    pyunicodegame.run(update=update, render=render, on_key=on_key)


if __name__ == "__main__":
    main()
