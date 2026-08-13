from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME

from .const import (
    CONF_SERIAL_BAUDRATE,
    CONF_SERIAL_PORT,
    CONF_TRANSPORT,
    CONF_USB_INTERFACE,
    CONF_USB_PRODUCT_ID,
    CONF_USB_VENDOR_ID,
    DEFAULT_SERIAL_BAUDRATE,
    DEFAULT_USB_INTERFACE,
    DEFAULT_USB_PRODUCT_ID,
    DEFAULT_USB_VENDOR_ID,
    DOMAIN,
    TRANSPORT_BLUETOOTH,
    TRANSPORT_USB,
)
from .transport import BluetoothSerialTransport, UsbTransport


class EpsonLabelWorksConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

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
        if user_input is not None:
            try:
                data = {
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_TRANSPORT: TRANSPORT_USB,
                    CONF_USB_VENDOR_ID: int(user_input[CONF_USB_VENDOR_ID], 0),
                    CONF_USB_PRODUCT_ID: int(user_input[CONF_USB_PRODUCT_ID], 0),
                    CONF_USB_INTERFACE: user_input[CONF_USB_INTERFACE],
                }
                transport = UsbTransport(data[CONF_USB_VENDOR_ID], data[CONF_USB_PRODUCT_ID], data[CONF_USB_INTERFACE])
                await self.hass.async_add_executor_job(_validate_transport, transport)
            except Exception:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(f"usb-{data[CONF_USB_VENDOR_ID]:04x}-{data[CONF_USB_PRODUCT_ID]:04x}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=data[CONF_NAME], data=data)
        return self.async_show_form(
            step_id="usb",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default="Epson LW-600P"): str,
                    vol.Required(CONF_USB_VENDOR_ID, default=f"0x{DEFAULT_USB_VENDOR_ID:04x}"): str,
                    vol.Required(CONF_USB_PRODUCT_ID, default=f"0x{DEFAULT_USB_PRODUCT_ID:04x}"): str,
                    vol.Required(CONF_USB_INTERFACE, default=DEFAULT_USB_INTERFACE): int,
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
