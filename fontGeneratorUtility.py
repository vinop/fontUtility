import freetype
import argparse
import os

# =========================
# Utility functions
# =========================

def make_thresholds(bpp):
    levels = 1 << bpp
    step = 256 // levels
    return [step * i for i in range(1, levels)]

def gray_to_bpp(v, thresholds):
    for i, t in enumerate(thresholds):
        if v < t:
            return i
    return len(thresholds)

def pack_pixels(pixels, bpp):
    """
    Pack pixels into bytes.
    Example:
      1bpp → 8 pixels/byte
      2bpp → 4 pixels/byte
      4bpp → 2 pixels/byte
    """
    out = []
    per_byte = 8 // bpp
    mask = (1 << bpp) - 1

    for i in range(0, len(pixels), per_byte):
        b = 0
        for j in range(per_byte):
            b <<= bpp
            if i + j < len(pixels):
                b |= pixels[i + j] & mask
        out.append(b)

    return out


# =========================
# Argument parsing
# =========================

parser = argparse.ArgumentParser(description="Generate C font from TTF using FreeType")

parser.add_argument("--font", required=True, help="Path to .ttf/.otf font file")
parser.add_argument("--size", type=int, required=True, help="Font size in pixels")
parser.add_argument("--first", type=int, default=32, help="First character code")
parser.add_argument("--last", type=int, default=126, help="Last character code")
parser.add_argument("--bpp", type=int, choices=[1, 2, 4], default=2, help="Bits per pixel")
parser.add_argument("--name", default="font", help="Font symbol name")
parser.add_argument("--out", default="font", help="Output filename base")

args = parser.parse_args()

FONT_FILE   = args.font
FONT_SIZE   = args.size
FIRST_CHAR  = args.first
LAST_CHAR   = args.last
BPP         = args.bpp
FONT_NAME   = args.name
OUT_BASE    = args.out

OUT_C = OUT_BASE + ".c"
OUT_H = OUT_BASE + ".h"

THRESHOLDS = make_thresholds(BPP)

# =========================
# Load font
# =========================

face = freetype.Face(FONT_FILE)
face.set_pixel_sizes(0, FONT_SIZE)

bitmap_data = []
glyphs = []

bitmap_offset = 0
line_height = face.size.height >> 6

# =========================
# Generate glyphs
# =========================

for char_code in range(FIRST_CHAR, LAST_CHAR + 1):
    face.load_char(chr(char_code), freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL)
    g = face.glyph
    bmp = g.bitmap

    width  = bmp.width
    height = bmp.rows

    pixels = []
    for y in range(height):
        for x in range(width):
            gray = bmp.buffer[y * bmp.pitch + x]
            pixels.append(gray_to_bpp(gray, THRESHOLDS))

    packed = pack_pixels(pixels, BPP)
    bitmap_data.extend(packed)

    glyphs.append({
        "offset": bitmap_offset,
        "width": width,
        "height": height,
        "xAdvance": g.advance.x >> 6,
        "xOffset": g.bitmap_left,
        "yOffset": -(g.bitmap_top - height),
    })

    bitmap_offset += len(packed)

# =========================
# Write header (.h)
# =========================

guard = f"_{FONT_NAME.upper()}_H_"

with open(OUT_H, "w") as f:
    f.write(f"""#ifndef {guard}
#define {guard}

#include <stdint.h>

typedef struct {{
    uint16_t bitmap_offset;
    uint8_t  width;
    uint8_t  height;
    int8_t   xAdvance;
    int8_t   xOffset;
    int8_t   yOffset;
}} font_glyph_t;

typedef struct {{
    const uint8_t      *bitmap;
    const font_glyph_t *glyphs;
    uint8_t first_char;
    uint8_t last_char;
    uint8_t line_height;
    uint8_t bpp;
    uint8_t fixed_width;
}} font_t;

extern const font_t {FONT_NAME};

#endif
""")

# =========================
# Write source (.c)
# =========================

with open(OUT_C, "w") as f:
    f.write(f'#include "{OUT_H}"\n\n')

    f.write(f"static const uint8_t {FONT_NAME}_Bitmap[] = {{\n")
    for i, b in enumerate(bitmap_data):
        f.write(f"0x{b:02X}, ")
        if (i + 1) % 16 == 0:
            f.write("\n")
    f.write("\n};\n\n")

    f.write(f"static const font_glyph_t {FONT_NAME}_Glyphs[] = {{\n")
    for g in glyphs:
        f.write(
            f"  {{ {g['offset']}, {g['width']}, {g['height']}, "
            f"{g['xAdvance']}, {g['xOffset']}, {g['yOffset']} }},\n"
        )
    f.write("};\n\n")

    f.write(f"""const font_t {FONT_NAME} = {{
    .bitmap       = {FONT_NAME}_Bitmap,
    .glyphs       = {FONT_NAME}_Glyphs,
    .first_char   = {FIRST_CHAR},
    .last_char    = {LAST_CHAR},
    .line_height  = {line_height},
    .bpp          = {BPP},
    .fixed_width  = 0
}};
""")

print("Font generation complete.")
print(f"Generated: {OUT_C}, {OUT_H}")
