from __future__ import annotations

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EpsonLabelWorksRuntime
from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([EpsonLabelTextEntity(entry, hass.data[DOMAIN][entry.entry_id])])


class EpsonLabelTextEntity(TextEntity):
    _attr_icon = "mdi:label"
    _attr_native_min = 0
    _attr_native_max = 255
    _attr_mode = "text"

    def __init__(self, entry: ConfigEntry, runtime: EpsonLabelWorksRuntime) -> None:
        self._entry = entry
        self._runtime = runtime
        self._attr_unique_id = f"{entry.entry_id}-print"
        self._attr_name = "Print label"
        self._attr_native_value = ""
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=runtime.name,
            manufacturer="Epson",
            model="LabelWorks LW-600P",
        )

    @property
    def extra_state_attributes(self):
        status = self._runtime.last_status
        if status is None:
            return None
        return {
            "printer_status": status.status,
            "printer_error": status.error,
            "tape_width_mm": status.tape_width_mm,
        }

    async def async_set_value(self, value: str) -> None:
        if not value:
            return
        data = self._runtime.settings.text_print_data(value)
        await self.hass.async_add_executor_job(self._runtime.print_label, data)
        self._attr_native_value = ""
        self.async_write_ha_state()
