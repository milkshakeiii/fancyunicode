#!/usr/bin/env python3
"""
Palette Suite for Spritesheet Builder

Provides color palette extraction, quantization, and unification for pixel art sprites.
Gemini's "pixel art" often has subtle color variations that this tool collapses into
clean, consistent palettes.

Usage:
    python3 palette.py extract <image> [--colors N]
    python3 palette.py quantize <image> -o <output> [--colors N]
    python3 palette.py apply <image> --palette <palette_source> -o <output>
    python3 palette.py unify <project_dir> [--colors N]
    python3 palette.py set-palette <project_dir> [--from-json|--from-image|--colors]

Requires: numpy, scikit-learn (for k-means clustering)
"""

import argparse
import json
import math
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image

try:
    from sklearn.cluster import KMeans
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


# Type alias for RGBA color tuples
Color = Tuple[int, int, int, int]

# Default sensitivity for auto-detecting optimal color count
DEFAULT_SENSITIVITY = 2.5


# =============================================================================
# CORE PALETTE FUNCTIONS
# =============================================================================

def color_distance(c1: Tuple[int, ...], c2: Tuple[int, ...]) -> float:
    """
    Euclidean distance in RGB space (ignores alpha).

    Args:
        c1: First color as (R, G, B) or (R, G, B, A)
        c2: Second color as (R, G, B) or (R, G, B, A)

    Returns:
        Euclidean distance between the two colors in RGB space
    """
    return math.sqrt(
        (c1[0] - c2[0]) ** 2 +
        (c1[1] - c2[1]) ** 2 +
        (c1[2] - c2[2]) ** 2
    )


def find_nearest_palette_color(color: Tuple[int, ...], palette: List[Color]) -> Color:
    """
    Find the closest palette color for a given color.

    Args:
        color: Input color as (R, G, B) or (R, G, B, A)
        palette: List of palette colors as (R, G, B, A) tuples

    Returns:
        The nearest palette color
    """
    if not palette:
        raise ValueError("Palette cannot be empty")

    min_dist = float('inf')
    nearest = palette[0]

    for p_color in palette:
        dist = color_distance(color, p_color)
        if dist < min_dist:
            min_dist = dist
            nearest = p_color

    return nearest


def extract_palette(img: Image.Image, max_colors: int = 8) -> List[Color]:
    """
    Extract dominant colors from an image using k-means clustering.

    Args:
        img: PIL Image to extract palette from
        max_colors: Maximum number of colors in palette (default: 8)

    Returns:
        List of (R, G, B, A) color tuples representing the palette
    """
    if not HAS_SKLEARN:
        raise ImportError(
            "scikit-learn is required for palette extraction. "
            "Install with: pip install scikit-learn"
        )

    # Convert to RGBA
    img = img.convert("RGBA")
    pixels = np.array(img)

    # Get all non-transparent pixels (alpha > 0)
    h, w, _ = pixels.shape
    flat_pixels = pixels.reshape(-1, 4)
    opaque_mask = flat_pixels[:, 3] > 0
    opaque_pixels = flat_pixels[opaque_mask]

    if len(opaque_pixels) == 0:
        return []

    # Use only RGB for clustering
    rgb_pixels = opaque_pixels[:, :3]

    # Adjust k if we have fewer unique colors than requested
    unique_colors = np.unique(rgb_pixels, axis=0)
    actual_k = min(max_colors, len(unique_colors))

    if actual_k == 0:
        return []

    # Run k-means clustering
    kmeans = KMeans(n_clusters=actual_k, random_state=42, n_init=10)
    kmeans.fit(rgb_pixels)

    # Get cluster centers as palette colors
    centers = kmeans.cluster_centers_.astype(int)

    # Convert to RGBA tuples (fully opaque)
    palette = [
        (int(c[0]), int(c[1]), int(c[2]), 255)
        for c in centers
    ]

    # Sort by luminance for consistent ordering
    palette.sort(key=lambda c: 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2])

    return palette


def detect_optimal_colors(img: Image.Image, min_k: int = 4, max_k: int = 16,
                          sensitivity: float = DEFAULT_SENSITIVITY) -> int:
    """
    Detect the optimal number of colors for an image using the elbow method.

    Runs k-means for various k values and finds the "elbow" point where
    adding more colors gives diminishing returns.

    Args:
        img: PIL Image to analyze
        min_k: Minimum number of colors to consider (default: 4)
        max_k: Maximum number of colors to consider (default: 16)
        sensitivity: Higher values bias toward more colors (default: 1.0)

    Returns:
        Optimal number of colors (k)
    """
    if not HAS_SKLEARN:
        raise ImportError(
            "scikit-learn is required for color detection. "
            "Install with: pip install scikit-learn"
        )

    # Convert to RGBA and get opaque pixels
    img = img.convert("RGBA")
    pixels = np.array(img)
    flat_pixels = pixels.reshape(-1, 4)
    opaque_mask = flat_pixels[:, 3] > 0
    opaque_pixels = flat_pixels[opaque_mask]

    if len(opaque_pixels) == 0:
        return min_k

    rgb_pixels = opaque_pixels[:, :3].astype(float)

    # Limit unique colors check
    unique_colors = np.unique(rgb_pixels, axis=0)
    max_k = min(max_k, len(unique_colors))

    if max_k <= min_k:
        return min_k

    # Sample pixels if too many (for speed)
    if len(rgb_pixels) > 10000:
        indices = np.random.choice(len(rgb_pixels), 10000, replace=False)
        rgb_pixels = rgb_pixels[indices]

    # Calculate inertia for each k
    inertias = []
    k_values = list(range(min_k, max_k + 1))

    for k in k_values:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=5, max_iter=100)
        kmeans.fit(rgb_pixels)
        inertias.append(kmeans.inertia_)

    # Find elbow using the "kneedle" algorithm (simplified)
    # Calculate the angle at each point and find max curvature
    if len(inertias) < 3:
        return min_k

    # Normalize the data for angle calculation
    x = np.array(k_values, dtype=float)
    y = np.array(inertias, dtype=float)

    # Normalize to [0, 1] range
    x_norm = (x - x.min()) / (x.max() - x.min()) if x.max() > x.min() else x
    y_norm = (y - y.min()) / (y.max() - y.min()) if y.max() > y.min() else y

    # Calculate distance from each point to line from first to last point
    # Line from (x_norm[0], y_norm[0]) to (x_norm[-1], y_norm[-1])
    p1 = np.array([x_norm[0], y_norm[0]])
    p2 = np.array([x_norm[-1], y_norm[-1]])

    distances = []
    for i in range(len(x_norm)):
        p = np.array([x_norm[i], y_norm[i]])
        # Distance from point to line
        d = np.abs(np.cross(p2 - p1, p1 - p)) / np.linalg.norm(p2 - p1)
        distances.append(d)

    # The elbow is the point with maximum distance from the line
    elbow_idx = np.argmax(distances)
    optimal_k = k_values[elbow_idx]

    # Apply sensitivity bias toward more colors
    # sensitivity > 1 shifts toward more colors
    if sensitivity > 1.0:
        # Add extra colors based on sensitivity
        bonus = int((sensitivity - 1.0) * (max_k - optimal_k) * 0.5)
        optimal_k = min(optimal_k + bonus, max_k)

    return optimal_k


def quantize_to_palette(img: Image.Image, palette: List[Color]) -> Image.Image:
    """
    Remap all pixels to the nearest palette color.

    Args:
        img: PIL Image to quantize
        palette: List of (R, G, B, A) color tuples

    Returns:
        New PIL Image with pixels quantized to palette colors
    """
    if not palette:
        raise ValueError("Palette cannot be empty")

    # Convert to RGBA
    img = img.convert("RGBA")
    pixels = np.array(img)
    h, w, _ = pixels.shape

    # Create output array
    output = np.zeros_like(pixels)

    # Convert palette to numpy array for vectorized operations
    palette_rgb = np.array([[c[0], c[1], c[2]] for c in palette])

    # Process all pixels
    flat_pixels = pixels.reshape(-1, 4)
    flat_output = output.reshape(-1, 4)

    for i, pixel in enumerate(flat_pixels):
        if pixel[3] == 0:
            # Preserve fully transparent pixels
            flat_output[i] = [0, 0, 0, 0]
        else:
            # Find nearest palette color
            rgb = pixel[:3]
            distances = np.sqrt(np.sum((palette_rgb - rgb) ** 2, axis=1))
            nearest_idx = np.argmin(distances)
            nearest_color = palette[nearest_idx]

            # Preserve original alpha, use palette RGB
            flat_output[i] = [nearest_color[0], nearest_color[1], nearest_color[2], pixel[3]]

    output = flat_output.reshape(h, w, 4)
    return Image.fromarray(output.astype(np.uint8), 'RGBA')


def count_colors(img: Image.Image) -> int:
    """Count unique colors in an image (excluding fully transparent)."""
    img = img.convert("RGBA")
    pixels = np.array(img).reshape(-1, 4)
    opaque_mask = pixels[:, 3] > 0
    opaque_pixels = pixels[opaque_mask]
    if len(opaque_pixels) == 0:
        return 0
    unique = np.unique(opaque_pixels, axis=0)
    return len(unique)


def get_color_histogram(img: Image.Image) -> List[Tuple[Color, int]]:
    """Get color histogram sorted by pixel count (descending)."""
    img = img.convert("RGBA")
    pixels = np.array(img).reshape(-1, 4)
    opaque_mask = pixels[:, 3] > 0
    opaque_pixels = pixels[opaque_mask]

    if len(opaque_pixels) == 0:
        return []

    # Count each unique color
    unique, counts = np.unique(opaque_pixels, axis=0, return_counts=True)

    # Create list of (color, count) tuples
    histogram = [
        ((int(c[0]), int(c[1]), int(c[2]), int(c[3])), int(cnt))
        for c, cnt in zip(unique, counts)
    ]

    # Sort by count descending
    histogram.sort(key=lambda x: x[1], reverse=True)

    return histogram


# =============================================================================
# PALETTE I/O
# =============================================================================

def palette_to_json(palette: List[Color]) -> List[List[int]]:
    """Convert palette to JSON-serializable format."""
    return [list(c) for c in palette]


def palette_from_json(data: List[List[int]]) -> List[Color]:
    """Convert JSON data to palette format."""
    return [tuple(c) for c in data]


def load_palette_from_file(path: Path) -> List[Color]:
    """Load palette from JSON file or extract from image."""
    if path.suffix.lower() == '.json':
        with open(path) as f:
            data = json.load(f)
        if isinstance(data, list):
            return palette_from_json(data)
        elif isinstance(data, dict) and 'palette' in data:
            return palette_from_json(data['palette'])
        else:
            raise ValueError(f"Invalid palette JSON format in {path}")
    else:
        # Assume it's an image - extract palette from it
        img = Image.open(path)
        # Use all unique colors from the image as the palette
        histogram = get_color_histogram(img)
        return [color for color, count in histogram]


def save_palette_to_json(palette: List[Color], path: Path) -> None:
    """Save palette to JSON file."""
    with open(path, 'w') as f:
        json.dump(palette_to_json(palette), f, indent=2)


def parse_hex_colors(hex_string: str) -> List[Color]:
    """Parse comma-separated hex colors into palette."""
    palette = []
    for hex_color in hex_string.split(','):
        hex_color = hex_color.strip().lstrip('#')
        if len(hex_color) == 6:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            palette.append((r, g, b, 255))
        elif len(hex_color) == 8:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            a = int(hex_color[6:8], 16)
            palette.append((r, g, b, a))
        else:
            raise ValueError(f"Invalid hex color: #{hex_color}")
    return palette


def color_to_hex(color: Color) -> str:
    """Convert RGBA color to hex string."""
    if color[3] == 255:
        return f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
    else:
        return f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}{color[3]:02x}"


# =============================================================================
# PROJECT INTEGRATION
# =============================================================================

METADATA_FILENAME = "metadata.json"


def load_project_metadata(project_dir: Path) -> dict:
    """Load metadata from project directory."""
    metadata_path = project_dir / METADATA_FILENAME
    if not metadata_path.exists():
        raise FileNotFoundError(f"No metadata.json found in {project_dir}")
    with open(metadata_path) as f:
        return json.load(f)


def save_project_metadata(project_dir: Path, metadata: dict) -> None:
    """Save metadata to project directory."""
    metadata_path = project_dir / METADATA_FILENAME
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)


def get_project_palette(project_dir: Path) -> Optional[List[Color]]:
    """Get palette from project metadata if it exists."""
    metadata = load_project_metadata(project_dir)
    if 'palette' in metadata:
        return palette_from_json(metadata['palette'])
    return None


def set_project_palette(project_dir: Path, palette: List[Color]) -> None:
    """Set palette in project metadata."""
    metadata = load_project_metadata(project_dir)
    metadata['palette'] = palette_to_json(palette)
    save_project_metadata(project_dir, metadata)
    print(f"Set palette with {len(palette)} colors in {project_dir / METADATA_FILENAME}")


def get_all_frame_paths(project_dir: Path) -> List[Path]:
    """Get all frame image paths from project."""
    metadata = load_project_metadata(project_dir)
    frames_dir = project_dir / "frames"

    paths = []
    seen = set()

    for anim_name, anim_data in metadata.get("animations", {}).items():
        for frame_info in anim_data.get("frames", []):
            extracted = frame_info.get("extracted")
            if extracted and extracted not in seen:
                seen.add(extracted)
                frame_path = frames_dir / extracted
                if frame_path.exists():
                    paths.append(frame_path)

    return paths


def unify_project_palette(project_dir: Path, max_colors: Optional[int] = None,
                          sensitivity: float = DEFAULT_SENSITIVITY) -> List[Color]:
    """
    Extract palette from base sprite and quantize all frames to it.

    Args:
        project_dir: Path to project directory
        max_colors: Maximum palette colors (None = auto-detect)
        sensitivity: Higher values bias toward more colors when auto-detecting (default: 3.0)

    Returns:
        The unified palette
    """
    frames_dir = project_dir / "frames"
    base_sprite_path = frames_dir / "idle_0.png"

    if not base_sprite_path.exists():
        raise FileNotFoundError(f"Base sprite not found: {base_sprite_path}")

    base_img = Image.open(base_sprite_path)

    # Auto-detect optimal color count if not specified
    if max_colors is None:
        print(f"Detecting optimal color count from {base_sprite_path}...")
        max_colors = detect_optimal_colors(base_img, sensitivity=sensitivity)
        print(f"Detected optimal colors: {max_colors}")

    # Extract palette from base sprite
    print(f"Extracting palette from {base_sprite_path}...")
    palette = extract_palette(base_img, max_colors)

    print(f"Palette ({len(palette)} colors):")
    for i, color in enumerate(palette):
        print(f"  {i+1}. {color_to_hex(color)} - RGB({color[0]}, {color[1]}, {color[2]})")

    # Get all frame paths
    frame_paths = get_all_frame_paths(project_dir)

    # Quantize each frame
    print(f"\nQuantizing {len(frame_paths)} frames...")
    for frame_path in frame_paths:
        img = Image.open(frame_path)
        before_colors = count_colors(img)
        quantized = quantize_to_palette(img, palette)
        after_colors = count_colors(quantized)
        quantized.save(frame_path)
        print(f"  {frame_path.name}: {before_colors} -> {after_colors} colors")

    # Save palette to metadata
    set_project_palette(project_dir, palette)

    return palette


# =============================================================================
# CLI COMMANDS
# =============================================================================

def cmd_extract(args) -> int:
    """Extract palette from an image."""
    image_path = Path(args.image)
    max_colors = args.colors

    if not image_path.exists():
        print(f"Error: Image not found: {image_path}")
        return 1

    img = Image.open(image_path)
    total_colors = count_colors(img)
    print(f"Image: {image_path}")
    print(f"Total unique colors: {total_colors}")
    print()

    # Auto-detect optimal color count if not specified
    if max_colors is None:
        print("Detecting optimal color count...")
        max_colors = detect_optimal_colors(img)
        print(f"Detected optimal colors: {max_colors}")
        print()

    palette = extract_palette(img, max_colors)

    print(f"Extracted palette ({len(palette)} colors):")
    for i, color in enumerate(palette):
        print(f"  {i+1}. {color_to_hex(color)} - RGB({color[0]}, {color[1]}, {color[2]})")

    # Show top colors by pixel count for comparison
    print()
    print("Top colors by pixel count:")
    histogram = get_color_histogram(img)[:10]
    for color, count in histogram:
        print(f"  {color_to_hex(color)}: {count} pixels")

    return 0


def cmd_quantize(args) -> int:
    """Quantize image to N colors."""
    image_path = Path(args.image)
    output_path = Path(args.output)
    max_colors = args.colors

    if not image_path.exists():
        print(f"Error: Image not found: {image_path}")
        return 1

    img = Image.open(image_path)
    before_colors = count_colors(img)

    print(f"Input: {image_path} ({before_colors} colors)")

    # Auto-detect optimal color count if not specified
    if max_colors is None:
        print("Detecting optimal color count...")
        max_colors = detect_optimal_colors(img)
        print(f"Detected optimal colors: {max_colors}")

    # Extract palette and quantize
    palette = extract_palette(img, max_colors)
    quantized = quantize_to_palette(img, palette)
    after_colors = count_colors(quantized)

    quantized.save(output_path)

    print(f"Output: {output_path} ({after_colors} colors)")
    print()
    print(f"Palette ({len(palette)} colors):")
    for i, color in enumerate(palette):
        print(f"  {i+1}. {color_to_hex(color)}")

    return 0


def cmd_apply(args) -> int:
    """Apply an existing palette to an image."""
    image_path = Path(args.image)
    palette_source = Path(args.palette)
    output_path = Path(args.output)

    if not image_path.exists():
        print(f"Error: Image not found: {image_path}")
        return 1

    if not palette_source.exists():
        print(f"Error: Palette source not found: {palette_source}")
        return 1

    # Load palette
    palette = load_palette_from_file(palette_source)
    print(f"Loaded palette with {len(palette)} colors from {palette_source}")

    # Quantize image
    img = Image.open(image_path)
    before_colors = count_colors(img)
    quantized = quantize_to_palette(img, palette)
    after_colors = count_colors(quantized)

    quantized.save(output_path)

    print(f"Input: {image_path} ({before_colors} colors)")
    print(f"Output: {output_path} ({after_colors} colors)")

    return 0


def cmd_unify(args) -> int:
    """Unify all frames in a project to a shared palette."""
    project_dir = Path(args.project_dir)
    max_colors = args.colors
    sensitivity = getattr(args, 'sensitivity', DEFAULT_SENSITIVITY)

    if not project_dir.exists():
        print(f"Error: Project directory not found: {project_dir}")
        return 1

    try:
        unify_project_palette(project_dir, max_colors, sensitivity=sensitivity)
        print("\nPalette unified successfully!")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_set_palette(args) -> int:
    """Set palette for a project from various sources."""
    project_dir = Path(args.project_dir)

    if not project_dir.exists():
        print(f"Error: Project directory not found: {project_dir}")
        return 1

    palette = None

    if args.from_json:
        json_path = Path(args.from_json)
        if not json_path.exists():
            print(f"Error: JSON file not found: {json_path}")
            return 1
        palette = load_palette_from_file(json_path)
        print(f"Loaded palette from JSON: {json_path}")

    elif args.from_image:
        image_path = Path(args.from_image)
        if not image_path.exists():
            print(f"Error: Image not found: {image_path}")
            return 1
        img = Image.open(image_path)
        max_colors = args.extract_colors or 8
        palette = extract_palette(img, max_colors)
        print(f"Extracted {len(palette)} colors from: {image_path}")

    elif args.hex_colors:
        try:
            palette = parse_hex_colors(args.hex_colors)
            print(f"Parsed {len(palette)} hex colors")
        except ValueError as e:
            print(f"Error: {e}")
            return 1

    else:
        print("Error: Must specify --from-json, --from-image, or --colors")
        return 1

    # Set the palette
    set_project_palette(project_dir, palette)

    print()
    print(f"Palette ({len(palette)} colors):")
    for i, color in enumerate(palette):
        print(f"  {i+1}. {color_to_hex(color)} - RGB({color[0]}, {color[1]}, {color[2]})")

    # Optionally apply to all frames
    if args.apply:
        print()
        print("Applying palette to all frames...")
        frame_paths = get_all_frame_paths(project_dir)
        for frame_path in frame_paths:
            img = Image.open(frame_path)
            quantized = quantize_to_palette(img, palette)
            quantized.save(frame_path)
            print(f"  Quantized: {frame_path.name}")

    return 0


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Palette tools for spritesheet builder"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # extract
    p_extract = subparsers.add_parser("extract", help="Extract palette from an image")
    p_extract.add_argument("image", help="Input image path")
    p_extract.add_argument("--colors", "-c", type=int, default=None,
                           help="Number of colors (default: auto-detect)")

    # quantize
    p_quantize = subparsers.add_parser("quantize", help="Quantize image to N colors")
    p_quantize.add_argument("image", help="Input image path")
    p_quantize.add_argument("-o", "--output", required=True, help="Output image path")
    p_quantize.add_argument("--colors", "-c", type=int, default=None,
                            help="Number of colors (default: auto-detect)")

    # apply
    p_apply = subparsers.add_parser("apply", help="Apply existing palette to image")
    p_apply.add_argument("image", help="Input image path")
    p_apply.add_argument("--palette", "-p", required=True,
                         help="Palette source (JSON file or image)")
    p_apply.add_argument("-o", "--output", required=True, help="Output image path")

    # unify
    p_unify = subparsers.add_parser("unify", help="Unify all frames to shared palette")
    p_unify.add_argument("project_dir", type=Path, help="Project directory")
    p_unify.add_argument("--colors", "-c", type=int, default=None,
                         help="Number of colors (default: auto-detect)")
    p_unify.add_argument("--sensitivity", "-s", type=float, default=DEFAULT_SENSITIVITY,
                         help=f"Sensitivity for auto-detection (higher = more colors, default: {DEFAULT_SENSITIVITY})")

    # set-palette
    p_set = subparsers.add_parser("set-palette", help="Set palette for a project")
    p_set.add_argument("project_dir", type=Path, help="Project directory")
    p_set.add_argument("--from-json", help="Load palette from JSON file")
    p_set.add_argument("--from-image", help="Extract palette from image")
    p_set.add_argument("--colors", dest="hex_colors",
                       help="Comma-separated hex colors (e.g., '#376dcd,#6e3e1a')")
    p_set.add_argument("--extract-colors", type=int, default=8,
                       help="Number of colors to extract from image (default: 8)")
    p_set.add_argument("--apply", action="store_true",
                       help="Apply palette to all existing frames")

    args = parser.parse_args()

    # Dispatch to command
    if args.command == "extract":
        sys.exit(cmd_extract(args))
    elif args.command == "quantize":
        sys.exit(cmd_quantize(args))
    elif args.command == "apply":
        sys.exit(cmd_apply(args))
    elif args.command == "unify":
        sys.exit(cmd_unify(args))
    elif args.command == "set-palette":
        sys.exit(cmd_set_palette(args))


if __name__ == "__main__":
    main()
