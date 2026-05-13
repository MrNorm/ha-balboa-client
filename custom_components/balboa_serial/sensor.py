"""Support for Balboa diagnostic sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.const import EntityCategory, UnitOfElectricPotential
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BalboaConfigEntry
from .entity import BalboaEntity
from .pybalboa import SpaClient


@dataclass(frozen=True, kw_only=True)
class BalboaSensorEntityDescription(SensorEntityDescription):
    """Describes a Balboa diagnostic sensor."""

    value_fn: Callable[[SpaClient], object]


def _spa_state(spa: SpaClient) -> str | None:
    if (state := spa.state) is None:
        return None
    return state.name.lower()


SENSOR_DESCRIPTIONS: tuple[BalboaSensorEntityDescription, ...] = (
    BalboaSensorEntityDescription(
        key="spa_state",
        translation_key="spa_state",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=None,
        value_fn=_spa_state,
    ),
    BalboaSensorEntityDescription(
        key="heater_type",
        translation_key="heater_type",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda spa: spa.heater_type,
    ),
    BalboaSensorEntityDescription(
        key="voltage",
        translation_key="voltage",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        value_fn=lambda spa: spa.voltage,
    ),
    BalboaSensorEntityDescription(
        key="software_version",
        translation_key="software_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda spa: spa.software_version,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BalboaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the spa's diagnostic sensors."""
    spa = entry.runtime_data
    async_add_entities(BalboaSensorEntity(spa, desc) for desc in SENSOR_DESCRIPTIONS)


class BalboaSensorEntity(BalboaEntity, SensorEntity):
    """A diagnostic sensor reading a single property off the spa client."""

    entity_description: BalboaSensorEntityDescription

    def __init__(
        self, spa: SpaClient, description: BalboaSensorEntityDescription
    ) -> None:
        super().__init__(spa, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> object:
        return self.entity_description.value_fn(self._client)
