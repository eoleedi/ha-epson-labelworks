from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EpsonLabelWorksRuntime
from .const import DOMAIN
from .entity import EpsonLabelWorksSettingEntity


@dataclass(frozen=True)
class NumberSetting:
    key: str
    minimum: float
    maximum: float
    step: float
    unit: str | None = None
    mode: NumberMode = NumberMode.BOX


SETTINGS = (
    NumberSetting("tape_width_mm", 4, 36, 1, UnitOfLength.MILLIMETERS),
    NumberSetting("font_size", 8, 96, 1, "pt"),
    NumberSetting("density", -5, 5, 1, mode=NumberMode.SLIDER),
    NumberSetting("margin_mm", 0, 20, 0.5, UnitOfLength.MILLIMETERS),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(EpsonLabelWorksNumber(entry, runtime, setting) for setting in SETTINGS)


class EpsonLabelWorksNumber(EpsonLabelWorksSettingEntity, NumberEntity):
    def __init__(self, entry: ConfigEntry, runtime: EpsonLabelWorksRuntime, setting: NumberSetting) -> None:
        super().__init__(entry, runtime, setting.key)
        self._attr_native_min_value = setting.minimum
        self._attr_native_max_value = setting.maximum
        self._attr_native_step = setting.step
        self._attr_native_unit_of_measurement = setting.unit
        self._attr_mode = setting.mode

    @property
    def native_value(self) -> float:
        return getattr(self._runtime.settings, self._key)

    async def async_set_native_value(self, value: float) -> None:
        if self._key in {"font_size", "density"}:
            value = round(value)
        setattr(self._runtime.settings, self._key, value)
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state is not None:
            try:
                value = float(state.state)
            except ValueError:
                return
            if self.native_min_value <= value <= self.native_max_value:
                await self.async_set_native_value(value)
