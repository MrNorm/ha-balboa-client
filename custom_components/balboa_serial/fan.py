"""Support for Balboa Spa pumps."""

import math
from typing import Any, cast

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.percentage import (
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)

from . import BalboaConfigEntry
from .entity import BalboaEntity
from .pybalboa import SpaControl
from .pybalboa.enums import OffOnState, UnknownState


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BalboaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the spa's fan-like controls (pumps and blowers)."""
    spa = entry.runtime_data
    entities: list[FanEntity] = [BalboaPumpFanEntity(control) for control in spa.pumps]
    entities.extend(BalboaBlowerFanEntity(control) for control in spa.blowers)
    async_add_entities(entities)


class _ControlBackedFanEntity(BalboaEntity, FanEntity):
    """Base fan entity wrapping a multi-speed SpaControl."""

    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_OFF
        | FanEntityFeature.TURN_ON
    )

    def __init__(self, control: SpaControl) -> None:
        super().__init__(control.client, control.name)
        self._control = control
        if control.index is not None:
            self._attr_translation_placeholders = {
                "index": f"{cast(int, control.index) + 1}"
            }

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._control.set_state(OffOnState.OFF)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        if percentage is None:
            percentage = 100
        await self.async_set_percentage(percentage)

    async def async_set_percentage(self, percentage: int) -> None:
        if percentage > 0:
            state = math.ceil(
                percentage_to_ranged_value((1, self.speed_count), percentage)
            )
        else:
            state = OffOnState.OFF
        await self._control.set_state(state)

    @property
    def percentage(self) -> int | None:
        if self._control.state == UnknownState.UNKNOWN:
            return None
        if self._control.state == OffOnState.OFF:
            return 0
        return ranged_value_to_percentage((1, self.speed_count), self._control.state)

    @property
    def is_on(self) -> bool | None:
        if self._control.state == UnknownState.UNKNOWN:
            return None
        return self._control.state != OffOnState.OFF

    @property
    def speed_count(self) -> int:
        return int(max(self._control.options))


class BalboaPumpFanEntity(_ControlBackedFanEntity):
    """Representation of a Balboa Spa pump fan entity."""

    _attr_translation_key = "pump"


class BalboaBlowerFanEntity(_ControlBackedFanEntity):
    """Representation of a Balboa Spa air blower (aka bubble jets) fan entity.

    Surfaced as its own fan entity instead of hiding inside the climate
    entity's fan_mode dropdown — much more discoverable, and the right
    place to find "where do I turn the bubbles on/off in HA".
    """

    _attr_translation_key = "blower"
    _attr_icon = "mdi:chart-bubble"
