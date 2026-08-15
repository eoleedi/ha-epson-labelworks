from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

ESC = 0x1B
FRAME_END = 0x7D
FORM_FEED = 0x0C
DPI = 180
STATUS_FRAME_LENGTH = 64
BLACK_THRESHOLD = 140

TAPE_WIDTHS_MM = {
    0x01: 6,
    0x02: 9,
    0x03: 12,
    0x04: 18,
    0x05: 24,
    0x06: 36,
    0x51: 6,
    0x52: 9,
    0x53: 12,
    0x54: 18,
    0x55: 24,
    0x56: 36,
}


class CutMode(StrEnum):
    EACH = "each"
    AFTER = "after"
    NONE = "none"


@dataclass(frozen=True)
class Status:
    raw_text: str
    status_code: int
    status: str
    error_code: int
    error: str
    tape_width_mm: int | None

    @property
    def ready_for_print(self) -> bool:
        return self.error_code == 0 and self.status_code in {0x00, 0x04, 0x05}


def dots_from_mm(mm: float) -> int:
    if mm <= 0:
        raise ValueError("millimeters must be positive")
    return round(mm * DPI / 25.4)


def frame(subcommand: int, payload: bytes = b"") -> bytes:
    if len(payload) > 252:
        raise ValueError("payload too large for Epson frame")
    length = len(payload) + 3
    checksum = (subcommand + sum(payload)) & 0xFF
    return bytes([ESC, 0x7B, length, subcommand]) + payload + bytes([checksum, FRAME_END])


def request_status() -> bytes:
    return bytes([ESC, 0x7B, 0x05, ord("Q"), 0x05, 0x00, 0x56, FRAME_END])


def reset_status_request() -> bytes:
    return bytes([ESC, 0x7B, 0x05, ord("Q"), 0x00, 0x00, 0x51, FRAME_END])


def reset_printer() -> bytes:
    return bytes([ESC, 0x7B, 0x03, ord("!"), ord("!"), FRAME_END])


def print_end() -> bytes:
    return bytes([ESC, 0x7B, 0x03, ord("@"), ord("@"), FRAME_END])


def job_environment(cut: CutMode = CutMode.AFTER, density: int = 0) -> bytes:
    if density < -5 or density > 5:
        raise ValueError("density must be between -5 and 5")
    cut_word = {
        CutMode.EACH: 0x01010101,
        CutMode.AFTER: 0x01010001,
        CutMode.NONE: 0,
    }[cut]
    return b"".join(
        [
            print_end(),
            frame(ord("{"), b"\x00\x00ST"),
            frame(ord("C"), cut_word.to_bytes(4, "little")),
            frame(ord("D"), bytes([density + 5])),
            frame(ord("G")),
        ]
    )


def raster_line_command(width_dots: int) -> bytes:
    return bytes([ESC, ord("."), 0, 0, 0, 1, width_dots & 0xFF, width_dots >> 8])


def raster_page(image, margin_dots: int = 0) -> bytes:
    gray = image.convert("L")
    width, height = gray.size
    if width <= 0 or height <= 0:
        raise ValueError("image must have positive dimensions")
    line = raster_line_command(height)
    row_size = (height + 7) // 8
    blank = bytes(row_size)
    pixels = gray.load()
    chunks: list[bytes] = []
    for x in range(-margin_dots, width + margin_dots):
        row = bytearray(row_size)
        if 0 <= x < width:
            for y in range(height - 1, -1, -1):
                if pixels[x, y] < BLACK_THRESHOLD:
                    dy = height - 1 - y
                    row[dy // 8] |= 0x80 >> (dy % 8)
        chunks.extend((line, bytes(row) if 0 <= x < width else blank))
    return b"".join(chunks)


def build_print_stream(image, cut: CutMode, density: int, margin_dots: int) -> bytes:
    width, _ = image.size
    return b"".join(
        [
            request_status(),
            job_environment(cut, density),
            request_status(),
            frame(ord("L"), (width + margin_dots * 2).to_bytes(4, "little")),
            frame(ord("T"), margin_dots.to_bytes(2, "little")),
            raster_page(image, margin_dots),
            bytes([FORM_FEED]),
            print_end(),
        ]
    )


def find_status_frame(data: bytes) -> bytes | None:
    for offset in range(max(0, len(data) - STATUS_FRAME_LENGTH), -1, -1):
        candidate = data[offset : offset + STATUS_FRAME_LENGTH]
        if len(candidate) == STATUS_FRAME_LENGTH and candidate[0] == ord("@") and candidate[-1] == 0xFF:
            return candidate
    return None


def parse_status(data: bytes) -> Status:
    if len(data) != STATUS_FRAME_LENGTH or data[0] != ord("@") or data[-1] != 0xFF:
        raise ValueError("invalid Epson status frame")
    text = data[:-1].rstrip(b"\x00").decode("ascii", errors="replace")

    def code(key: str) -> int:
        index = text.rfind(key)
        if index < 0 or index + 5 > len(text) or text[index + 2] not in {":", "="}:
            raise ValueError(f"missing or invalid {key} field in Epson status frame")
        try:
            return int(text[index + 3 : index + 5], 16)
        except ValueError as exc:
            raise ValueError(f"missing or invalid {key} field in Epson status frame") from exc

    status_code = code("ST")
    error_code = code("ER")
    return Status(
        raw_text=text,
        status_code=status_code,
        status={0: "idle", 1: "feeding", 2: "printing", 3: "data_sending", 4: "feed_end", 5: "print_end"}.get(status_code, "unknown"),
        error_code=error_code,
        error={0: "no_error", 1: "cutter_error", 6: "no_tape_cartridge", 0x15: "head_overheated", 0x21: "cover_open", 0x42: "tape_end"}.get(error_code, "unknown"),
        tape_width_mm=TAPE_WIDTHS_MM.get(code("TW")),
    )


def parse_usb_status(data: bytes) -> Status:
    if len(data) < 4 or data[0] != 0x08:
        raise ValueError("invalid Epson USB status response")
    activity = data[1]
    status_code = 0x00 if activity == 0 else 0x02
    return Status(
        raw_text=data.hex(" "),
        status_code=status_code,
        status="idle" if activity == 0 else "printing",
        error_code=0,
        error="no_error",
        tape_width_mm=TAPE_WIDTHS_MM.get(data[3]),
    )


def stream_chunks(stream: bytes, size: int = 4096) -> Iterable[bytes]:
    for offset in range(0, len(stream), size):
        yield stream[offset : offset + size]
