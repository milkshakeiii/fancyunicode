#!/usr/bin/env python3
"""Quick side-by-side comparison of original and pixel-extracted images."""

import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def compare(original_path: str, pixels_path: str, output_path: str = None):
    original = Image.open(original_path)
    pixels = Image.open(pixels_path)

    # Scale up pixels to match original size (nearest neighbor to keep crisp)
    pixels_scaled = pixels.resize(original.size, Image.NEAREST)

    # Create side-by-side with space for labels
    label_height = 40
    combined = Image.new("RGBA", (original.width * 2, original.height + label_height), (255, 255, 255, 255))
    combined.paste(original.convert("RGBA"), (0, label_height))
    combined.paste(pixels_scaled, (original.width, label_height))

    # Add labels
    draw = ImageDraw.Draw(combined)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    except:
        font = ImageFont.load_default()

    draw.text((original.width // 2, 10), "Original", fill=(0, 0, 0), anchor="mt", font=font)
    draw.text((original.width + original.width // 2, 10), "Extracted", fill=(0, 0, 0), anchor="mt", font=font)

    if output_path:
        combined.save(output_path)
        print(f"Saved: {output_path}")
    else:
        combined.show()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python compare.py <original> <pixels> [output]")
        sys.exit(1)

    output = sys.argv[3] if len(sys.argv) > 3 else None
    compare(sys.argv[1], sys.argv[2], output)
