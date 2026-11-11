# /// script
# requires-python = ">=3.9"
# dependencies = ["pillow"]
# ///
"""Build the display BMPs from editable PNG sources.

Edit the PNGs in icons/70px/, icons/20px/, and art/background.png with any
image editor, then run:

    uv run tools/build_images.py

Every pixel is snapped to the nearest of the three colors the e-ink panel can
show (white, black, red); transparent pixels become white. The output is a
3x3 sprite sheet per icon size plus the full-screen background, each written
as an uncompressed 4-bit indexed BMP with a fixed palette (what
adafruit_imageload and displayio.OnDiskBitmap expect).
"""

import struct
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ICON_DIR = ROOT / "icons"
BMP_DIR = ROOT / "bmps"

# Must match ICON_MAP in code.py (OpenWeatherMap icon code prefixes).
ICON_MAP = ("01", "02", "03", "04", "09", "10", "11", "13", "50")
COLS = 3

# Palette index order: 0 = white, 1 = black, 2 = red.
PALETTE = ((255, 255, 255), (0, 0, 0), (255, 0, 0))
SIZES = (70, 20)
BG_WIDTH, BG_HEIGHT = 296, 128


def nearest(rgb):
    r, g, b = rgb
    return min(
        range(len(PALETTE)),
        key=lambda i: (r - PALETTE[i][0]) ** 2
        + (g - PALETTE[i][1]) ** 2
        + (b - PALETTE[i][2]) ** 2,
    )


def load_image(path, width, height):
    img = Image.open(path).convert("RGBA")
    if img.size != (width, height):
        sys.exit(f"{path}: expected {width}x{height}, got {img.size[0]}x{img.size[1]}")
    indices = []
    off_palette = 0
    raw = img.tobytes()
    for i in range(0, len(raw), 4):
        r, g, b, a = raw[i : i + 4]
        rgb = (255, 255, 255) if a < 128 else (r, g, b)
        if rgb not in PALETTE:
            off_palette += 1
        indices.append(nearest(rgb))
    if off_palette:
        print(f"  note: {path.name}: snapped {off_palette} off-palette pixels")
    return indices


def find_icon(size, code):
    matches = sorted((ICON_DIR / f"{size}px").glob(f"{code}*.png"))
    if len(matches) != 1:
        sys.exit(f"expected exactly one icons/{size}px/{code}*.png, found {len(matches)}")
    return matches[0]


def write_bmp(path, width, height, pixels):
    """Write a bottom-up, uncompressed 4bpp BMP with the fixed palette."""
    row_bytes = ((width * 4 + 31) // 32) * 4
    data = bytearray()
    for y in range(height - 1, -1, -1):
        row = bytearray(row_bytes)
        for x in range(width):
            v = pixels[y * width + x]
            if x % 2 == 0:
                row[x // 2] |= v << 4
            else:
                row[x // 2] |= v
        data += row
    palette = b"".join(bytes((b, g, r, 0)) for r, g, b in PALETTE)
    offset = 14 + 40 + len(palette)
    header = struct.pack(
        "<2sIHHI", b"BM", offset + len(data), 0, 0, offset
    ) + struct.pack(
        "<IiiHHIIiiII", 40, width, height, 1, 4, 0, len(data), 2835, 2835,
        len(PALETTE), len(PALETTE),
    )
    path.write_bytes(header + palette + data)


def build(size):
    rows = (len(ICON_MAP) + COLS - 1) // COLS
    width, height = size * COLS, size * rows
    sheet = [0] * (width * height)
    for n, code in enumerate(ICON_MAP):
        icon = load_image(find_icon(size, code), size, size)
        ox, oy = (n % COLS) * size, (n // COLS) * size
        for y in range(size):
            start = (oy + y) * width + ox
            sheet[start : start + size] = icon[y * size : (y + 1) * size]
    out = BMP_DIR / f"weather_icons_{size}px.bmp"
    write_bmp(out, width, height, sheet)
    print(f"wrote {out.relative_to(ROOT)} ({width}x{height})")


def build_background():
    src = ROOT / "art" / "background.png"
    out = BMP_DIR / "weather_bg.bmp"
    write_bmp(out, BG_WIDTH, BG_HEIGHT, load_image(src, BG_WIDTH, BG_HEIGHT))
    print(f"wrote {out.relative_to(ROOT)} ({BG_WIDTH}x{BG_HEIGHT})")


if __name__ == "__main__":
    for s in SIZES:
        build(s)
    build_background()
