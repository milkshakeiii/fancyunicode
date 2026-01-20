#!/usr/bin/env python3
"""
Spritesheet Builder

Builds spritesheets using Gemini image generation and pixelgrid.py extraction.
Supports additive building across multiple calls.

Usage:
    python3 spritesheet_builder.py init <project_dir> <character_prompt> [--cell-size WxH] [--resolution WxH] [--no-quantize]
    python3 spritesheet_builder.py add-frame <project_dir> <animation> <frame_prompt> [--no-quantize]
    python3 spritesheet_builder.py build <project_dir>
    python3 spritesheet_builder.py show <project_dir>
    python3 spritesheet_builder.py quantize <project_dir> [--colors N]

Options:
    --cell-size WxH    Frame dimensions will be multiples of this (default: 10x20)
    --resolution WxH   Hint for Gemini about desired sprite size (default: 2 cells wide x 1 cell tall)
    --no-quantize      Skip automatic palette quantization (init/add-frame)
    --colors N         Number of colors for palette (default: auto-detect)

Requires GOOGLE_API_KEY environment variable to be set.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image

from pixelgrid import (
    detect_grid_size,
    find_best_offset,
    refine_grid_lines,
    extract_pixels,
    crop_to_content,
)

from palette import (
    extract_palette,
    quantize_to_palette,
    unify_project_palette,
    get_project_palette,
    set_project_palette,
    palette_to_json,
    palette_from_json,
    color_to_hex,
    detect_optimal_colors,
)


# =============================================================================
# CONFIGURATION
# =============================================================================

STYLE_PROMPT = """The image should be on a solid bright green (#00FF00) background for easy chroma keying.
The character should be centered, showing their full side profile.
CRITICAL: The ENTIRE character must fit within the image with large margins. Every body part - head, ears, tail, legs, arms, wings - must be fully visible with space around them. Nothing can touch or go past any edge. Make the character small enough to leave 20% empty green space on all sides.
Use flat solid colors with no gradients, shading, or anti-aliasing.
NO outlines. Extremely simple shapes only.
Eyes should be medium-sized solid BLACK circles, no whites, no eyelids, no pupils.
No facial details other than eyes. No two details should be close to one another.
All features must be thick and blocky. No thin lines - items, clothing, limbs should be as wide as the character's head.
Large solid color regions, minimal color count.
No shadows on the green background.
The green background should be completely uniform #00FF00.
The entire image should be filled with the green background, edge to edge, no white or other colors."""

METADATA_FILENAME = "metadata.json"


# =============================================================================
# FRAME SIZE HELPERS
# =============================================================================

def round_to_cell_multiple(size: Tuple[int, int], cell_size: Tuple[int, int]) -> Tuple[int, int]:
    """Round dimensions up to nearest cell_size multiple."""
    cell_w, cell_h = cell_size
    w = ((size[0] + cell_w - 1) // cell_w) * cell_w
    h = ((size[1] + cell_h - 1) // cell_h) * cell_h
    return (w, h)


def pad_frame_to_size(frame: Image.Image, target_size: Tuple[int, int]) -> Image.Image:
    """Center frame on transparent canvas of target_size."""
    if frame.size == target_size:
        return frame
    canvas = Image.new("RGBA", target_size, (0, 0, 0, 0))
    offset_x = (target_size[0] - frame.size[0]) // 2
    offset_y = (target_size[1] - frame.size[1]) // 2
    canvas.paste(frame, (offset_x, offset_y))
    return canvas


def expand_all_frames(project_dir: Path, metadata: dict, new_frame_size: Tuple[int, int]) -> None:
    """Re-pad all existing frames to new_frame_size."""
    frames_dir = project_dir / "frames"
    old_size = tuple(metadata["frame_size"])

    print(f"Expanding frames from {old_size[0]}x{old_size[1]} to {new_frame_size[0]}x{new_frame_size[1]}")

    # Track which files we've already processed (some frames are shared)
    processed_files = set()

    for anim_name, anim_data in metadata["animations"].items():
        for frame_info in anim_data["frames"]:
            extracted_filename = frame_info["extracted"]
            if extracted_filename in processed_files:
                continue
            processed_files.add(extracted_filename)

            frame_path = frames_dir / extracted_filename
            if frame_path.exists():
                frame_img = Image.open(frame_path).convert("RGBA")
                padded = pad_frame_to_size(frame_img, new_frame_size)
                padded.save(frame_path)
                print(f"  Re-padded: {extracted_filename}")

    metadata["frame_size"] = list(new_frame_size)


# =============================================================================
# GEMINI IMAGE GENERATION
# =============================================================================

def generate_image(full_prompt: str, output_path: Path, reference_image: Optional[Path] = None) -> Path:
    """Generate image with Gemini, optionally using a reference image."""
    from google import genai
    from google.genai import types

    client = genai.Client()

    print(f"Generating image with prompt:\n{full_prompt[:200]}...\n")

    # Build contents - optionally include reference image
    if reference_image and reference_image.exists():
        print(f"Using reference image: {reference_image}")
        with open(reference_image, "rb") as f:
            image_data = f.read()
        contents = [
            types.Part.from_bytes(data=image_data, mime_type="image/png"),
            full_prompt,
        ]
    else:
        contents = [full_prompt]

    response = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=contents,
        config={
            "response_modalities": ["image", "text"],
        },
    )

    # Extract image from response
    for part in response.candidates[0].content.parts:
        if hasattr(part, "inline_data") and part.inline_data is not None:
            image_data = part.inline_data.data
            with open(output_path, "wb") as f:
                f.write(image_data)
            print(f"Saved image to {output_path}")
            return output_path

    raise RuntimeError("No image generated in response")


def build_base_prompt(character_prompt: str, requested_resolution: Optional[Tuple[int, int]] = None) -> str:
    """Build prompt for base idle sprite."""
    resolution_hint = ""
    if requested_resolution:
        resolution_hint = f"\nThe character should be {requested_resolution[0]}x{requested_resolution[1]} pixels in size."
    return f"""Create pixel art of {character_prompt}, side-on view, facing right.{resolution_hint}
{STYLE_PROMPT}"""


def build_frame_prompt(character_prompt: str, frame_prompt: str, requested_resolution: Optional[Tuple[int, int]] = None) -> str:
    """Build prompt for an animation frame with reference image."""
    resolution_hint = ""
    if requested_resolution:
        resolution_hint = f"\nThe character should be {requested_resolution[0]}x{requested_resolution[1]} pixels in size."
    return f"""The attached image shows the base sprite for {character_prompt}.
Create a new frame of this EXACT same character showing: {frame_prompt}
The character must look identical - same colors, same proportions, same style.
Only the pose/action should change.{resolution_hint}
{STYLE_PROMPT}"""


# =============================================================================
# PIXELGRID EXTRACTION
# =============================================================================

def extract_sprite(raw_path: Path, output_path: Path) -> Tuple[int, int]:
    """
    Extract pixels using pixelgrid.

    Returns (width, height) of extracted sprite.
    """
    img = Image.open(raw_path)
    print(f"Raw image size: {img.size}")

    # Detect grid
    cell_width, cell_height = detect_grid_size(img)
    print(f"Detected cell size: {cell_width}x{cell_height}")

    # Find best offset
    offset_x, offset_y = find_best_offset(img, cell_width, cell_height)
    print(f"Detected offset: ({offset_x}, {offset_y})")

    # Refine grid lines
    x_lines, y_lines = refine_grid_lines(img, cell_width, cell_height, offset_x, offset_y)
    print(f"Grid: {len(x_lines)-1} x {len(y_lines)-1} cells")

    # Extract pixels
    pixel_img, bbox = extract_pixels(img, x_lines, y_lines, remove_green=True)
    print(f"Content bbox: x={bbox[0]}, y={bbox[1]}, w={bbox[2]}, h={bbox[3]}")

    # Crop to content
    cropped = crop_to_content(pixel_img, bbox)
    cropped.save(output_path)
    print(f"Saved extracted sprite: {output_path} ({cropped.size[0]}x{cropped.size[1]})")

    return cropped.size


# =============================================================================
# METADATA MANAGEMENT
# =============================================================================

def load_metadata(project_dir: Path) -> dict:
    """Load metadata from project directory."""
    metadata_path = project_dir / METADATA_FILENAME
    if not metadata_path.exists():
        raise FileNotFoundError(f"No metadata.json found in {project_dir}")
    with open(metadata_path) as f:
        return json.load(f)


def save_metadata(project_dir: Path, metadata: dict) -> None:
    """Save metadata to project directory."""
    metadata_path = project_dir / METADATA_FILENAME
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Updated {metadata_path}")


def init_metadata(
    character_prompt: str,
    cell_size: Tuple[int, int],
    frame_size: Tuple[int, int],
    requested_resolution: Optional[Tuple[int, int]] = None,
) -> dict:
    """Create initial metadata structure."""
    metadata = {
        "character_prompt": character_prompt,
        "cell_size": list(cell_size),
        "frame_size": list(frame_size),
        "style_prompt": STYLE_PROMPT,
        "animations": {
            "idle": {
                "frames": []
            }
        }
    }
    if requested_resolution:
        metadata["requested_resolution"] = list(requested_resolution)
    return metadata


# =============================================================================
# CLI COMMANDS
# =============================================================================

def parse_size_arg(size_str: str) -> Tuple[int, int]:
    """Parse a WxH size string into (width, height) tuple."""
    parts = size_str.lower().split("x")
    if len(parts) != 2:
        raise ValueError(f"Invalid size format: {size_str} (expected WxH, e.g., 8x12)")
    return (int(parts[0]), int(parts[1]))


def cmd_init(args) -> int:
    """Initialize new project."""
    project_dir: Path = args.project_dir
    character_prompt: str = args.character_prompt
    cell_size: Tuple[int, int] = parse_size_arg(args.cell_size)
    if args.resolution:
        requested_resolution: Tuple[int, int] = parse_size_arg(args.resolution)
    else:
        # Default: 2 cells wide x 1 cell tall
        requested_resolution = (cell_size[0] * 2, cell_size[1])

    print(f"Initializing project: {project_dir}")
    print(f"Character: {character_prompt}")
    print(f"Cell size: {cell_size[0]}x{cell_size[1]}")
    print(f"Requested resolution: {requested_resolution[0]}x{requested_resolution[1]}")

    # Create directory structure
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "raw").mkdir(exist_ok=True)
    (project_dir / "frames").mkdir(exist_ok=True)

    # Check if already initialized
    metadata_path = project_dir / METADATA_FILENAME
    if metadata_path.exists():
        print(f"Warning: Project already exists at {project_dir}")
        response = input("Overwrite? [y/N] ")
        if response.lower() != "y":
            print("Aborted.")
            return 1

    # Generate base sprite
    raw_path = project_dir / "raw" / "idle_base.png"
    prompt = build_base_prompt(character_prompt, requested_resolution)
    generate_image(prompt, raw_path)

    # Extract pixels
    frames_path = project_dir / "frames" / "idle_0.png"
    extracted_size = extract_sprite(raw_path, frames_path)

    # Round frame size to cell multiple
    frame_size = round_to_cell_multiple(extracted_size, cell_size)
    print(f"Extracted size: {extracted_size[0]}x{extracted_size[1]} -> padded to: {frame_size[0]}x{frame_size[1]}")

    # Pad the extracted frame to the target frame size
    if extracted_size != frame_size:
        frame_img = Image.open(frames_path).convert("RGBA")
        padded = pad_frame_to_size(frame_img, frame_size)
        padded.save(frames_path)

    # Initialize metadata
    metadata = init_metadata(character_prompt, cell_size, frame_size, requested_resolution)
    metadata["animations"]["idle"]["frames"].append({
        "prompt": None,
        "raw": "idle_base.png",
        "extracted": "idle_0.png"
    })

    # Auto-quantize by default unless --no-quantize is specified
    palette = None
    if not args.no_quantize:
        base_img = Image.open(frames_path)

        # Auto-detect optimal colors if not specified
        num_colors = args.colors
        if num_colors is None:
            print("\nDetecting optimal color count...")
            num_colors = detect_optimal_colors(base_img)
            print(f"Detected optimal colors: {num_colors}")

        print(f"\nExtracting palette ({num_colors} colors)...")
        palette = extract_palette(base_img, num_colors)
        print(f"Palette extracted:")
        for i, color in enumerate(palette):
            print(f"  {i+1}. {color_to_hex(color)}")

        # Quantize the base sprite to clean palette
        quantized = quantize_to_palette(base_img, palette)
        quantized.save(frames_path)
        print(f"Base sprite quantized to {len(palette)} colors")

        # Store palette in metadata
        metadata["palette"] = palette_to_json(palette)

    save_metadata(project_dir, metadata)

    print(f"\nProject initialized!")
    print(f"  Cell size: {cell_size[0]}x{cell_size[1]}")
    print(f"  Frame size: {frame_size[0]}x{frame_size[1]}")
    print(f"  Base sprite: {frames_path}")
    if palette:
        print(f"  Palette: {len(palette)} colors (stored in metadata)")
    return 0


def cmd_add_frame(args) -> int:
    """Add frame to animation."""
    project_dir: Path = args.project_dir
    animation: str = args.animation
    frame_prompt: str = args.frame_prompt

    print(f"Adding frame to {animation}: {frame_prompt}")

    # Load metadata
    metadata = load_metadata(project_dir)
    character_prompt = metadata["character_prompt"]
    cell_size = tuple(metadata["cell_size"])
    current_frame_size = tuple(metadata["frame_size"])
    requested_resolution = None
    if "requested_resolution" in metadata:
        requested_resolution = tuple(metadata["requested_resolution"])

    # Get or create animation
    if animation not in metadata["animations"]:
        print(f"Creating new animation: {animation}")
        # New animations start with idle base as frame 0 (shared)
        metadata["animations"][animation] = {
            "frames": [{
                "prompt": None,
                "raw": None,
                "extracted": "idle_0.png"  # Shared base
            }]
        }

    anim_data = metadata["animations"][animation]
    frame_num = len(anim_data["frames"])

    # Generate image using base sprite as reference
    raw_filename = f"{animation}_frame_{frame_num}.png"
    raw_path = project_dir / "raw" / raw_filename
    base_sprite = project_dir / "frames" / "idle_0.png"

    prompt = build_frame_prompt(character_prompt, frame_prompt, requested_resolution)
    generate_image(prompt, raw_path, reference_image=base_sprite)

    # Extract pixels
    extracted_filename = f"{animation}_{frame_num}.png"
    extracted_path = project_dir / "frames" / extracted_filename
    extracted_size = extract_sprite(raw_path, extracted_path)

    # Calculate required frame size (max of current and extracted, rounded to cell multiple)
    required_size = (
        max(current_frame_size[0], extracted_size[0]),
        max(current_frame_size[1], extracted_size[1]),
    )
    new_frame_size = round_to_cell_multiple(required_size, cell_size)

    # Check if we need to expand all frames
    if new_frame_size != current_frame_size:
        print(f"New frame exceeds current size, expanding all frames...")
        expand_all_frames(project_dir, metadata, new_frame_size)

    # Pad the new frame to the target frame size
    frame_size = tuple(metadata["frame_size"])
    frame_img = Image.open(extracted_path).convert("RGBA")
    if frame_img.size != frame_size:
        padded = pad_frame_to_size(frame_img, frame_size)
        padded.save(extracted_path)
        print(f"Padded new frame to {frame_size[0]}x{frame_size[1]}")
        frame_img = padded

    # Auto-quantize by default unless --no-quantize is specified
    if not args.no_quantize:
        palette = get_project_palette(project_dir)
        if palette:
            print(f"Quantizing to project palette ({len(palette)} colors)...")
            quantized = quantize_to_palette(frame_img, palette)
            quantized.save(extracted_path)
            print(f"Frame quantized to palette")
        else:
            print("Note: No palette in metadata, skipping quantization")
            print("Run 'quantize' command to unify all frames to a shared palette")

    # Update metadata
    anim_data["frames"].append({
        "prompt": frame_prompt,
        "raw": raw_filename,
        "extracted": extracted_filename
    })

    save_metadata(project_dir, metadata)

    print(f"\nAdded frame {frame_num} to {animation}")
    print(f"  {animation} now has {len(anim_data['frames'])} frames")
    print(f"  Frame size: {frame_size[0]}x{frame_size[1]}")
    return 0


def cmd_build(args) -> int:
    """Build spritesheet."""
    project_dir: Path = args.project_dir

    print(f"Building spritesheet for {project_dir}")

    # Load metadata
    metadata = load_metadata(project_dir)
    animations = metadata["animations"]
    frame_size = tuple(metadata["frame_size"])

    if not animations:
        print("Error: No animations defined")
        return 1

    # Find max frames across all animations
    max_frames = max(len(anim["frames"]) for anim in animations.values())
    num_animations = len(animations)

    print(f"Animations: {list(animations.keys())}")
    print(f"Grid: {num_animations} rows x {max_frames} columns")
    print(f"Frame size: {frame_size[0]}x{frame_size[1]}")

    # Create spritesheet
    sheet_width = max_frames * frame_size[0]
    sheet_height = num_animations * frame_size[1]
    spritesheet = Image.new("RGBA", (sheet_width, sheet_height), (0, 0, 0, 0))

    # Load and place frames
    frames_dir = project_dir / "frames"

    for row, (anim_name, anim_data) in enumerate(animations.items()):
        frames = anim_data["frames"]
        print(f"  {anim_name}: {len(frames)} frames")

        last_frame = None
        for col in range(max_frames):
            if col < len(frames):
                frame_info = frames[col]
                frame_path = frames_dir / frame_info["extracted"]
                if frame_path.exists():
                    frame_img = Image.open(frame_path).convert("RGBA")
                    last_frame = frame_img
                else:
                    print(f"    Warning: Missing {frame_path}")
                    frame_img = last_frame
            else:
                # Pad with last frame
                frame_img = last_frame

            if frame_img:
                x = col * frame_size[0]
                y = row * frame_size[1]

                # Handle size mismatch by centering
                if frame_img.size != frame_size:
                    # Create a correctly sized frame and paste centered
                    correct_frame = Image.new("RGBA", frame_size, (0, 0, 0, 0))
                    offset_x = (frame_size[0] - frame_img.size[0]) // 2
                    offset_y = (frame_size[1] - frame_img.size[1]) // 2
                    correct_frame.paste(frame_img, (offset_x, offset_y))
                    frame_img = correct_frame

                spritesheet.paste(frame_img, (x, y))

    # Save spritesheet
    output_path = project_dir / "spritesheet.png"
    spritesheet.save(output_path)
    print(f"\nSaved spritesheet: {output_path}")
    print(f"  Size: {sheet_width}x{sheet_height}")

    # Update metadata with spritesheet info
    metadata["spritesheet"] = {
        "rows": num_animations,
        "cols": max_frames,
        "width": sheet_width,
        "height": sheet_height,
        "animation_order": list(animations.keys())
    }
    save_metadata(project_dir, metadata)

    return 0


def cmd_show(args) -> int:
    """Show project status."""
    project_dir: Path = args.project_dir

    # Load metadata
    metadata = load_metadata(project_dir)

    print(f"Project: {project_dir}")
    print(f"Character: {metadata['character_prompt']}")
    if "cell_size" in metadata:
        print(f"Cell size: {metadata['cell_size'][0]}x{metadata['cell_size'][1]}")
    if "requested_resolution" in metadata:
        print(f"Requested resolution: {metadata['requested_resolution'][0]}x{metadata['requested_resolution'][1]}")
    print(f"Frame size: {metadata['frame_size'][0]}x{metadata['frame_size'][1]}")

    # Show palette if defined
    if "palette" in metadata:
        palette = palette_from_json(metadata["palette"])
        print(f"Palette: {len(palette)} colors")
        for i, color in enumerate(palette):
            print(f"  {i+1}. {color_to_hex(color)} - RGB({color[0]}, {color[1]}, {color[2]})")
    print()

    print("Animations:")
    for anim_name, anim_data in metadata["animations"].items():
        frames = anim_data["frames"]
        print(f"  {anim_name}: {len(frames)} frames")
        for i, frame in enumerate(frames):
            prompt = frame.get("prompt") or "(base)"
            print(f"    [{i}] {prompt}")

    print()

    # Check for spritesheet
    spritesheet_path = project_dir / "spritesheet.png"
    if spritesheet_path.exists():
        print(f"Spritesheet: {spritesheet_path}")
        if "spritesheet" in metadata:
            info = metadata["spritesheet"]
            print(f"  Size: {info['width']}x{info['height']}")
            print(f"  Grid: {info['rows']} rows x {info['cols']} columns")

        # Try to open with default viewer
        if sys.platform == "linux":
            subprocess.Popen(["xdg-open", str(spritesheet_path)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(spritesheet_path)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        print("Spritesheet: not built yet (run 'build' command)")

    return 0


def cmd_quantize(args) -> int:
    """Quantize all frames to a shared palette."""
    project_dir: Path = args.project_dir
    max_colors = args.colors  # None means auto-detect

    print(f"Quantizing project: {project_dir}")
    if max_colors is not None:
        print(f"Colors: {max_colors}")
    else:
        print(f"Colors: auto-detect")
    print()

    try:
        palette = unify_project_palette(project_dir, max_colors)
        print(f"\nProject quantized to {len(palette)} colors!")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Build spritesheets using Gemini and pixelgrid extraction"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # init
    p_init = subparsers.add_parser("init", help="Initialize a new project")
    p_init.add_argument("project_dir", type=Path, help="Project directory")
    p_init.add_argument("character_prompt", help="Description of the character")
    p_init.add_argument("--cell-size", default="10x20",
                        help="Cell size as WxH (default: 10x20). Frame dimensions will be multiples of this.")
    p_init.add_argument("--resolution", default=None,
                        help="Requested resolution as WxH. Hint for Gemini (default: 2 cells wide x 1 cell tall).")
    p_init.add_argument("--no-quantize", action="store_true",
                        help="Skip automatic palette extraction and quantization")
    p_init.add_argument("--colors", type=int, default=None,
                        help="Number of palette colors (default: auto-detect)")

    # add-frame
    p_add = subparsers.add_parser("add-frame", help="Add a frame to an animation")
    p_add.add_argument("project_dir", type=Path, help="Project directory")
    p_add.add_argument("animation", help="Animation name (e.g., 'idle', 'walk')")
    p_add.add_argument("frame_prompt", help="Description of what this frame shows")
    p_add.add_argument("--no-quantize", action="store_true",
                       help="Skip automatic quantization to project palette")

    # build
    p_build = subparsers.add_parser("build", help="Build the spritesheet")
    p_build.add_argument("project_dir", type=Path, help="Project directory")

    # show
    p_show = subparsers.add_parser("show", help="Show project status")
    p_show.add_argument("project_dir", type=Path, help="Project directory")

    # quantize
    p_quantize = subparsers.add_parser("quantize", help="Quantize all frames to shared palette")
    p_quantize.add_argument("project_dir", type=Path, help="Project directory")
    p_quantize.add_argument("--colors", "-c", type=int, default=None,
                            help="Number of palette colors (default: auto-detect)")

    args = parser.parse_args()

    # Check for API key
    if args.command in ("init", "add-frame"):
        if not os.environ.get("GOOGLE_API_KEY") and not os.environ.get("GEMINI_API_KEY"):
            print("Error: GOOGLE_API_KEY or GEMINI_API_KEY environment variable not set")
            print("Get an API key from https://aistudio.google.com/")
            sys.exit(1)
        if not os.environ.get("GOOGLE_API_KEY") and os.environ.get("GEMINI_API_KEY"):
            os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

    # Dispatch to command
    if args.command == "init":
        sys.exit(cmd_init(args))
    elif args.command == "add-frame":
        sys.exit(cmd_add_frame(args))
    elif args.command == "build":
        sys.exit(cmd_build(args))
    elif args.command == "show":
        sys.exit(cmd_show(args))
    elif args.command == "quantize":
        sys.exit(cmd_quantize(args))


if __name__ == "__main__":
    main()
