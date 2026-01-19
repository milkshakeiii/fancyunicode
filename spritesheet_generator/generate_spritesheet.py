#!/usr/bin/env python3
"""
Spritesheet Generator - Experimental Script

Generates pixel-art spritesheets by:
1. Using Gemini API to create a base sprite image (with green background)
2. Using Veo 3.1 to animate the sprite (image-to-video)
3. Extracting frames from the video
4. Converting frames to very small pixel art (as small as 10x20 pixels)
5. Removing green background via chroma keying
6. Assembling frames into a PNG spritesheet row

Usage:
    python generate_spritesheet.py
    python generate_spritesheet.py --subject "slime" --width 10 --height 20

Requires GOOGLE_API_KEY environment variable to be set.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image

# =============================================================================
# CONFIGURATION - Easy to tweak for experimentation
# =============================================================================

SUBJECT = "warrior"
ANIMATION_TYPE = "walk cycle"
TARGET_WIDTH = 20
TARGET_HEIGHT = 20
FRAME_COUNT = 8
VIDEO_DURATION = 4  # seconds (4-8 for Veo 3.1)
GREEN_TOLERANCE = 50  # chroma key tolerance (0-255)
DOWNSAMPLE_MODE = "mode"  # "mode" (most-frequent-color) or "average" (box filter)
TRANSPARENCY_THRESHOLD = 240  # alpha values below this are considered transparent

# Green screen color
GREEN_SCREEN_COLOR = (0, 255, 0)  # #00FF00

# Output directory
OUTPUT_DIR = Path(__file__).parent / "output"


# =============================================================================
# GEMINI IMAGE GENERATION
# =============================================================================

def generate_base_sprite(
    subject: str,
    output_path: Path,
    target_width: int = 20,
    target_height: int = 20,
    style: str = "pixel art",
    view: str = "side view",
) -> Path:
    """Generate a base sprite using Gemini image generation."""
    from google import genai

    client = genai.Client()

    prompt = f"""Create a {target_width}x{target_height} pixel {style} sprite of a {subject}, {view}.
The sprite should be on a solid bright green (#00FF00) background for easy chroma keying.
The character should be centered and facing right.
Simple, clean pixel art style suitable for a 2D game. Keep details bold and simple for the small size.
No shadows on the green background.
The green background should be completely uniform #00FF00.
The entire image should be filled with the green background, edge to edge, no white or other colors."""

    print(f"Generating base sprite with prompt:\n{prompt}\n")

    response = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=[prompt],
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
            print(f"Saved base sprite to {output_path}")
            return output_path

    raise RuntimeError("No image generated in response")


# =============================================================================
# VEO VIDEO GENERATION
# =============================================================================

def generate_animation_video(
    image_path: Path,
    output_path: Path,
    animation_prompt: str,
    duration_seconds: int = 2,
) -> Path:
    """Generate animation video from base sprite using Veo 3.1."""
    from google import genai
    from google.genai import types

    client = genai.Client()

    # Upload the image file
    print(f"Uploading image {image_path}...")
    with open(image_path, "rb") as f:
        image_data = f.read()

    # Create the image for Veo
    image = types.Image(
        image_bytes=image_data,
        mime_type="image/png",
    )

    full_prompt = f"""{animation_prompt}
Keep the character on the green background.
Smooth looping animation.
The character should stay centered in frame.
Maintain the pixel art style."""

    print(f"Generating animation with prompt:\n{full_prompt}\n")

    # Generate video
    operation = client.models.generate_videos(
        model="veo-3.1-generate-preview",
        prompt=full_prompt,
        image=image,
        config=types.GenerateVideosConfig(
            duration_seconds=duration_seconds,
            number_of_videos=1,
        ),
    )

    # Poll for completion
    print("Waiting for video generation...")
    while not operation.done:
        time.sleep(5)
        operation = client.operations.get(operation)
        print("  Still generating...")

    if operation.error:
        raise RuntimeError(f"Video generation failed: {operation.error}")

    # Download the video
    video = operation.result.generated_videos[0]
    video_data = client.files.download(file=video.video)

    # video_data may be bytes or a generator
    with open(output_path, "wb") as f:
        if isinstance(video_data, bytes):
            f.write(video_data)
        else:
            for chunk in video_data:
                if isinstance(chunk, int):
                    # Single byte
                    f.write(bytes([chunk]))
                else:
                    f.write(chunk)

    print(f"Saved animation video to {output_path}")
    return output_path


# =============================================================================
# FRAME EXTRACTION
# =============================================================================

def extract_frames(
    video_path: Path,
    output_dir: Path,
    frame_count: int,
) -> List[Path]:
    """Extract evenly-spaced frames from video using ffmpeg."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get video duration using ffprobe
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ],
        capture_output=True,
        text=True,
    )
    duration = float(result.stdout.strip())
    print(f"Video duration: {duration:.2f}s")

    # Calculate frame rate to get desired number of frames
    fps = frame_count / duration

    # Extract frames
    output_pattern = output_dir / "frame_%04d.png"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i", str(video_path),
            "-vf", f"fps={fps}",
            str(output_pattern),
        ],
        capture_output=True,
    )

    # Collect extracted frames
    frames = sorted(output_dir.glob("frame_*.png"))[:frame_count]
    print(f"Extracted {len(frames)} frames")
    return frames


# =============================================================================
# CHROMA KEY BACKGROUND REMOVAL
# =============================================================================

def remove_green_background(
    image: Image.Image,
    tolerance: int = 50,
) -> Image.Image:
    """Remove green screen background using chroma keying."""
    # Convert to RGBA if needed
    if image.mode != "RGBA":
        image = image.convert("RGBA")

    # Convert to numpy for faster processing
    data = np.array(image)

    # Extract RGB channels
    r, g, b, a = data[:, :, 0], data[:, :, 1], data[:, :, 2], data[:, :, 3]

    # Find pixels close to GREEN_SCREEN_COLOR
    target_r, target_g, target_b = GREEN_SCREEN_COLOR
    green_mask = (
        (np.abs(r.astype(int) - target_r) < tolerance) &
        (np.abs(g.astype(int) - target_g) < tolerance) &
        (np.abs(b.astype(int) - target_b) < tolerance)
    )

    # Set alpha to 0 for green pixels
    data[:, :, 3] = np.where(green_mask, 0, a)

    return Image.fromarray(data)


# =============================================================================
# DOWNSAMPLING
# =============================================================================

def downsample_image(
    image: Image.Image,
    target_width: int,
    target_height: int,
    mode: str = "mode",
) -> Image.Image:
    """Downsample image to target size.

    Args:
        image: Source image (RGBA)
        target_width: Target width in pixels
        target_height: Target height in pixels
        mode: "mode" (most-frequent-color per block) or "average" (box filter)

    Returns:
        Downsampled RGBA image
    """
    if image.mode != "RGBA":
        image = image.convert("RGBA")

    orig_width, orig_height = image.size

    if mode == "average":
        # BOX resampling does area averaging
        return image.resize((target_width, target_height), Image.Resampling.BOX)

    elif mode == "mode":
        # Most frequent color per block - preserves hard edges
        block_w = orig_width / target_width
        block_h = orig_height / target_height
        new_img = Image.new("RGBA", (target_width, target_height))

        for out_y in range(target_height):
            for out_x in range(target_width):
                # Get all pixels in this block
                x0 = int(out_x * block_w)
                y0 = int(out_y * block_h)
                x1 = int((out_x + 1) * block_w)
                y1 = int((out_y + 1) * block_h)

                pixels = []
                for py in range(y0, min(y1, orig_height)):
                    for px in range(x0, min(x1, orig_width)):
                        pixels.append(image.getpixel((px, py)))

                if pixels:
                    # Find most frequent color
                    most_common = Counter(pixels).most_common(1)[0][0]
                    new_img.putpixel((out_x, out_y), most_common)

        return new_img

    else:
        raise ValueError(f"mode must be 'average' or 'mode', got '{mode}'")


# =============================================================================
# FRAME PROCESSING
# =============================================================================

def remove_letterbox(image: Image.Image, threshold: int = 20, verbose: bool = False) -> Image.Image:
    """Remove black letterbox/pillarbox bars from edges of image."""
    data = np.array(image)
    orig_width, orig_height = image.width, image.height

    # Find rows/cols that are mostly black (all RGB values < threshold)
    if image.mode == "RGBA":
        rgb = data[:, :, :3]
    else:
        rgb = data

    # A row is "black" if max RGB value across all pixels is below threshold
    row_max = rgb.max(axis=(1, 2))
    non_black_rows = np.where(row_max >= threshold)[0]

    # A column is "black" if max RGB value across all pixels is below threshold
    col_max = rgb.max(axis=(0, 2))
    non_black_cols = np.where(col_max >= threshold)[0]

    if len(non_black_rows) == 0 or len(non_black_cols) == 0:
        return image

    top = non_black_rows[0]
    bottom = non_black_rows[-1] + 1
    left = non_black_cols[0]
    right = non_black_cols[-1] + 1

    if verbose and (top > 0 or bottom < orig_height or left > 0 or right < orig_width):
        print(f"    Letterbox: removed {top}px top, {orig_height - bottom}px bottom, {left}px left, {orig_width - right}px right")

    return image.crop((left, top, right, bottom))


def get_content_bbox(image: Image.Image, min_alpha: int = 128, erode_pixels: int = 2) -> Optional[Tuple[int, int, int, int]]:
    """Get bounding box of non-transparent pixels, ignoring sparse artifacts.

    Args:
        image: RGBA image
        min_alpha: Minimum alpha value to consider as content
        erode_pixels: Erode the alpha mask by this many pixels to remove artifacts

    Returns (x_min, y_min, x_max, y_max) or None.
    """
    if image.mode != "RGBA":
        image = image.convert("RGBA")

    data = np.array(image)
    alpha = data[:, :, 3]

    # Threshold alpha
    mask = alpha >= min_alpha

    # Erode to remove sparse pixels (simple box erosion)
    if erode_pixels > 0:
        from scipy import ndimage
        struct = np.ones((erode_pixels * 2 + 1, erode_pixels * 2 + 1))
        mask = ndimage.binary_erosion(mask, structure=struct)
        # Dilate back to restore original size of real content
        mask = ndimage.binary_dilation(mask, structure=struct)

    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)

    if not rows.any() or not cols.any():
        return None

    y_min, y_max = np.where(rows)[0][[0, -1]]
    x_min, x_max = np.where(cols)[0][[0, -1]]

    return (x_min, y_min, x_max, y_max)


def union_bbox(bboxes: List[Tuple[int, int, int, int]]) -> Tuple[int, int, int, int]:
    """Compute union of multiple bounding boxes."""
    x_min = min(b[0] for b in bboxes)
    y_min = min(b[1] for b in bboxes)
    x_max = max(b[2] for b in bboxes)
    y_max = max(b[3] for b in bboxes)
    return (x_min, y_min, x_max, y_max)


def process_frames(
    frame_paths: List[Path],
    output_dir: Path,
    target_width: int,
    target_height: int,
    green_tolerance: int,
    downsample_mode: str,
    transparency_threshold: int,
    verbose: bool = True,
) -> List[Path]:
    """Process all frames with consistent cropping across the batch."""

    # Pass 1: Remove letterbox and green, collect bounding boxes
    if verbose:
        print("  Pass 1: Removing backgrounds and finding content bounds...")

    processed_images = []
    bboxes = []

    for frame_path in frame_paths:
        img = Image.open(frame_path).convert("RGBA")
        orig_size = img.size

        # Remove letterbox bars
        img = remove_letterbox(img, verbose=False)
        letterbox_size = img.size

        # Remove green background
        img = remove_green_background(img, tolerance=green_tolerance)

        # Get content bounding box
        bbox = get_content_bbox(img)

        if verbose:
            letterbox_removed = orig_size[1] - letterbox_size[1]
            print(f"    {frame_path.name}: {orig_size[0]}x{orig_size[1]}, letterbox: {letterbox_removed}px, bbox: {bbox}")

        processed_images.append(img)
        if bbox:
            bboxes.append(bbox)

    if not bboxes:
        raise ValueError("No content found in any frame")

    # Compute union bounding box
    final_bbox = union_bbox(bboxes)
    crop_width = final_bbox[2] - final_bbox[0] + 1
    crop_height = final_bbox[3] - final_bbox[1] + 1

    if verbose:
        print(f"\n  Union bounding box: x={final_bbox[0]}-{final_bbox[2]}, y={final_bbox[1]}-{final_bbox[3]}")
        print(f"  Content size: {crop_width}x{crop_height}")

    # Pass 2: Crop and downsample
    if verbose:
        print(f"\n  Pass 2: Cropping to union bbox and downsampling to {target_width}x{target_height}...")

    output_paths = []
    for i, img in enumerate(processed_images):
        # Crop to union bbox
        img = img.crop((final_bbox[0], final_bbox[1], final_bbox[2] + 1, final_bbox[3] + 1))

        # Downsample
        img = downsample_image(img, target_width, target_height, mode=downsample_mode)

        # Apply transparency threshold
        data = np.array(img)
        data[:, :, 3] = np.where(data[:, :, 3] < transparency_threshold, 0, 255)
        img = Image.fromarray(data)

        # Save
        output_path = output_dir / f"frame_{i:04d}.png"
        img.save(output_path)
        output_paths.append(output_path)

    if verbose:
        print(f"  Processed {len(output_paths)} frames")

    return output_paths


# =============================================================================
# SPRITESHEET ASSEMBLY
# =============================================================================

def assemble_spritesheet(
    frames: List[Path],
    output_path: Path,
    padding: int = 0,
) -> Tuple[Path, dict]:
    """Assemble frames into a horizontal spritesheet."""
    if not frames:
        raise ValueError("No frames to assemble")

    # Load all frames
    images = [Image.open(f) for f in frames]

    # Get dimensions (assume all frames same size)
    frame_width, frame_height = images[0].size

    # Calculate spritesheet dimensions
    sheet_width = len(images) * frame_width + (len(images) - 1) * padding
    sheet_height = frame_height

    # Create spritesheet
    spritesheet = Image.new("RGBA", (sheet_width, sheet_height), (0, 0, 0, 0))

    # Paste frames
    x_offset = 0
    for img in images:
        spritesheet.paste(img, (x_offset, 0))
        x_offset += frame_width + padding

    # Save spritesheet
    spritesheet.save(output_path)
    print(f"Saved spritesheet to {output_path}")

    # Generate metadata
    metadata = {
        "frame_width": frame_width,
        "frame_height": frame_height,
        "frame_count": len(images),
        "padding": padding,
        "total_width": sheet_width,
        "total_height": sheet_height,
    }

    return output_path, metadata


# =============================================================================
# MAIN PIPELINE
# =============================================================================

def generate_spritesheet(
    subject: str,
    animation_type: str,
    target_width: int,
    target_height: int,
    frame_count: int,
    video_duration: int,
    green_tolerance: int,
    downsample_mode: str,
    transparency_threshold: int,
    output_dir: Path,
    base_sprite: Optional[Path] = None,
    sprite_only: bool = False,
) -> Path:
    """Run the full spritesheet generation pipeline."""
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Define output paths
    base_sprite_path = output_dir / "01_base_sprite.png"
    animation_path = output_dir / "02_animation.mp4"
    frames_dir = output_dir / "03_frames"
    processed_dir = output_dir / "04_processed"
    spritesheet_path = output_dir / "spritesheet.png"
    metadata_path = output_dir / "metadata.json"

    # Step 1: Generate or reuse base sprite
    print("=" * 60)
    if base_sprite and base_sprite.exists():
        print("STEP 1: Using existing base sprite...")
        print("=" * 60)
        # Copy to output dir for consistency (unless it's the same file)
        if base_sprite.resolve() != base_sprite_path.resolve():
            shutil.copy(base_sprite, base_sprite_path)
            print(f"Copied {base_sprite} to {base_sprite_path}")
        else:
            print(f"Using {base_sprite_path}")
    else:
        print("STEP 1: Generating base sprite...")
        print("=" * 60)
        generate_base_sprite(subject, base_sprite_path, target_width, target_height)

    if sprite_only:
        print("\n" + "=" * 60)
        print("DONE (sprite only)")
        print("=" * 60)
        print(f"\nBase sprite saved to: {base_sprite_path}")
        print("\nTo animate, run:")
        print(f"  python generate_spritesheet.py --base-sprite {base_sprite_path} --animation \"{animation_type}\"")
        return base_sprite_path

    # Step 2: Generate animation video
    print("\n" + "=" * 60)
    print("STEP 2: Generating animation video...")
    print("=" * 60)
    animation_prompt = f"Animate this {target_width}x{target_height} pixel sprite doing a {animation_type}."
    generate_animation_video(
        base_sprite_path,
        animation_path,
        animation_prompt,
        duration_seconds=video_duration,
    )

    # Step 3: Extract frames
    print("\n" + "=" * 60)
    print("STEP 3: Extracting frames...")
    print("=" * 60)
    frames = extract_frames(animation_path, frames_dir, frame_count)

    # Step 4: Process frames (batch processing with unified cropping)
    print("\n" + "=" * 60)
    print("STEP 4: Processing frames...")
    print("=" * 60)
    processed_dir.mkdir(parents=True, exist_ok=True)
    processed_frames = process_frames(
        frames,
        processed_dir,
        target_width,
        target_height,
        green_tolerance,
        downsample_mode,
        transparency_threshold,
    )

    # Step 5: Assemble spritesheet
    print("\n" + "=" * 60)
    print("STEP 5: Assembling spritesheet...")
    print("=" * 60)
    spritesheet_path, metadata = assemble_spritesheet(processed_frames, spritesheet_path)

    # Add generation parameters to metadata
    metadata.update({
        "subject": subject,
        "animation_type": animation_type,
        "green_tolerance": green_tolerance,
        "downsample_mode": downsample_mode,
        "transparency_threshold": transparency_threshold,
    })

    # Save metadata
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved metadata to {metadata_path}")

    print("\n" + "=" * 60)
    print("DONE!")
    print("=" * 60)
    print(f"\nOutput files:")
    print(f"  Base sprite:  {base_sprite_path}")
    print(f"  Animation:    {animation_path}")
    print(f"  Frames:       {frames_dir}/")
    print(f"  Processed:    {processed_dir}/")
    print(f"  Spritesheet:  {spritesheet_path}")
    print(f"  Metadata:     {metadata_path}")

    return spritesheet_path


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate pixel-art spritesheets using Gemini and Veo",
    )
    parser.add_argument(
        "--subject",
        default=SUBJECT,
        help=f"Subject to generate (default: {SUBJECT})",
    )
    parser.add_argument(
        "--animation",
        default=ANIMATION_TYPE,
        help=f"Animation type (default: {ANIMATION_TYPE})",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=TARGET_WIDTH,
        help=f"Target sprite width in pixels (default: {TARGET_WIDTH})",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=TARGET_HEIGHT,
        help=f"Target sprite height in pixels (default: {TARGET_HEIGHT})",
    )
    parser.add_argument(
        "--frames",
        type=int,
        default=FRAME_COUNT,
        help=f"Number of frames to extract (default: {FRAME_COUNT})",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=VIDEO_DURATION,
        choices=[4, 5, 6, 7, 8],
        help=f"Video duration in seconds (default: {VIDEO_DURATION})",
    )
    parser.add_argument(
        "--green-tolerance",
        type=int,
        default=GREEN_TOLERANCE,
        help=f"Chroma key tolerance 0-255 (default: {GREEN_TOLERANCE})",
    )
    parser.add_argument(
        "--downsample-mode",
        choices=["mode", "average"],
        default=DOWNSAMPLE_MODE,
        help=f"Downsampling algorithm (default: {DOWNSAMPLE_MODE})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help=f"Output directory (default: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--base-sprite",
        type=Path,
        default=None,
        help="Path to existing base sprite (skip generation step)",
    )
    args = parser.parse_args()

    # Default to sprite-only when generating a new sprite (no --base-sprite)
    # This lets you review the sprite before animating
    if args.base_sprite is None:
        args.sprite_only = True
    else:
        args.sprite_only = False

    # Check for API key (accept either name)
    if not os.environ.get("GOOGLE_API_KEY") and not os.environ.get("GEMINI_API_KEY"):
        print("Error: GOOGLE_API_KEY or GEMINI_API_KEY environment variable not set")
        print("Get an API key from https://aistudio.google.com/")
        sys.exit(1)
    # google-genai uses GOOGLE_API_KEY, so copy GEMINI_API_KEY if needed
    if not os.environ.get("GOOGLE_API_KEY") and os.environ.get("GEMINI_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

    # Check for ffmpeg
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        print("Error: ffmpeg and ffprobe must be installed")
        print("Install with: sudo apt install ffmpeg")
        sys.exit(1)

    generate_spritesheet(
        subject=args.subject,
        animation_type=args.animation,
        target_width=args.width,
        target_height=args.height,
        frame_count=args.frames,
        video_duration=args.duration,
        green_tolerance=args.green_tolerance,
        downsample_mode=args.downsample_mode,
        transparency_threshold=TRANSPARENCY_THRESHOLD,
        output_dir=args.output_dir,
        base_sprite=args.base_sprite,
        sprite_only=args.sprite_only,
    )


if __name__ == "__main__":
    main()
