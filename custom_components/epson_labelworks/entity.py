from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

from . import EpsonLabelWorksRuntime
from .const import DOMAIN


class EpsonLabelWorksSettingEntity(RestoreEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, runtime: EpsonLabelWorksRuntime, key: str) -> None:
        self._runtime = runtime
        self._key = key
        self._attr_unique_id = f"{entry.entry_id}-{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=runtime.name,
            manufacturer="Epson",
            model="LabelWorks LW-600P",
        )
