#!/usr/bin/env python3
"""
Pixel Grid Detector

Analyzes Gemini's "almost pixel art" to detect the underlying grid structure
and optionally overlay a grid visualization.

The goal is to find where Gemini intended pixel boundaries to be, so we can
convert the soft/anti-aliased output into clean pixel art.
"""

import argparse
from pathlib import Path
from typing import Tuple, List, Optional

import numpy as np
from PIL import Image, ImageDraw


def detect_grid_size(img: Image.Image, max_cell_size: int = 100) -> Tuple[int, int]:
    """
    Detect the likely pixel grid cell size in the image.

    Looks for repeating patterns of color transitions that suggest
    pixel boundaries.

    Returns (cell_width, cell_height) in pixels.
    """
    arr = np.array(img.convert("RGB"))
    height, width = arr.shape[:2]

    # Compute horizontal color differences
    h_diff = np.abs(np.diff(arr.astype(float), axis=1)).sum(axis=2)
    # Compute vertical color differences
    v_diff = np.abs(np.diff(arr.astype(float), axis=0)).sum(axis=2)

    # Sum differences along each row/column to find periodic peaks
    h_sums = h_diff.sum(axis=0)  # Sum along columns -> array of width-1
    v_sums = v_diff.sum(axis=1)  # Sum along rows -> array of height-1

    # Find periodicity using autocorrelation
    def find_period(signal: np.ndarray, max_period: int) -> int:
        """Find the dominant period in a 1D signal."""
        # Normalize
        signal = signal - signal.mean()
        if signal.std() == 0:
            return 1
        signal = signal / signal.std()

        # Autocorrelation for different lags
        correlations = []
        for lag in range(1, min(max_period, len(signal) // 2)):
            corr = np.correlate(signal[:-lag], signal[lag:])[0]
            correlations.append((lag, corr / len(signal[:-lag])))

        if not correlations:
            return 1

        # Find peaks in correlation
        best_lag = max(correlations, key=lambda x: x[1])[0]
        return best_lag

    cell_width = find_period(h_sums, max_cell_size)
    cell_height = find_period(v_sums, max_cell_size)

    return cell_width, cell_height


def draw_grid_overlay(
    img: Image.Image,
    cell_width: int,
    cell_height: int,
    offset_x: int = 0,
    offset_y: int = 0,
    color: Tuple[int, int, int, int] = (255, 0, 0, 128),
) -> Image.Image:
    """
    Draw a grid overlay on the image.

    Args:
        img: Input image
        cell_width: Width of each grid cell
        cell_height: Height of each grid cell
        offset_x: X offset for grid alignment
        offset_y: Y offset for grid alignment
        color: RGBA color for grid lines

    Returns:
        New image with grid overlay
    """
    # Convert to RGBA if needed
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    # Create overlay
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    width, height = img.size

    # Draw vertical lines
    x = offset_x
    while x < width:
        draw.line([(x, 0), (x, height)], fill=color, width=1)
        x += cell_width

    # Draw horizontal lines
    y = offset_y
    while y < height:
        draw.line([(0, y), (width, y)], fill=color, width=1)
        y += cell_height

    # Composite
    result = Image.alpha_composite(img, overlay)
    return result


def find_best_offset(
    img: Image.Image,
    cell_width: int,
    cell_height: int,
    search_range: Optional[int] = None,
) -> Tuple[int, int]:
    """
    Find the best grid offset that aligns with color transitions.

    Returns (offset_x, offset_y).
    """
    if search_range is None:
        search_range = max(cell_width, cell_height)

    arr = np.array(img.convert("RGB"))
    height, width = arr.shape[:2]

    best_score = -1
    best_offset = (0, 0)

    # Try different offsets
    for ox in range(min(search_range, cell_width)):
        for oy in range(min(search_range, cell_height)):
            score = 0

            # Score vertical lines (check horizontal color diff at grid lines)
            for x in range(ox, width - 1, cell_width):
                diff = np.abs(arr[:, x].astype(float) - arr[:, x + 1].astype(float)).sum()
                score += diff

            # Score horizontal lines
            for y in range(oy, height - 1, cell_height):
                diff = np.abs(arr[y, :].astype(float) - arr[y + 1, :].astype(float)).sum()
                score += diff

            if score > best_score:
                best_score = score
                best_offset = (ox, oy)

    return best_offset


def find_edge_lines(
    img: Image.Image,
    min_cell_size: int = 3,
    threshold_percentile: float = 70,
) -> Tuple[List[int], List[int]]:
    """
    Find grid lines by detecting all high-contrast edges.

    Args:
        img: Input image
        min_cell_size: Minimum distance between lines
        threshold_percentile: Only keep edges above this percentile of contrast

    Returns:
        (x_lines, y_lines) - lists of x and y coordinates for grid lines
    """
    arr = np.array(img.convert("RGB")).astype(float)
    height, width = arr.shape[:2]

    # Compute difference signals (sum of color change along each row/column)
    h_diff = np.abs(np.diff(arr, axis=1)).sum(axis=2)  # shape: (height, width-1)
    v_diff = np.abs(np.diff(arr, axis=0)).sum(axis=2)  # shape: (height-1, width)

    # Sum along the perpendicular axis to get 1D signals
    h_signal = h_diff.sum(axis=0)  # contrast at each x position
    v_signal = v_diff.sum(axis=1)  # contrast at each y position

    def find_peaks(signal: np.ndarray, min_gap: int, threshold_pct: float) -> List[int]:
        """Find local maxima above threshold."""
        threshold = np.percentile(signal, threshold_pct)

        peaks = []
        for i in range(1, len(signal) - 1):
            # Local maximum and above threshold
            if signal[i] > signal[i-1] and signal[i] > signal[i+1] and signal[i] > threshold:
                peaks.append((i, signal[i]))

        if not peaks:
            return []

        # Remove peaks too close together (keep the stronger one)
        filtered = [peaks[0]]
        for pos, strength in peaks[1:]:
            if pos - filtered[-1][0] >= min_gap:
                filtered.append((pos, strength))
            elif strength > filtered[-1][1]:
                filtered[-1] = (pos, strength)

        # Remove interior peaks that are weaker than both neighbors
        # (these are likely false edges through the middle of a pixel)
        if len(filtered) >= 3:
            final = [filtered[0]]
            for i in range(1, len(filtered) - 1):
                prev_strength = filtered[i-1][1]
                curr_strength = filtered[i][1]
                next_strength = filtered[i+1][1]

                # Keep if it's at least 20% as strong as the weaker neighbor
                min_neighbor = min(prev_strength, next_strength)
                if curr_strength >= min_neighbor * 0.2:
                    final.append(filtered[i])
            final.append(filtered[-1])
            filtered = final

        return [p[0] for p in filtered]

    x_lines = find_peaks(h_signal, min_cell_size, threshold_percentile)
    y_lines = find_peaks(v_signal, min_cell_size, threshold_percentile)

    # Add edges
    if not x_lines or x_lines[0] > min_cell_size:
        x_lines = [0] + x_lines
    if not x_lines or x_lines[-1] < width - min_cell_size:
        x_lines = x_lines + [width - 1]
    if not y_lines or y_lines[0] > min_cell_size:
        y_lines = [0] + y_lines
    if not y_lines or y_lines[-1] < height - min_cell_size:
        y_lines = y_lines + [height - 1]

    return x_lines, y_lines


def refine_grid_lines(
    img: Image.Image,
    cell_width: int,
    cell_height: int,
    offset_x: int,
    offset_y: int,
    search_radius: int = None,
) -> Tuple[List[int], List[int]]:
    """
    Refine grid lines by adjusting each line independently to maximize
    alignment with color transitions.

    Args:
        img: Input image
        cell_width: Initial cell width
        cell_height: Initial cell height
        offset_x: Initial X offset
        offset_y: Initial Y offset
        search_radius: How far each line can move (default: cell_size // 3)

    Returns:
        (x_lines, y_lines) - lists of x and y coordinates for grid lines
    """
    # Use edge-based detection instead of refining a regular grid
    return find_edge_lines(img, min_cell_size=min(cell_width, cell_height) // 2)


def draw_adaptive_grid(
    img: Image.Image,
    x_lines: List[int],
    y_lines: List[int],
    color: Tuple[int, int, int, int] = (255, 0, 0, 128),
) -> Image.Image:
    """
    Draw grid with individually positioned lines.

    Args:
        img: Input image
        x_lines: List of x coordinates for vertical lines
        y_lines: List of y coordinates for horizontal lines
        color: RGBA color for grid lines

    Returns:
        New image with grid overlay
    """
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    width, height = img.size

    # Draw vertical lines
    for x in x_lines:
        draw.line([(x, 0), (x, height)], fill=color, width=1)

    # Draw horizontal lines
    for y in y_lines:
        draw.line([(0, y), (width, y)], fill=color, width=1)

    result = Image.alpha_composite(img, overlay)
    return result


def extract_pixels(
    img: Image.Image,
    x_lines: List[int],
    y_lines: List[int],
    green_tolerance: int = 50,
    mode: str = "mode",
    remove_green: bool = True,
) -> Tuple[Image.Image, Tuple[int, int, int, int]]:
    """
    Convert grid cells to actual pixels, removing green background cells.

    Args:
        img: Input image
        x_lines: X coordinates of vertical grid lines
        y_lines: Y coordinates of horizontal grid lines
        green_tolerance: Tolerance for detecting green background
        mode: "mode" (most frequent color) or "average"

    Returns:
        (pixel_image, bbox) where:
        - pixel_image: RGBA image with one pixel per grid cell
        - bbox: (x, y, width, height) position in grid coordinates
    """
    arr = np.array(img.convert("RGBA"))

    # Grid dimensions
    cols = len(x_lines) - 1
    rows = len(y_lines) - 1

    if cols <= 0 or rows <= 0:
        raise ValueError("Need at least 2 lines in each direction")

    # Create output array
    pixels = np.zeros((rows, cols, 4), dtype=np.uint8)

    # Track which cells have content (non-green)
    has_content = np.zeros((rows, cols), dtype=bool)

    green = np.array([0, 255, 0])

    for row in range(rows):
        y1 = y_lines[row]
        y2 = y_lines[row + 1]

        for col in range(cols):
            x1 = x_lines[col]
            x2 = x_lines[col + 1]

            # Get center pixel of this cell
            center_y = (y1 + y2) // 2
            center_x = (x1 + x2) // 2

            if center_y >= arr.shape[0] or center_x >= arr.shape[1]:
                continue

            pixel_color = arr[center_y, center_x]

            if remove_green:
                # Check if it's green (background)
                # More lenient: green is dominant channel and reasonably bright
                r, g, b = int(pixel_color[0]), int(pixel_color[1]), int(pixel_color[2])
                is_green = (
                    g > r + 30 and  # G significantly higher than R
                    g > b + 30 and  # G significantly higher than B
                    g > 100         # G is reasonably bright
                )

                if is_green:
                    pixels[row, col] = [0, 0, 0, 0]  # Transparent
                else:
                    pixels[row, col] = pixel_color
                    pixels[row, col, 3] = 255  # Fully opaque
                    has_content[row, col] = True
            else:
                # Keep all colors as-is
                pixels[row, col] = pixel_color
                pixels[row, col, 3] = 255
                has_content[row, col] = True

    # Find bounding box of content
    content_rows = np.any(has_content, axis=1)
    content_cols = np.any(has_content, axis=0)

    if not np.any(content_rows) or not np.any(content_cols):
        # No content found
        return Image.fromarray(pixels), (0, 0, cols, rows)

    row_min = np.argmax(content_rows)
    row_max = rows - np.argmax(content_rows[::-1])
    col_min = np.argmax(content_cols)
    col_max = cols - np.argmax(content_cols[::-1])

    # Return full image and bbox in grid coordinates
    pixel_img = Image.fromarray(pixels)
    bbox = (col_min, row_min, col_max - col_min, row_max - row_min)

    return pixel_img, bbox


def crop_to_content(
    pixel_img: Image.Image,
    bbox: Tuple[int, int, int, int],
) -> Image.Image:
    """
    Crop pixel image to its content bounding box.

    Args:
        pixel_img: Full pixel image
        bbox: (x, y, width, height) in pixel coordinates

    Returns:
        Cropped image
    """
    x, y, w, h = bbox
    return pixel_img.crop((x, y, x + w, y + h))


def main():
    parser = argparse.ArgumentParser(description="Detect and visualize pixel grid in images")
    parser.add_argument("image", help="Path to input image")
    parser.add_argument("-o", "--output", help="Output path (default: adds _grid suffix)")
    parser.add_argument("--cell-width", type=int, help="Override detected cell width")
    parser.add_argument("--cell-height", type=int, help="Override detected cell height")
    parser.add_argument("--offset-x", type=int, help="Override detected X offset")
    parser.add_argument("--offset-y", type=int, help="Override detected Y offset")
    parser.add_argument("--no-refine", action="store_true", help="Skip adaptive line refinement")
    parser.add_argument("--extract", action="store_true", help="Extract pixels from grid cells")
    parser.add_argument("--keep-green", action="store_true", help="Don't convert green to transparent")
    parser.add_argument("--color", default="red", help="Grid line color (default: red)")
    args = parser.parse_args()

    img_path = Path(args.image)
    img = Image.open(img_path)

    print(f"Image size: {img.size}")

    # Detect or use provided cell size
    if args.cell_width and args.cell_height:
        cell_width, cell_height = args.cell_width, args.cell_height
        print(f"Using provided cell size: {cell_width}x{cell_height}")
    else:
        cell_width, cell_height = detect_grid_size(img)
        print(f"Detected cell size: {cell_width}x{cell_height}")

    # Find or use provided offset
    if args.offset_x is not None and args.offset_y is not None:
        offset_x, offset_y = args.offset_x, args.offset_y
        print(f"Using provided offset: ({offset_x}, {offset_y})")
    else:
        offset_x, offset_y = find_best_offset(img, cell_width, cell_height)
        print(f"Detected offset: ({offset_x}, {offset_y})")

    # Parse color
    color_map = {
        "red": (255, 0, 0, 128),
        "green": (0, 255, 0, 128),
        "blue": (0, 0, 255, 128),
        "white": (255, 255, 255, 128),
        "black": (0, 0, 0, 128),
    }
    color = color_map.get(args.color, (255, 0, 0, 128))

    # Get grid lines
    if args.no_refine:
        # Regular grid
        width, height = img.size
        x_lines = list(range(offset_x, width + 1, cell_width))
        y_lines = list(range(offset_y, height + 1, cell_height))
        print(f"Regular grid: {len(x_lines)} x {len(y_lines)} lines")
    else:
        print("Refining grid lines...")
        x_lines, y_lines = refine_grid_lines(img, cell_width, cell_height, offset_x, offset_y)
        print(f"Refined: {len(x_lines)} vertical lines, {len(y_lines)} horizontal lines")

    grid_cols = len(x_lines) - 1
    grid_rows = len(y_lines) - 1

    if args.extract:
        # Extract pixels from grid
        print("Extracting pixels...")
        pixel_img, bbox = extract_pixels(img, x_lines, y_lines, remove_green=not args.keep_green)
        print(f"Full grid: {pixel_img.size[0]}x{pixel_img.size[1]} pixels")
        print(f"Content bbox: x={bbox[0]}, y={bbox[1]}, w={bbox[2]}, h={bbox[3]}")

        # Save full pixel image
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = img_path.parent / f"{img_path.stem}_pixels.png"

        pixel_img.save(output_path)
        print(f"Saved: {output_path}")

        # Also save cropped version
        cropped = crop_to_content(pixel_img, bbox)
        cropped_path = output_path.parent / f"{output_path.stem}_cropped.png"
        cropped.save(cropped_path)
        print(f"Saved cropped: {cropped_path} ({cropped.size[0]}x{cropped.size[1]})")
    else:
        # Draw grid overlay
        result = draw_adaptive_grid(img, x_lines, y_lines, color)

        if args.output:
            output_path = Path(args.output)
        else:
            output_path = img_path.parent / f"{img_path.stem}_grid{img_path.suffix}"

        result.save(output_path)
        print(f"Saved: {output_path}")
        print(f"Grid dimensions: ~{grid_cols}x{grid_rows} cells")


if __name__ == "__main__":
    main()
