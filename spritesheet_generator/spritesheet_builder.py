#!/usr/bin/env python3
"""
Spritesheet Builder

Builds spritesheets using Gemini image generation and pixelgrid extraction.
Generates consistent pixel art animations with automatic palette management.

Single sprite generation (for inventory items, etc.):
    python3 spritesheet_builder.py single items/iron_ore.png "iron ore"
    python3 spritesheet_builder.py single items/silk.png "silk thread" --cell-size 16x16
    python3 spritesheet_builder.py single items/sword.png "iron sword" --colors 8

Example workflow for animated spritesheets:
    # 1. Create project with base sprite
    python3 spritesheet_builder.py init output/warrior "a warrior with sword and shield" \\
        --style "Few colors and simple shapes"

    # 2. Add animation frames
    python3 spritesheet_builder.py add-frame output/warrior idle "eyes closed, blinking"
    python3 spritesheet_builder.py add-frame output/warrior walk "left foot forward"
    python3 spritesheet_builder.py add-frame output/warrior walk "right foot forward"

    # 3. Build spritesheet
    python3 spritesheet_builder.py build output/warrior

    # 4. Preview animation
    python3 demo_spritesheet.py output/warrior

Init options:
    --style TEXT        Extra style instructions (e.g., "Few colors and simple shapes")
    --sensitivity N     Color detection sensitivity, higher = more colors (default: 2.5)
    --colors N          Force specific palette size (default: auto-detect)
    --cell-size WxH     Frame size rounding (default: 10x20)
    --resolution WxH    Gemini size hint (default: 20x20)

Project structure:
    output/warrior/
    ├── raw/                    # Gemini outputs and references
    ├── frames/                 # Extracted pixel art frames
    ├── metadata.json           # Project config and palette
    └── spritesheet.png         # Final spritesheet (after build)

Requires GOOGLE_API_KEY or GEMINI_API_KEY environment variable.
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
    snap_palette_greys,
    is_near_grey,
    DEFAULT_SENSITIVITY,
    DEFAULT_GREY_THRESHOLD,
)


# =============================================================================
# CONFIGURATION
# =============================================================================

STYLE_PROMPT = """The image should be on a solid bright green (#00FF00) background for easy chroma keying.
The character should be centered, showing their full side profile.
CRITICAL: The ENTIRE character must fit within the image with large margins. Every body part - head, ears, tail, legs, arms, wings - must be fully visible with space around them. Nothing can touch or go past any edge. Make the character small enough to leave 20% empty green space on all sides.
No shadows on the green background.
The green background should be completely uniform #00FF00.
The entire image should be filled with the green background, edge to edge, no white or other colors."""

# For animation frames - no margin requirements since limbs may extend
FRAME_STYLE_PROMPT = """The image should be on a solid bright green (#00FF00) background for easy chroma keying.
No shadows on the green background.
The green background should be completely uniform #00FF00.
The entire image should be filled with the green background, edge to edge, no white or other colors."""

# For single item sprites (inventory icons)
ITEM_STYLE_PROMPT = """The image should be on a solid bright green (#00FF00) background for easy chroma keying.
The item should be centered and fill most of the frame with a small margin.
Top-down or 3/4 isometric view typical of crafting game inventory icons.
Extremely simple, chunky pixel art style.
Use flat solid colors with NO gradients, NO shading, NO anti-aliasing, NO outlines.
Bold, recognizable silhouette. Maximum 8-12 colors.
The green background must be completely uniform #00FF00.
Fill the entire image edge-to-edge with green background, no other background colors."""

METADATA_FILENAME = "metadata.json"


# =============================================================================
# FRAME SIZE HELPERS
# =============================================================================

def round_to_cell_multiple(size: Tuple[int, int], cell_size: Tuple[int, int]) -> Tuple[int, int]:
    """Round dimensions up to nearest cell_size multiple."""
    cell_w, cell_h = cell_size
    w = ((size[0] + cell_w - 1) // cell_w) * cell_w
    h = ((size[1] + cell_h - 1) // cell_h) * cell_h
    return (int(w), int(h))


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
    """Re-extract all existing frames from raw images with new_frame_size."""
    frames_dir = project_dir / "frames"
    raw_dir = project_dir / "raw"
    old_size = tuple(metadata["frame_size"])

    print(f"Expanding frames from {old_size[0]}x{old_size[1]} to {new_frame_size[0]}x{new_frame_size[1]}")

    # Get hint_cell_size from stored reference scale
    reference_scale = metadata["reference_scale"]
    hint_cell_size = (reference_scale, reference_scale)

    # Get palette for re-quantization
    palette = get_project_palette(project_dir)

    # Track which files we've already processed
    processed_files = set()

    for anim_name, anim_data in metadata["animations"].items():
        for frame_info in anim_data["frames"]:
            extracted_filename = frame_info["extracted"]
            if extracted_filename in processed_files:
                continue
            processed_files.add(extracted_filename)

            raw_filename = frame_info["raw"]
            raw_path = raw_dir / raw_filename
            frame_path = frames_dir / extracted_filename

            if raw_path.exists():
                # Re-extract from raw with new target size
                print(f"  Re-extracting: {extracted_filename} from {raw_filename}")
                _, _, _ = extract_sprite(raw_path, frame_path,
                                         hint_cell_size=hint_cell_size,
                                         target_frame_size=new_frame_size)

                # Re-quantize to palette
                if palette:
                    frame_img = Image.open(frame_path).convert("RGBA")
                    quantized = quantize_to_palette(frame_img, palette)
                    quantized.save(frame_path)

    metadata["frame_size"] = list(new_frame_size)


# =============================================================================
# GEMINI IMAGE GENERATION
# =============================================================================

def prepare_reference_image(sprite_path: Path, target_size: int = 1024) -> Tuple[bytes, int]:
    """
    Scale up a small sprite and place on green background for use as reference.

    The sprite is scaled to fill 40% of the target size (30% margin on each side),
    matching the STYLE_PROMPT instructions given to Gemini.

    Returns (PNG image data as bytes, scale factor used).
    """
    sprite = Image.open(sprite_path).convert("RGBA")

    # Calculate scale to fill 40% of target (30% margin on each side)
    sprite_area = target_size * 0.4
    scale = int(sprite_area / max(sprite.width, sprite.height))

    # Scale up using nearest neighbor to preserve pixel art
    scaled_size = (sprite.width * scale, sprite.height * scale)
    scaled = sprite.resize(scaled_size, Image.Resampling.NEAREST)

    # Create square green background
    background = Image.new("RGBA", (target_size, target_size), (0, 255, 0, 255))

    # Paste scaled sprite centered on background
    paste_x = (target_size - scaled_size[0]) // 2
    paste_y = (target_size - scaled_size[1]) // 2
    background.paste(scaled, (paste_x, paste_y), scaled)

    # Convert to bytes
    import io
    buffer = io.BytesIO()
    background.save(buffer, format="PNG")
    return buffer.getvalue(), scale


def generate_image(full_prompt: str, output_path: Path, reference_image: Optional[Path] = None) -> Path:
    """
    Generate image with Gemini, optionally using a reference image.

    Args:
        full_prompt: The generation prompt
        output_path: Where to save the generated image
        reference_image: Path to a reference image file to send to Gemini
    """
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
        config=types.GenerateContentConfig(
            response_modalities=["image", "text"],
            image_config=types.ImageConfig(
                aspect_ratio="1:1",
            ),
        ),
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


def build_base_prompt(character_prompt: str, requested_resolution: Optional[Tuple[int, int]] = None,
                      extra_instructions: Optional[str] = None) -> str:
    """Build prompt for base idle sprite."""
    resolution_hint = ""
    if requested_resolution:
        resolution_hint = f"\nThe character should be {requested_resolution[0]}x{requested_resolution[1]} pixels in size."
    extra = f"\n{extra_instructions}" if extra_instructions else ""
    return f"""Create pixel art of {character_prompt}, side-on view, facing right.{resolution_hint}{extra}
{STYLE_PROMPT}"""


def build_frame_prompt(character_prompt: str, frame_prompt: str, requested_resolution: Optional[Tuple[int, int]] = None,
                       extra_instructions: Optional[str] = None) -> str:
    """Build prompt for an animation frame with reference image."""
    resolution_hint = ""
    if requested_resolution:
        resolution_hint = f"\nThe character should be {requested_resolution[0]}x{requested_resolution[1]} pixels in size."
    extra = f"\n{extra_instructions}" if extra_instructions else ""
    return f"""The attached image shows the base sprite for {character_prompt}.
Create a new frame of this EXACT same character showing: {frame_prompt}
The character must look identical - same colors, same proportions, same style.
Only the pose/action should change.{resolution_hint}{extra}
{FRAME_STYLE_PROMPT}"""


# =============================================================================
# PIXELGRID EXTRACTION
# =============================================================================

def extract_sprite(raw_path: Path, output_path: Path,
                   hint_cell_size: Optional[Tuple[int, int]] = None,
                   target_frame_size: Optional[Tuple[int, int]] = None) -> Tuple[Tuple[int, int], Tuple[int, int], Tuple[int, int, int, int]]:
    """
    Extract pixels using pixelgrid.

    Args:
        raw_path: Path to raw Gemini output
        output_path: Path to save extracted sprite
        hint_cell_size: Optional (width, height) to use instead of auto-detection
        target_frame_size: If provided, extract this size from grid center (preserves Gemini's positioning)

    Returns:
        ((sprite_width, sprite_height), (cell_width, cell_height), (left, top, right, bottom))
        where the third tuple is content bounds relative to grid center
    """
    img = Image.open(raw_path)
    print(f"Raw image size: {img.size}")

    # Detect grid (or use hint)
    if hint_cell_size:
        cell_width, cell_height = hint_cell_size
        print(f"Using cell size hint: {cell_width}x{cell_height}")
    else:
        cell_width, cell_height = detect_grid_size(img)
        print(f"Detected cell size: {cell_width}x{cell_height}")

    # Find best offset
    offset_x, offset_y = find_best_offset(img, cell_width, cell_height)
    print(f"Detected offset: ({offset_x}, {offset_y})")

    # Refine grid lines
    x_lines, y_lines = refine_grid_lines(img, cell_width, cell_height, offset_x, offset_y)
    grid_width = len(x_lines) - 1
    grid_height = len(y_lines) - 1
    print(f"Grid: {grid_width} x {grid_height} cells")

    # Extract pixels
    pixel_img, bbox = extract_pixels(img, x_lines, y_lines, remove_green=True)
    print(f"Content bbox: x={bbox[0]}, y={bbox[1]}, w={bbox[2]}, h={bbox[3]}")

    # Get content bounds relative to grid center
    center_x = grid_width // 2
    center_y = grid_height // 2
    content_left, content_top, content_w, content_h = bbox

    # Content bounds relative to grid center
    rel_content = (
        content_left - center_x,  # left relative to center
        content_top - center_y,   # top relative to center
        content_left + content_w - center_x,  # right relative to center
        content_top + content_h - center_y,   # bottom relative to center
    )

    if target_frame_size:
        # Extract region of target_frame_size centered on grid
        target_w, target_h = target_frame_size
        left = center_x - target_w // 2
        top = center_y - target_h // 2
        right = left + target_w
        bottom = top + target_h

        # Clamp to grid bounds
        left = max(0, left)
        top = max(0, top)
        right = min(grid_width, right)
        bottom = min(grid_height, bottom)

        result = pixel_img.crop((left, top, right, bottom))
        print(f"Extracted region: ({left}, {top}) to ({right}, {bottom})")
        result.save(output_path)
        print(f"Saved extracted sprite: {output_path} ({result.size[0]}x{result.size[1]})")
        return result.size, (cell_width, cell_height), rel_content
    else:
        # For init - crop to content
        cropped = crop_to_content(pixel_img, bbox)
        cropped.save(output_path)
        print(f"Saved extracted sprite: {output_path} ({cropped.size[0]}x{cropped.size[1]})")
        return cropped.size, (cell_width, cell_height), rel_content


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
    style_instructions: Optional[str] = None,
    detected_cell_size: Optional[Tuple[int, int]] = None,
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
    if style_instructions:
        metadata["style_instructions"] = style_instructions
    if detected_cell_size:
        metadata["detected_cell_size"] = list(detected_cell_size)
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
    style_instructions: Optional[str] = args.style
    if args.resolution:
        requested_resolution: Tuple[int, int] = parse_size_arg(args.resolution)
    else:
        # Default: 2 cells wide x 1 cell tall
        requested_resolution = (cell_size[0] * 2, cell_size[1])

    print(f"Initializing project: {project_dir}")
    print(f"Character: {character_prompt}")
    print(f"Cell size: {cell_size[0]}x{cell_size[1]}")
    print(f"Requested resolution: {requested_resolution[0]}x{requested_resolution[1]}")
    if style_instructions:
        print(f"Style: {style_instructions}")

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
    prompt = build_base_prompt(character_prompt, requested_resolution, style_instructions)
    generate_image(prompt, raw_path)

    # Extract pixels
    frames_path = project_dir / "frames" / "idle_0.png"
    extracted_size, detected_cell_size, rel_content = extract_sprite(raw_path, frames_path)

    # Content bounds relative to grid center: (left, top, right, bottom)
    # Frame size needs to fit content on both sides of center
    content_extent_w = max(abs(rel_content[0]), abs(rel_content[2])) * 2
    content_extent_h = max(abs(rel_content[1]), abs(rel_content[3])) * 2
    frame_size = round_to_cell_multiple((content_extent_w, content_extent_h), cell_size)
    print(f"Content bounds: {rel_content}")
    print(f"Frame size: {frame_size[0]}x{frame_size[1]}")

    # Pad the extracted frame to the target frame size
    if extracted_size != frame_size:
        frame_img = Image.open(frames_path).convert("RGBA")
        padded = pad_frame_to_size(frame_img, frame_size)
        padded.save(frames_path)

    # Initialize metadata
    metadata = init_metadata(character_prompt, cell_size, frame_size, requested_resolution, style_instructions, detected_cell_size)
    # Store content bounds (relative to grid center) for union tracking
    # Convert to Python ints to ensure JSON serialization works
    metadata["content_bounds"] = [int(x) for x in rel_content]  # [left, top, right, bottom]
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
            num_colors = detect_optimal_colors(base_img, sensitivity=args.sensitivity)
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

    # Create reference image from idle_0 for consistent positioning during re-extraction
    reference_data, reference_scale = prepare_reference_image(frames_path)
    reference_path = project_dir / "raw" / "idle_base_reference.png"
    with open(reference_path, "wb") as f:
        f.write(reference_data)
    print(f"Saved reference image: {reference_path} (scale: {reference_scale}x)")
    metadata["reference_scale"] = reference_scale

    # Update metadata to use reference image as "raw" for idle_0
    metadata["animations"]["idle"]["frames"][0]["raw"] = "idle_base_reference.png"

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
    style_instructions = metadata.get("style_instructions")

    # Get or create animation
    if animation not in metadata["animations"]:
        print(f"Creating new animation: {animation}")
        metadata["animations"][animation] = {
            "frames": []
        }

    anim_data = metadata["animations"][animation]
    frame_num = len(anim_data["frames"])

    # Generate image using the stored reference image
    raw_filename = f"{animation}_frame_{frame_num}.png"
    raw_path = project_dir / "raw" / raw_filename
    reference_image = project_dir / "raw" / "idle_base_reference.png"

    prompt = build_frame_prompt(character_prompt, frame_prompt, requested_resolution, style_instructions)
    generate_image(prompt, raw_path, reference_image=reference_image)

    # Get the scale from metadata for cell size hint
    reference_scale = metadata["reference_scale"]
    hint_cell_size = (reference_scale, reference_scale)

    # Extract pixels with current frame size
    extracted_filename = f"{animation}_{frame_num}.png"
    extracted_path = project_dir / "frames" / extracted_filename
    extracted_size, _, rel_content = extract_sprite(raw_path, extracted_path,
                                                    hint_cell_size=hint_cell_size,
                                                    target_frame_size=current_frame_size)

    # Check if new content extends beyond current bounds
    current_bounds = metadata.get("content_bounds", [0, 0, 0, 0])
    new_bounds = [
        int(min(current_bounds[0], rel_content[0])),  # left
        int(min(current_bounds[1], rel_content[1])),  # top
        int(max(current_bounds[2], rel_content[2])),  # right
        int(max(current_bounds[3], rel_content[3])),  # bottom
    ]

    if new_bounds != current_bounds:
        # Content bounds expanded - calculate new frame size
        content_extent_w = max(abs(new_bounds[0]), abs(new_bounds[2])) * 2
        content_extent_h = max(abs(new_bounds[1]), abs(new_bounds[3])) * 2
        new_frame_size = round_to_cell_multiple((content_extent_w, content_extent_h), cell_size)

        if new_frame_size != current_frame_size:
            print(f"Content bounds expanded, re-extracting all frames...")
            print(f"  Old bounds: {current_bounds}")
            print(f"  New bounds: {new_bounds}")
            metadata["content_bounds"] = new_bounds
            expand_all_frames(project_dir, metadata, new_frame_size)
            # Re-extract this frame with new size
            extracted_size, _, _ = extract_sprite(raw_path, extracted_path,
                                                  hint_cell_size=hint_cell_size,
                                                  target_frame_size=new_frame_size)
        else:
            metadata["content_bounds"] = new_bounds

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

        for col in range(max_frames):
            frame_img = None
            if col < len(frames):
                frame_info = frames[col]
                frame_path = frames_dir / frame_info["extracted"]
                if frame_path.exists():
                    frame_img = Image.open(frame_path).convert("RGBA")
                else:
                    print(f"    Warning: Missing {frame_path}")
            # Leave blank for missing frames (don't pad)

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
    sensitivity = getattr(args, 'sensitivity', DEFAULT_SENSITIVITY)

    print(f"Quantizing project: {project_dir}")
    if max_colors is not None:
        print(f"Colors: {max_colors}")
    else:
        print(f"Colors: auto-detect (sensitivity: {sensitivity})")
    print()

    try:
        palette = unify_project_palette(project_dir, max_colors, sensitivity=sensitivity)
        print(f"\nProject quantized to {len(palette)} colors!")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


def find_dominant_color(img: Image.Image) -> Tuple[int, int, int]:
    """Find the most common color in an image (ignoring transparency)."""
    from collections import Counter
    img = img.convert("RGBA")
    pixels = list(img.getdata())
    # Filter out transparent pixels
    opaque = [p[:3] for p in pixels if p[3] > 0]
    if not opaque:
        return (128, 128, 128)
    most_common = Counter(opaque).most_common(1)[0][0]
    return most_common


def cmd_single(args) -> int:
    """Generate a single sprite without project scaffolding."""
    import tempfile

    output_path: Path = args.output
    subject: str = args.subject
    custom_prompt: Optional[str] = args.prompt
    cell_size: Tuple[int, int] = parse_size_arg(args.cell_size)
    resolution: Tuple[int, int] = parse_size_arg(args.resolution) if args.resolution else cell_size
    colors: Optional[int] = args.colors
    sensitivity: float = args.sensitivity
    color_role: Optional[str] = args.color_role
    # Snap greys only if explicitly requested OR if color_role is "taker"
    snap_greys: bool = args.snap_greys or (color_role == "taker")
    color_input: Optional[int] = args.color_input
    source_color_arg: Optional[str] = args.source_color
    palette_hint: Optional[str] = args.palette_hint
    palette_from: Optional[Path] = args.palette_from

    # Build the prompt
    if custom_prompt:
        full_prompt = custom_prompt
    else:
        palette_instruction = ""
        if palette_hint:
            palette_instruction = f"\nUse these colors: {palette_hint}."

        full_prompt = f"""Create pixel art of "{subject}" for a crafting game inventory icon.
The item should be {resolution[0]}x{resolution[1]} pixels in size.{palette_instruction}
{ITEM_STYLE_PROMPT}"""

    print(f"Generating: {subject}")
    print(f"Output: {output_path}")
    print(f"Resolution hint: {resolution[0]}x{resolution[1]}")
    print(f"Cell size: {cell_size[0]}x{cell_size[1]}")
    if palette_hint:
        print(f"Palette hint: {palette_hint}")
    if snap_greys:
        print(f"Snap greys: enabled")

    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Use temp directory for raw image
    with tempfile.TemporaryDirectory() as tmpdir:
        raw_path = Path(tmpdir) / "raw.png"

        # Generate image
        generate_image(full_prompt, raw_path)

        # Extract pixels using pixelgrid (crops to content)
        extracted_path = Path(tmpdir) / "extracted.png"
        extracted_size, detected_cell_size, _ = extract_sprite(raw_path, extracted_path)

        # Load extracted sprite
        result = Image.open(extracted_path).convert("RGBA")
        print(f"Extracted size: {result.size[0]}x{result.size[1]}")

        # Quantize
        palette = None
        if not args.no_quantize:
            # Load palette from another item, or extract new one
            if palette_from:
                with open(palette_from) as f:
                    source_meta = json.load(f)
                palette = palette_from_json(source_meta["palette"])
                print(f"Using palette from {palette_from} ({len(palette)} colors)")
            else:
                num_colors = colors
                if num_colors is None:
                    num_colors = detect_optimal_colors(result, sensitivity=sensitivity)
                    print(f"Auto-detected {num_colors} colors")

                palette = extract_palette(result, num_colors)

                # Snap near-grey colors to exact grey
                if snap_greys:
                    palette = snap_palette_greys(palette)
                    print(f"Snapped near-greys to exact grey")

            result = quantize_to_palette(result, palette)
            print(f"Quantized to {len(palette)} colors")

        # Pad to nearest cell_size multiple
        frame_size = round_to_cell_multiple(result.size, cell_size)
        if result.size != frame_size:
            result = pad_frame_to_size(result, frame_size)
            print(f"Padded to: {frame_size[0]}x{frame_size[1]}")

        result.save(output_path)
        print(f"Saved: {output_path} ({result.size[0]}x{result.size[1]})")

        # Show preview: raw Gemini image and scaled-up result side by side
        raw_img = Image.open(raw_path)
        # Scale up result to be visible (10x)
        scale = 10
        result_scaled = result.resize(
            (result.size[0] * scale, result.size[1] * scale),
            Image.Resampling.NEAREST
        )
        # Create side-by-side comparison
        # Resize raw to match height of scaled result
        raw_height = result_scaled.size[1]
        raw_aspect = raw_img.size[0] / raw_img.size[1]
        raw_resized = raw_img.resize(
            (int(raw_height * raw_aspect), raw_height),
            Image.Resampling.LANCZOS
        )
        # Combine
        preview_width = raw_resized.size[0] + result_scaled.size[0] + 10
        preview = Image.new("RGBA", (preview_width, raw_height), (40, 40, 40, 255))
        preview.paste(raw_resized, (0, 0))
        preview.paste(result_scaled, (raw_resized.size[0] + 10, 0))
        preview_path = output_path.parent / f"{output_path.stem}_preview.png"
        preview.save(preview_path)
        subprocess.run(["xdg-open", str(preview_path)], check=False)

        # Build and save metadata
        metadata = {
            "name": subject,
        }

        if palette:
            metadata["palette"] = palette_to_json(palette)

        if color_role:
            metadata["color_role"] = color_role
            if color_role == "source":
                # Determine source color
                if source_color_arg:
                    # Parse "R,G,B" format
                    parts = [int(x.strip()) for x in source_color_arg.split(",")]
                    source_color = tuple(parts[:3])
                else:
                    # Auto-detect dominant color
                    source_color = find_dominant_color(result)
                metadata["source_color"] = list(source_color)
                print(f"Source color: RGB{source_color}")
            elif color_role == "taker":
                if color_input is not None:
                    metadata["color_input_index"] = color_input
                    print(f"Color input index: {color_input}")

        # Save metadata JSON
        metadata_path = output_path.with_suffix(".json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        print(f"Saved metadata: {metadata_path}")

    return 0


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
    p_init.add_argument("--sensitivity", "-s", type=float, default=DEFAULT_SENSITIVITY,
                        help=f"Sensitivity for color auto-detection (default: {DEFAULT_SENSITIVITY})")
    p_init.add_argument("--style", type=str, default=None,
                        help="Extra style instructions for generation (e.g., 'Few colors and simple shapes')")

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
    p_quantize.add_argument("--sensitivity", "-s", type=float, default=DEFAULT_SENSITIVITY,
                            help=f"Sensitivity for auto-detection (higher = more colors, default: {DEFAULT_SENSITIVITY})")

    # single
    p_single = subparsers.add_parser("single", help="Generate a single sprite (no project scaffolding)")
    p_single.add_argument("output", type=Path, help="Output file path (e.g., items/iron_ore.png)")
    p_single.add_argument("subject", help="What to generate (e.g., 'iron ore', 'wooden plank')")
    p_single.add_argument("--prompt", type=str, default=None,
                          help="Override the full prompt (ignores subject)")
    p_single.add_argument("--cell-size", default="10x20",
                          help="Frame size rounding as WxH (default: 10x20)")
    p_single.add_argument("--resolution", default=None,
                          help="Resolution hint for Gemini as WxH (default: same as cell-size)")
    p_single.add_argument("--colors", "-c", type=int, default=None,
                          help="Number of palette colors (default: auto-detect)")
    p_single.add_argument("--sensitivity", "-s", type=float, default=DEFAULT_SENSITIVITY,
                          help=f"Sensitivity for color auto-detection (default: {DEFAULT_SENSITIVITY})")
    p_single.add_argument("--no-quantize", action="store_true",
                          help="Skip palette quantization")
    p_single.add_argument("--snap-greys", action="store_true",
                          help="Snap near-grey colors to exact grey (auto-enabled for takers)")
    p_single.add_argument("--palette-hint", type=str, default=None,
                          help="Color hints for Gemini (e.g., 'silver grey, dark grey')")
    p_single.add_argument("--color-role", choices=["source", "taker"], default=None,
                          help="Color role: 'source' provides color, 'taker' receives color from inputs")
    p_single.add_argument("--color-input", type=int, default=None,
                          help="For takers: which recipe input index provides the color")
    p_single.add_argument("--source-color", type=str, default=None,
                          help="For sources: the color provided as 'R,G,B' (default: auto-detect)")
    p_single.add_argument("--palette-from", type=Path, default=None,
                          help="Use palette from another item's JSON (e.g., item_sprites/silkworm_cacoons.json)")

    args = parser.parse_args()

    # Check for API key
    if args.command in ("init", "add-frame", "single"):
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
    elif args.command == "single":
        sys.exit(cmd_single(args))


if __name__ == "__main__":
    main()
