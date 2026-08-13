from __future__ import annotations

import base64
import io
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont, ImageOps

from .protocol import dots_from_mm


def text_label(text: str, tape_width_mm: float, length_mm: float | None, font_size: int) -> Image.Image:
    height = dots_from_mm(tape_width_mm)
    font = _font(font_size)
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
        chars_per_line = max(1, (width - 12) // max(1, round(font_size * 0.58)))
        for part in parts:
            lines.extend(wrap(part, chars_per_line) or [""])
    image = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(image)
    line_height = font_size + 4
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


def _font(size: int) -> ImageFont.ImageFont:
    for name in ("DejaVuSans.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            pass
    return ImageFont.load_default()
