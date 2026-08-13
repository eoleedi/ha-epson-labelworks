import base64
import io

from PIL import Image

from epson_labelworks import render


def test_text_label_dimensions():
    image = render.text_label("Home Assistant", 12, 50, 28)

    assert image.size == (354, 85)


def test_text_label_detects_length_from_text():
    short = render.text_label("Hi", 12, None, 28)
    long = render.text_label("Home Assistant", 12, None, 28)

    assert short.size == (71, 85)
    assert long.width > short.width


def test_text_label_auto_length_uses_longest_line():
    multiline = render.text_label("Hi\nHome Assistant", 12, None, 28)
    longest_line = render.text_label("Home Assistant", 12, None, 28)

    assert multiline.width == longest_line.width


def test_image_label_fits_source():
    source = Image.new("L", (20, 20), 0)
    data = io.BytesIO()
    source.save(data, format="PNG")

    image = render.image_label(base64.b64encode(data.getvalue()).decode(), 12, 50)

    assert image.size == (354, 85)
    assert image.getpixel((177, 42)) == 0
