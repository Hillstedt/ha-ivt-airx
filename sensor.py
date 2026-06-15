from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    MANUFACTURER,
    PATH_CH_STATUS,
    PATH_COMPRESSOR_STATUS,
    PATH_DHW_TEMP,
    PATH_MODULATION,
    PATH_OUTDOOR_TEMP,
    PATH_RETURN_TEMP,
    PATH_SUPPLY_TEMP,
)
from .coordinator import IVTAirXCoordinator


@dataclass(frozen=True, kw_only=True)
class AirXSensorDescription(SensorEntityDescription):
    resource_path: str = ""


# Phase 1: small starter set — just enough to confirm the data pipeline.
SENSOR_DESCRIPTIONS: tuple[AirXSensorDescription, ...] = (
    AirXSensorDescription(
        key="outdoor_temperature",
        name="Outdoor Temperature",
        resource_path=PATH_OUTDOOR_TEMP,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AirXSensorDescription(
        key="supply_temperature",
        name="Supply Temperature",
        resource_path=PATH_SUPPLY_TEMP,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AirXSensorDescription(
        key="return_temperature",
        name="Return Temperature",
        resource_path=PATH_RETURN_TEMP,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AirXSensorDescription(
        key="dhw_temperature",
        name="Hot Water Temperature",
        resource_path=PATH_DHW_TEMP,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AirXSensorDescription(
        key="compressor_modulation",
        name="Compressor Modulation",
        resource_path=PATH_MODULATION,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AirXSensorDescription(
        key="compressor_status",
        name="Compressor Status",
        resource_path=PATH_COMPRESSOR_STATUS,
        device_class=SensorDeviceClass.ENUM,
        options=["off", "heating", "cooling", "dhw", "defrost", "alarm"],
    ),
    AirXSensorDescription(
        key="ch_status",
        name="Central Heating Status",
        resource_path=PATH_CH_STATUS,
        device_class=SensorDeviceClass.ENUM,
        options=["off", "on"],
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: IVTAirXCoordinator = hass.data[DOMAIN][entry.entry_id]
    gateway_id: str = entry.data["gateway_id"]
    async_add_entities(
        AirXSensor(coordinator, description, gateway_id)
        for description in SENSOR_DESCRIPTIONS
    )


class AirXSensor(CoordinatorEntity[IVTAirXCoordinator], SensorEntity):
    """A single read-only sensor backed by one PoinTT resource path."""

    entity_description: AirXSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: IVTAirXCoordinator,
        description: AirXSensorDescription,
        gateway_id: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._gateway_id = gateway_id
        self._attr_unique_id = f"{gateway_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        return self.coordinator.get_value(self.entity_description.resource_path)

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        return self.coordinator.get_value(self.entity_description.resource_path) is not None

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._gateway_id)},
            "name": "IVT AirX Heat Pump",
            "manufacturer": MANUFACTURER,
            "model": "AirX 407",
        }
