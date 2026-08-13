from epson_labelworks import protocol
from epson_labelworks.transport import PrinterTransport


class Image:
    size = (1, 8)

    def convert(self, mode):
        return self

    def load(self):
        return {(0, y): 255 for y in range(8)}


class FakeTransport(PrinterTransport):
    def __init__(self):
        self.writes = []

    def open(self):
        pass

    def close(self):
        pass

    def write(self, data):
        self.writes.append(data)

    def read(self, size, timeout_s):
        return b"@ST=00ER=00TW=03".ljust(63, b"\x00") + b"\xff"


def test_wait_until_ready_requests_status():
    transport = FakeTransport()

    status = transport.wait_until_ready()

    assert transport.writes == [protocol.request_status()]
    assert status.ready_for_print


def test_print_image_resets_status_mode_after_print(monkeypatch):
    transport = FakeTransport()
    monkeypatch.setattr("epson_labelworks.transport.time.sleep", lambda _: None)

    status = transport.print_image(Image(), protocol.CutMode.AFTER, 0, 0)

    assert transport.writes[-1] == protocol.reset_status_request()
    assert status.ready_for_print
