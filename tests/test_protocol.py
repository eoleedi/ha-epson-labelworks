import pytest
from PIL import Image

from epson_labelworks import protocol


def test_dots_from_mm_uses_180_dpi():
    assert protocol.dots_from_mm(25.4) == 180


def test_frame_checksum():
    assert protocol.frame(ord("D"), b"\x05") == b"\x1b{\x04D\x05I}"


def test_print_stream_contains_raster_and_form_feed():
    image = Image.new("L", (2, 8), 255)
    image.putpixel((0, 7), 0)

    stream = protocol.build_print_stream(image, protocol.CutMode.AFTER, 0, 0)

    assert protocol.raster_line_command(8) + b"\x80" in stream
    assert stream.endswith(b"\x0c" + protocol.print_end())


def test_parse_status():
    text = b"@ST=00ER=00TW=03"
    status = protocol.parse_status(text.ljust(63, b"\x00") + b"\xff")

    assert status.ready_for_print
    assert status.status == "idle"
    assert status.error == "no_error"
    assert status.tape_width_mm == 12


def test_parse_status_rejects_missing_required_fields():
    with pytest.raises(ValueError, match="ST field"):
        protocol.parse_status(b"@not-a-status".ljust(63, b"\x00") + b"\xff")


def test_parse_usb_status():
    status = protocol.parse_usb_status(bytes.fromhex("08 00 00 03 00 00 00 00"))

    assert status.ready_for_print
    assert status.status == "idle"
    assert status.tape_width_mm == 12
