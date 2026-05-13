"""Support for Balboa switches."""

from __future__ import annotations

from typing import Any, cast

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BalboaConfigEntry
from .entity import BalboaEntity
from .pybalboa import SpaClient, SpaControl
from .pybalboa.enums import (
    MessageType,
    OffOnState,
    SpaState,
    ToggleItemCode,
    UnknownState,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BalboaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the spa's switches."""
    spa = entry.runtime_data
    entities: list[SwitchEntity] = [
        FilterCycle2EnabledSwitch(spa),
        TwentyFourHourClockSwitch(spa),
        HoldModeSwitch(spa),
    ]
    entities.extend(AuxSwitchEntity(control) for control in spa.aux)
    entities.extend(MisterSwitchEntity(control) for control in spa.misters)
    async_add_entities(entities)


class FilterCycle2EnabledSwitch(BalboaEntity, SwitchEntity):
    """Whether filter cycle 2 is enabled."""

    def __init__(self, spa: SpaClient) -> None:
        super().__init__(spa, "filter_cycle_2_enabled")
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_translation_key = "filter_cycle_2_enabled"

    @property
    def is_on(self) -> bool:
        return self._client.filter_cycle_2_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._client.configure_filter_cycle(2, enabled=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._client.configure_filter_cycle(2, enabled=False)


class TwentyFourHourClockSwitch(BalboaEntity, SwitchEntity):
    """Toggle between 24-hour and 12-hour clock mode on the spa panel."""

    def __init__(self, spa: SpaClient) -> None:
        super().__init__(spa, "24h_time")
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_translation_key = "twenty_four_hour_time"

    @property
    def is_on(self) -> bool:
        return self._client.is_24_hour

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._client.set_24_hour_time(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._client.set_24_hour_time(False)


class HoldModeSwitch(BalboaEntity, SwitchEntity):
    """Put the spa into hold mode (pumps off for service / cover work).

    Hold mode is toggled by a single TOGGLE_STATE message; the read state
    comes from the spa's reported SpaState. We only emit the toggle when the
    desired state differs from the current one.
    """

    _attr_icon = "mdi:pause-circle"

    def __init__(self, spa: SpaClient) -> None:
        super().__init__(spa, "hold_mode")
        self._attr_translation_key = "hold_mode"

    @property
    def is_on(self) -> bool:
        return self._client.state == SpaState.HOLD_MODE

    async def _toggle(self) -> None:
        await self._client.send_message(
            MessageType.TOGGLE_STATE, ToggleItemCode.HOLD_MODE
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        if not self.is_on:
            await self._toggle()

    async def async_turn_off(self, **kwargs: Any) -> None:
        if self.is_on:
            await self._toggle()


class _ControlBackedSwitch(BalboaEntity, SwitchEntity):
    """Switch backed by a pybalboa SpaControl whose state is OffOnState."""

    def __init__(self, control: SpaControl, key_prefix: str, translation_key: str) -> None:
        super().__init__(control.client, control.name)
        self._control = control
        self._attr_translation_key = translation_key
        self._attr_translation_placeholders = {
            "index": f"{cast(int, control.index) + 1}"
        }

    @property
    def is_on(self) -> bool | None:
        if self._control.state == UnknownState.UNKNOWN:
            return None
        return self._control.state != OffOnState.OFF

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._control.set_state(OffOnState.ON)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._control.set_state(OffOnState.OFF)


class AuxSwitchEntity(_ControlBackedSwitch):
    """Auxiliary output switch (e.g. AUX1, AUX2)."""

    def __init__(self, control: SpaControl) -> None:
        super().__init__(control, "aux", "aux")


class MisterSwitchEntity(_ControlBackedSwitch):
    """Mister switch."""

    def __init__(self, control: SpaControl) -> None:
        super().__init__(control, "mister", "mister")
