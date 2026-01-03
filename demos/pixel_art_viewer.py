#!/usr/bin/env python3
"""
Pixel art viewer that matches logical resolution with window scaling.

Displays an image at its logical pixel resolution using mode downscaling
to preserve hard pixel edges, with adjustable window scaling.
"""

import argparse
import pygame
import pyunicodegame


def main():
    parser = argparse.ArgumentParser(description="Pixel art viewer with scaling")
    parser.add_argument("image", help="Path to image file")
    parser.add_argument("--width", type=int, default=194, help="Logical width in pixels")
    parser.add_argument("--height", type=int, default=96, help="Logical height in pixels")
    parser.add_argument("--font", default="5x8", choices=["5x8", "6x13", "9x18", "10x20"],
                        help="Font size (smaller = smaller window)")
    args = parser.parse_args()

    # Half-block chars give 2 vertical pixels per cell
    cell_height = (args.height + 1) // 2

    root = pyunicodegame.init(
        "Pixel Art Viewer",
        width=args.width + 2,
        height=cell_height + 3,
        bg=(10, 10, 20, 255),
        font_name=args.font,
    )

    # Create sprite with "mode" for hard pixel edges
    sprite = pyunicodegame.create_sprite_from_image(
        args.image,
        width=args.width,
        height=args.height,
        x=1,
        y=2,
        mode="mode",
    )
    root.add_sprite(sprite)

    def render():
        info = f"{args.width}x{args.height}px mode | Q to quit"
        root.put_string(1, 1, info, (100, 100, 100))

    def on_key(key):
        if key == pygame.K_q:
            pyunicodegame.quit()

    pyunicodegame.run(render=render, on_key=on_key)


if __name__ == "__main__":
    main()
