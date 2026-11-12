"""Noor Four-Corner Cropper: local manual perspective correction using Pillow."""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageOps, UnidentifiedImageError

SUPPORTED = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}
MAX_PIXELS = 60_000_000
MAX_SIDE = 30_000


def _solve(matrix: list[list[float]], rhs: list[float]) -> list[float]:
    """Solve a small dense linear system with pivoted Gaussian elimination."""
    n = len(rhs)
    a = [row[:] + [rhs[i]] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[pivot][col]) < 1e-12:
            raise ValueError("Selected corners are too close together for a stable perspective transform")
        a[col], a[pivot] = a[pivot], a[col]
        scale = a[col][col]
        for j in range(col, n + 1):
            a[col][j] /= scale
        for r in range(n):
            if r == col:
                continue
            factor = a[r][col]
            for j in range(col, n + 1):
                a[r][j] -= factor * a[col][j]
    return [a[i][n] for i in range(n)]


def _cross(a, b, c):
    return (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])


def validate_corners(corners: Sequence[Sequence[float]], width: int, height: int):
    if len(corners) != 4:
        raise ValueError("Exactly four corners are required in clockwise order: top-left, top-right, bottom-right, bottom-left")
    pts = []
    for p in corners:
        if len(p) != 2:
            raise ValueError("Each corner must contain an x and y coordinate")
        x, y = float(p[0]), float(p[1])
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError("Corner coordinates must be finite numbers")
        if x < 0 or y < 0 or x > width - 1 or y > height - 1:
            raise ValueError(f"Corner ({x:g}, {y:g}) falls outside the {width}×{height} image")
        pts.append((x, y))
    crosses = [_cross(pts[i], pts[(i + 1) % 4], pts[(i + 2) % 4]) for i in range(4)]
    if any(v <= 1e-6 for v in crosses):
        raise ValueError("Corners must form a non-self-intersecting convex quadrilateral in clockwise order")
    area = abs(sum(pts[i][0] * pts[(i + 1) % 4][1] - pts[(i + 1) % 4][0] * pts[i][1] for i in range(4))) / 2
    if area < 16:
        raise ValueError("Selected region is too small; enlarge the quadrilateral")
    return pts


def output_dimensions(corners: Sequence[Sequence[float]]) -> tuple[int, int]:
    p = [(float(x), float(y)) for x, y in corners]
    dist = lambda a, b: math.hypot(b[0] - a[0], b[1] - a[1])
    width = round((dist(p[0], p[1]) + dist(p[3], p[2])) / 2)
    height = round((dist(p[0], p[3]) + dist(p[1], p[2])) / 2)
    if width < 2 or height < 2:
        raise ValueError("Selected region is too small to produce an image")
    if width > MAX_SIDE or height > MAX_SIDE or width * height > MAX_PIXELS:
        raise ValueError("Corrected image would be too large; choose a smaller source region")
    return width, height


def perspective_coefficients(corners: Sequence[Sequence[float]], output_size: tuple[int, int]):
    """Return Pillow output-to-input projective coefficients for the selected quad."""
    out_w, out_h = output_size
    if out_w < 2 or out_h < 2:
        raise ValueError("Output dimensions must each be at least 2 pixels")
    src = [(float(x), float(y)) for x, y in corners]
    dst = [(0.0, 0.0), (out_w - 1.0, 0.0), (out_w - 1.0, out_h - 1.0), (0.0, out_h - 1.0)]
    rows, rhs = [], []
    for (x, y), (u, v) in zip(dst, src):
        rows.append([x, y, 1, 0, 0, 0, -u*x, -u*y]); rhs.append(u)
        rows.append([0, 0, 0, x, y, 1, -v*x, -v*y]); rhs.append(v)
    return tuple(_solve(rows, rhs))


def warp_image(image: Image.Image, corners: Sequence[Sequence[float]], output_size=None) -> Image.Image:
    """Perspective-correct a quadrilateral; source image is not modified."""
    im = ImageOps.exif_transpose(image)
    pts = validate_corners(corners, im.width, im.height)
    size = output_size or output_dimensions(pts)
    if len(size) != 2 or any(not isinstance(n, int) or n < 2 for n in size):
        raise ValueError("Output dimensions must be two integers of at least 2 pixels")
    w, h = size
    if w > MAX_SIDE or h > MAX_SIDE or w * h > MAX_PIXELS:
        raise ValueError("Output dimensions exceed safe image limits")
    coeffs = perspective_coefficients(pts, size)
    mode = "RGBA" if "A" in im.getbands() else "RGB"
    base = im.convert(mode)
    fill = (255, 255, 255, 0) if mode == "RGBA" else (255, 255, 255)
    return base.transform(size, Image.Transform.PERSPECTIVE, coeffs,
                          resample=Image.Resampling.BICUBIC, fillcolor=fill)


def open_image(path: str | Path) -> Image.Image:
    p = Path(path)
    if p.suffix.lower() not in SUPPORTED:
        raise ValueError(f"Unsupported image format: {p.name}")
    try:
        with Image.open(p) as im:
            if im.width * im.height > MAX_PIXELS or im.width > MAX_SIDE or im.height > MAX_SIDE:
                raise ValueError("Input image is too large to process safely")
            im.load()
            return ImageOps.exif_transpose(im).copy()
    except (OSError, UnidentifiedImageError) as exc:
        raise ValueError(f"Cannot open image {p.name}: {exc}") from exc


def save_corrected(input_path, output_path, corners, output_size=None, format=None):
    source, target = Path(input_path), Path(output_path)
    if source.exists() and source.resolve() == target.resolve():
        raise ValueError("Output must be a new file; the source image will not be overwritten")
    if target.suffix.lower() not in SUPPORTED:
        raise ValueError("Choose an output filename ending in PNG, JPG, TIFF, BMP or WebP")
    image = open_image(source)
    corrected = None
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.stem + ".tmp" + target.suffix)
    try:
        corrected = warp_image(image, corners, output_size)
        fmt = format or Image.registered_extensions().get(target.suffix.lower())
        if fmt is None:
            raise ValueError("Cannot determine output image format")
        if fmt.upper() in {"JPEG", "JPG"} and corrected.mode == "RGBA":
            background = Image.new("RGB", corrected.size, "white")
            background.paste(corrected, mask=corrected.getchannel("A"))
            background.save(temporary, format="JPEG", quality=95)
            background.close()
        else:
            corrected.save(temporary, format=fmt)
        temporary.replace(target)
        return target
    finally:
        image.close()
        if corrected is not None:
            corrected.close()
        if temporary.exists():
            temporary.unlink()


def main():
    if len(sys.argv) == 1 and sys.platform == "win32":
        from noor_four_corner_cropper_gui import run_gui
        run_gui(); return
    parser = argparse.ArgumentParser(description="Manually correct a four-corner document image")
    parser.add_argument("input", help="Input image path")
    parser.add_argument("--corners", nargs=8, type=float, required=True,
                        metavar=("TLX", "TLY", "TRX", "TRY", "BRX", "BRY", "BLX", "BLY"),
                        help="Four source-image corners in clockwise order, in pixels")
    parser.add_argument("-o", "--output", required=True, help="New output image path")
    parser.add_argument("--width", type=int, help="Optional corrected output width in pixels")
    parser.add_argument("--height", type=int, help="Optional corrected output height in pixels")
    args = parser.parse_args()
    try:
        corners = list(zip(args.corners[::2], args.corners[1::2]))
        size = (args.width, args.height) if args.width is not None and args.height is not None else None
        if (args.width is None) != (args.height is None):
            raise ValueError("Specify both --width and --height, or neither")
        path = save_corrected(args.input, args.output, corners, size)
        print(f"Created: {path}")
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
