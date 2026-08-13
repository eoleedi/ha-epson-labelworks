from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EpsonLabelWorksRuntime
from .const import DOMAIN
from .entity import EpsonLabelWorksSettingEntity
from .protocol import CutMode


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([EpsonLabelWorksCutMode(entry, hass.data[DOMAIN][entry.entry_id])])


class EpsonLabelWorksCutMode(EpsonLabelWorksSettingEntity, SelectEntity):
    _attr_options = [mode.value for mode in CutMode]

    def __init__(self, entry: ConfigEntry, runtime: EpsonLabelWorksRuntime) -> None:
        super().__init__(entry, runtime, "cut_mode")

    @property
    def current_option(self) -> str:
        return self._runtime.settings.cut.value

    async def async_select_option(self, option: str) -> None:
        self._runtime.settings.cut = CutMode(option)
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state is not None and state.state in self.options:
            await self.async_select_option(state.state)
