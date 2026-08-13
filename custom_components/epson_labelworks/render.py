from __future__ import annotations

import base64
import io
from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont, ImageOps

from .protocol import DPI, dots_from_mm

POINTS_PER_INCH = 72


def text_label(text: str, tape_width_mm: float, length_mm: float | None, font_size: int) -> Image.Image:
    height = dots_from_mm(tape_width_mm)
    font_size_pixels = pixels_from_points(font_size)
    font = _font(font_size_pixels)
    parts = text.splitlines() or [""]
    if length_mm is None:
        measure = ImageDraw.Draw(Image.new("L", (1, 1)))
        boxes = [measure.textbbox((0, 0), part, font=font) for part in parts]
        text_width = max(box[2] - box[0] for box in boxes)
        width = max(dots_from_mm(10), text_width + 12)
        lines = parts
    else:
        width = dots_from_mm(length_mm)
        lines = []
        chars_per_line = max(1, (width - 12) // max(1, round(font_size_pixels * 0.58)))
        for part in parts:
            lines.extend(wrap(part, chars_per_line) or [""])
    image = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(image)
    line_height = font_size_pixels + 4
    y = max(0, (height - len(lines) * line_height) // 2)
    for line in lines:
        box = draw.textbbox((0, 0), line, font=font)
        draw.text((max(0, (width - box[2] + box[0]) // 2), y), line, fill=0, font=font)
        y += line_height
    return image


def image_label(encoded: str, tape_width_mm: float, length_mm: float) -> Image.Image:
    source = Image.open(io.BytesIO(base64.b64decode(encoded, validate=True))).convert("L")
    size = (dots_from_mm(length_mm), dots_from_mm(tape_width_mm))
    fitted = ImageOps.contain(source, size)
    image = Image.new("L", size, 255)
    image.paste(fitted, ((size[0] - fitted.width) // 2, (size[1] - fitted.height) // 2))
    return image


def pixels_from_points(points: int) -> int:
    return round(points * DPI / POINTS_PER_INCH)


def _font(size: int) -> ImageFont.ImageFont:
    names = (
        "/config/fonts/NotoSansCJKtc-Regular.otf",
        "/config/fonts/NotoSansTC-Regular.ttf",
        "NotoSansCJKtc-Regular.otf",
        "NotoSansTC-Regular.ttf",
        "DejaVuSans.ttf",
        "Arial.ttf",
    )
    for name in names:
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            pass
    fonts_dir = Path("/config/fonts")
    if fonts_dir.is_dir():
        for path in (*fonts_dir.glob("*.otf"), *fonts_dir.glob("*.ttf")):
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                pass
    return ImageFont.load_default(size=size)
