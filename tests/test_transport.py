import pytest

from epson_labelworks import protocol
from epson_labelworks.transport import PrinterTransport


class Image:
    size = (1, 8)

    def convert(self, mode):
        return self

    def load(self):
        return {(0, y): 255 for y in range(8)}


class FakeTransport(PrinterTransport):
    def __init__(self, statuses=None):
        self.writes = []
        self.statuses = list(statuses or [0x00])

    def open(self):
        pass

    def close(self):
        pass

    def write(self, data):
        self.writes.append(data)

    def read(self, size, timeout_s):
        status = self.statuses.pop(0)
        return f"@ST={status:02X}ER=00TW=03".encode().ljust(63, b"\x00") + b"\xff"


def test_wait_until_ready_requests_status():
    transport = FakeTransport()

    status = transport.wait_until_ready()

    assert transport.writes == [protocol.request_status()]
    assert status.ready_for_print


def test_print_image_resets_status_mode_after_print(monkeypatch):
    transport = FakeTransport([0x00, 0x05])
    monkeypatch.setattr("epson_labelworks.transport.time.sleep", lambda _: None)

    status = transport.print_image(Image(), protocol.CutMode.AFTER, 0, 0)

    assert transport.writes[-1] == protocol.reset_status_request()
    assert status.ready_for_print
    assert transport.writes[-3:-1] == [protocol.request_status(), protocol.request_status()]


def test_status_uses_status_request():
    transport = FakeTransport()

    transport.status()

    assert transport.writes == [protocol.request_status()]


def test_wait_until_ready_raises_when_last_status_is_busy(monkeypatch):
    transport = FakeTransport()
    busy = protocol.parse_status(b"@ST=02ER=00TW=03".ljust(63, b"\x00") + b"\xff")
    monkeypatch.setattr(transport, "_query_status", lambda timeout_s: busy)
    times = iter([0, 0, 0, 2])
    monkeypatch.setattr("epson_labelworks.transport.time.monotonic", lambda: next(times))

    with pytest.raises(TimeoutError):
        transport.wait_until_ready(timeout_s=1)
