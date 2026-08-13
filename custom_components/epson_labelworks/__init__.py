from __future__ import annotations

import threading
from dataclasses import dataclass

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from . import protocol, render
from .const import (
    CONF_SERIAL_BAUDRATE,
    CONF_SERIAL_PORT,
    CONF_TRANSPORT,
    CONF_USB_INTERFACE,
    CONF_USB_PRODUCT_ID,
    CONF_USB_VENDOR_ID,
    DOMAIN,
    PLATFORMS,
    TRANSPORT_BLUETOOTH,
)
from .transport import BluetoothSerialTransport, PrinterTransport, UsbTransport

SERVICE_PRINT_LABEL = "print_label"
SERVICE_SCHEMA = vol.Schema(
    {
        vol.Optional("config_entry_id"): cv.string,
        vol.Optional("text"): cv.string,
        vol.Optional("image_base64"): cv.string,
        vol.Optional("tape_width_mm", default=12): vol.All(vol.Coerce(float), vol.Range(min=4, max=36)),
        vol.Optional("length_mm"): vol.All(vol.Coerce(float), vol.Range(min=10, max=500)),
        vol.Optional("font_size", default=28): vol.All(vol.Coerce(int), vol.Range(min=8, max=96)),
        vol.Optional("cut", default=protocol.CutMode.AFTER): vol.Coerce(protocol.CutMode),
        vol.Optional("density", default=0): vol.All(vol.Coerce(int), vol.Range(min=-5, max=5)),
        vol.Optional("margin_mm", default=1): vol.All(vol.Coerce(float), vol.Range(min=0, max=20)),
    }
)


@dataclass
class EpsonLabelWorksRuntime:
    name: str
    transport: PrinterTransport

    def __post_init__(self) -> None:
        self.lock = threading.Lock()
        self.last_status: protocol.Status | None = None

    def status(self) -> protocol.Status:
        with self.lock, self.transport as printer:
            self.last_status = printer.status()
            return self.last_status

    def print_label(self, data: dict) -> protocol.Status:
        text = data.get("text")
        image_base64 = data.get("image_base64")
        if bool(text) == bool(image_base64):
            raise ValueError("provide exactly one of text or image_base64")
        if text:
            image = render.text_label(text, data["tape_width_mm"], data.get("length_mm"), data["font_size"])
        else:
            if "length_mm" not in data:
                raise ValueError("length_mm is required for image labels")
            image = render.image_label(image_base64, data["tape_width_mm"], data["length_mm"])
        margin_dots = protocol.dots_from_mm(data["margin_mm"]) if data["margin_mm"] else 0
        with self.lock, self.transport as printer:
            self.last_status = printer.print_image(image, data["cut"], data["density"], margin_dots)
            return self.last_status


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})

    async def handle_print(call: ServiceCall) -> None:
        runtimes: dict[str, EpsonLabelWorksRuntime] = hass.data[DOMAIN]
        entry_id = call.data.get("config_entry_id")
        if entry_id:
            runtime = runtimes.get(entry_id)
        elif len(runtimes) == 1:
            runtime = next(iter(runtimes.values()))
        else:
            raise HomeAssistantError("config_entry_id is required when multiple printers are configured")
        if runtime is None:
            raise HomeAssistantError("Epson LabelWorks printer is not loaded")
        try:
            await hass.async_add_executor_job(runtime.print_label, dict(call.data))
        except Exception as exc:
            raise HomeAssistantError(f"Printing failed: {exc}") from exc

    if not hass.services.has_service(DOMAIN, SERVICE_PRINT_LABEL):
        hass.services.async_register(DOMAIN, SERVICE_PRINT_LABEL, handle_print, schema=SERVICE_SCHEMA)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data = entry.data
    if data[CONF_TRANSPORT] == TRANSPORT_BLUETOOTH:
        transport = BluetoothSerialTransport(data[CONF_SERIAL_PORT], data[CONF_SERIAL_BAUDRATE])
    else:
        transport = UsbTransport(data[CONF_USB_VENDOR_ID], data[CONF_USB_PRODUCT_ID], data[CONF_USB_INTERFACE])
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = EpsonLabelWorksRuntime(data[CONF_NAME], transport)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id, None)
        return True
    return False
