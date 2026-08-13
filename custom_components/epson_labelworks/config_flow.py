from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME

from .const import (
    CONF_SERIAL_BAUDRATE,
    CONF_SERIAL_PORT,
    CONF_TRANSPORT,
    CONF_USB_ADDRESS,
    CONF_USB_BUS,
    CONF_USB_DEVICE,
    CONF_USB_INTERFACE,
    CONF_USB_PRODUCT_ID,
    CONF_USB_SERIAL_NUMBER,
    CONF_USB_VENDOR_ID,
    DEFAULT_SERIAL_BAUDRATE,
    DEFAULT_USB_INTERFACE,
    DOMAIN,
    TRANSPORT_BLUETOOTH,
    TRANSPORT_USB,
)
from .transport import BluetoothSerialTransport, UsbDeviceInfo, UsbTransport, discover_usb_devices

_LOGGER = logging.getLogger(__name__)


class EpsonLabelWorksConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._usb_devices: dict[str, UsbDeviceInfo] = {}

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            if user_input[CONF_TRANSPORT] == TRANSPORT_USB:
                return await self.async_step_usb()
            return await self.async_step_bluetooth()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_TRANSPORT, default=TRANSPORT_USB): vol.In([TRANSPORT_USB, TRANSPORT_BLUETOOTH])}
            ),
        )

    async def async_step_usb(self, user_input=None):
        errors = {}
        if not self._usb_devices:
            try:
                devices = await self.hass.async_add_executor_job(discover_usb_devices)
                self._usb_devices = {device.selector_value: device for device in devices}
            except Exception:
                _LOGGER.exception("Failed to enumerate USB devices")
                errors["base"] = "usb_discovery_failed"
            if not self._usb_devices and not errors:
                errors["base"] = "no_usb_devices"
        if user_input is not None:
            try:
                device = self._usb_devices[user_input[CONF_USB_DEVICE]]
                data = {
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_TRANSPORT: TRANSPORT_USB,
                    CONF_USB_VENDOR_ID: device.vendor_id,
                    CONF_USB_PRODUCT_ID: device.product_id,
                    CONF_USB_INTERFACE: DEFAULT_USB_INTERFACE,
                    CONF_USB_BUS: device.bus,
                    CONF_USB_ADDRESS: device.address,
                }
                if device.serial_number:
                    data[CONF_USB_SERIAL_NUMBER] = device.serial_number
                transport = UsbTransport(
                    device.vendor_id,
                    device.product_id,
                    DEFAULT_USB_INTERFACE,
                    device.bus,
                    device.address,
                    device.serial_number,
                )
                await self.hass.async_add_executor_job(_validate_transport, transport)
            except KeyError:
                errors["base"] = "usb_device_unavailable"
            except Exception:
                _LOGGER.exception("Failed to connect to the USB printer or read its status")
                errors["base"] = "cannot_connect"
            else:
                identity = device.serial_number or f"{device.bus}-{device.address}"
                await self.async_set_unique_id(f"usb-{device.vendor_id:04x}-{device.product_id:04x}-{identity}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=data[CONF_NAME], data=data)
        return self.async_show_form(
            step_id="usb",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default="Epson LW-600P"): str,
                    vol.Required(CONF_USB_DEVICE): vol.In(
                        {value: device.label for value, device in self._usb_devices.items()}
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_bluetooth(self, user_input=None):
        errors = {}
        if user_input is not None:
            data = {**user_input, CONF_TRANSPORT: TRANSPORT_BLUETOOTH}
            try:
                await self.hass.async_add_executor_job(
                    _validate_transport,
                    BluetoothSerialTransport(data[CONF_SERIAL_PORT], data[CONF_SERIAL_BAUDRATE]),
                )
            except Exception:
                _LOGGER.exception("Failed to connect to the Bluetooth printer or read its status")
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(f"serial-{data[CONF_SERIAL_PORT]}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=data[CONF_NAME], data=data)
        return self.async_show_form(
            step_id="bluetooth",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default="Epson LW-600P"): str,
                    vol.Required(CONF_SERIAL_PORT, default="/dev/rfcomm0"): str,
                    vol.Required(CONF_SERIAL_BAUDRATE, default=DEFAULT_SERIAL_BAUDRATE): int,
                }
            ),
            errors=errors,
        )


def _validate_transport(transport) -> None:
    with transport as printer:
        printer.status()
