import socket

import pytest

from epson_labelworks import transport as transport_module
from epson_labelworks.transport import (
    BluetoothRfcommTransport,
    BluetoothSerialTransport,
    create_bluetooth_transport,
    is_bluetooth_address,
)


class FakeSocket:
    def __init__(self, recv_data=None, recv_exc=None):
        self.connected_to = None
        self.sent = b""
        self.timeouts = []
        self.closed = False
        self.recv_data = recv_data
        self.recv_exc = recv_exc

    def settimeout(self, value):
        self.timeouts.append(value)

    def connect(self, address):
        self.connected_to = address

    def sendall(self, data):
        self.sent += data

    def recv(self, size):
        if self.recv_exc is not None:
            raise self.recv_exc
        return self.recv_data

    def close(self):
        self.closed = True


@pytest.fixture
def fake_socket(monkeypatch):
    created = {}

    def factory(family, kind, proto):
        created["args"] = (family, kind, proto)
        created["socket"] = FakeSocket(recv_data=b"@ST=00")
        return created["socket"]

    monkeypatch.setattr(transport_module.socket, "AF_BLUETOOTH", 31, raising=False)
    monkeypatch.setattr(transport_module.socket, "BTPROTO_RFCOMM", 3, raising=False)
    monkeypatch.setattr(transport_module.socket, "socket", factory)
    return created


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("64:EB:8C:12:34:56", True),
        (" 64:eb:8c:12:34:56 ", True),
        ("/dev/rfcomm0", False),
        ("64:EB:8C:12:34", False),
        ("64-EB-8C-12-34-56", False),
    ],
)
def test_is_bluetooth_address(value, expected):
    assert is_bluetooth_address(value) is expected


def test_create_bluetooth_transport_selects_socket_for_address():
    transport = create_bluetooth_transport("64:eb:8c:12:34:56", 115200)

    assert isinstance(transport, BluetoothRfcommTransport)
    assert transport.address == "64:EB:8C:12:34:56"
    assert transport.channel == 1


def test_create_bluetooth_transport_keeps_serial_device_paths():
    transport = create_bluetooth_transport("/dev/rfcomm0", 115200)

    assert isinstance(transport, BluetoothSerialTransport)
    assert transport.port == "/dev/rfcomm0"


def test_rfcomm_transport_connects_writes_and_reads(fake_socket):
    transport = BluetoothRfcommTransport("64:EB:8C:12:34:56")

    with transport:
        sock = fake_socket["socket"]
        assert fake_socket["args"] == (31, socket.SOCK_STREAM, 3)
        assert sock.connected_to == ("64:EB:8C:12:34:56", 1)
        transport.write(b"abc")
        assert sock.sent == b"abc"
        assert transport.read(64, 1) == b"@ST=00"

    assert sock.closed
    assert transport.socket is None


def test_rfcomm_transport_read_timeout_returns_empty(fake_socket):
    transport = BluetoothRfcommTransport("64:EB:8C:12:34:56")
    transport.open()
    fake_socket["socket"].recv_exc = TimeoutError()

    assert transport.read(64, 0) == b""
    assert fake_socket["socket"].timeouts[-1] == 0.01


def test_rfcomm_transport_read_raises_when_printer_disconnects(fake_socket):
    transport = BluetoothRfcommTransport("64:EB:8C:12:34:56")
    transport.open()
    fake_socket["socket"].recv_data = b""

    with pytest.raises(ConnectionError):
        transport.read(64, 1)


def test_rfcomm_transport_closes_socket_when_connect_fails(monkeypatch, fake_socket):
    sockets = []

    class FailingSocket(FakeSocket):
        def connect(self, address):
            raise OSError("host is down")

    def factory(*args):
        sockets.append(FailingSocket())
        return sockets[-1]

    monkeypatch.setattr(transport_module.socket, "socket", factory)

    with pytest.raises(OSError, match="host is down"):
        BluetoothRfcommTransport("64:EB:8C:12:34:56").open()
    assert sockets[0].closed


def test_rfcomm_transport_reports_missing_bluetooth_support(monkeypatch):
    monkeypatch.delattr(transport_module.socket, "AF_BLUETOOTH", raising=False)

    with pytest.raises(RuntimeError, match="does not support Bluetooth RFCOMM"):
        BluetoothRfcommTransport("64:EB:8C:12:34:56").open()
