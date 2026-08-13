import sys
import types

import pytest

from epson_labelworks.transport import UsbTransport, discover_usb_devices


class FakeUsbDevice:
    idVendor = 0x04B8
    idProduct = 0x0705
    bus = 1
    address = 4
    manufacturer = "EPSON"
    product = "LW-600P"
    serial_number = "ABC123"


def install_usb(monkeypatch, find):
    usb = types.ModuleType("usb")
    usb.core = types.ModuleType("usb.core")
    usb.core.find = find
    usb.util = types.ModuleType("usb.util")
    monkeypatch.setitem(sys.modules, "usb", usb)
    monkeypatch.setitem(sys.modules, "usb.core", usb.core)
    monkeypatch.setitem(sys.modules, "usb.util", usb.util)


def test_discover_usb_devices_builds_friendly_labels(monkeypatch):
    install_usb(monkeypatch, lambda **kwargs: [FakeUsbDevice()])

    devices = discover_usb_devices()

    assert len(devices) == 1
    assert devices[0].selector_value == "04b8:0705:1:4"
    assert devices[0].label == "EPSON LW-600P (04b8:0705, bus 1, address 4)"
    assert devices[0].serial_number == "ABC123"


def test_usb_transport_matches_saved_serial_number(monkeypatch):
    candidates = [FakeUsbDevice()]

    def find(**kwargs):
        assert kwargs["idVendor"] == 0x04B8
        assert kwargs["idProduct"] == 0x0705
        assert kwargs["custom_match"](candidates[0])
        return None

    install_usb(monkeypatch, find)
    transport = UsbTransport(0x04B8, 0x0705, serial_number="ABC123")

    with pytest.raises(RuntimeError, match="not found"):
        transport.open()
