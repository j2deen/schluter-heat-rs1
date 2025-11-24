"""Sensor platform for Schluter DITRA-HEAT-E-RS1 integration."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfPower, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SchluterDataUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Schluter sensor entities."""
    coordinator: SchluterDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Wait for first data fetch
    if not coordinator.data:
        return

    # Create sensor entities for each thermostat
    entities = []
    for device_id in coordinator.data:
        entities.extend([
            SchluterHeatingSensor(coordinator, device_id),
            SchluterHeatingTimeSensor(coordinator, device_id),
            SchluterGFCISensor(coordinator, device_id),
            SchluterPowerSensor(coordinator, device_id, entry),
        ])

    async_add_entities(entities)


class SchluterHeatingSensor(CoordinatorEntity[SchluterDataUpdateCoordinator], SensorEntity):
    """Sensor for current heating output percentage."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = SensorDeviceClass.POWER_FACTOR

    def __init__(
        self, coordinator: SchluterDataUpdateCoordinator, device_id: int
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{DOMAIN}_{device_id}_heating"
        self._attr_name = "Heating output"
        
        # Link to device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(device_id))},
        }

    @property
    def native_value(self) -> int | None:
        """Return the heating percentage."""
        if self._device_id in self.coordinator.data:
            return self.coordinator.data[self._device_id].heating_percent
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and self._device_id in self.coordinator.data


class SchluterHeatingTimeSensor(CoordinatorEntity[SchluterDataUpdateCoordinator], SensorEntity):
    """Sensor for daily heating time tracking."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_suggested_display_precision = 1

    def __init__(
        self, coordinator: SchluterDataUpdateCoordinator, device_id: int
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{DOMAIN}_{device_id}_heating_time"
        self._attr_name = "Heating time today"
        self._heating_time = 0.0  # Hours
        self._last_heating = False
        
        # Link to device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(device_id))},
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self._device_id in self.coordinator.data:
            thermostat = self.coordinator.data[self._device_id]
            is_heating = thermostat.heating
            
            # If currently heating and was heating last update, add time
            if is_heating and self._last_heating:
                # Coordinator updates every 30 seconds
                self._heating_time += 30 / 3600  # Convert seconds to hours
            
            self._last_heating = is_heating
        
        self.async_write_ha_state()

    @property
    def native_value(self) -> float:
        """Return the total heating time today."""
        return round(self._heating_time, 1)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {
            "is_heating": self._last_heating,
            "last_update": self.coordinator.last_update_success_time,
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and self._device_id in self.coordinator.data


class SchluterGFCISensor(CoordinatorEntity[SchluterDataUpdateCoordinator], SensorEntity):
    """Sensor for GFCI safety status."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["ok", "error", "unknown"]

    def __init__(
        self, coordinator: SchluterDataUpdateCoordinator, device_id: int
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{DOMAIN}_{device_id}_gfci"
        self._attr_name = "GFCI status"
        
        # Link to device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(device_id))},
        }

    @property
    def native_value(self) -> str | None:
        """Return the GFCI status."""
        if self._device_id in self.coordinator.data:
            status = self.coordinator.data[self._device_id].gfci_status
            return status if status in self._attr_options else "unknown"
        return None

    @property
    def icon(self) -> str:
        """Return the icon."""
        if self.native_value == "ok":
            return "mdi:shield-check"
        elif self.native_value == "error":
            return "mdi:shield-alert"
        return "mdi:shield-off"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and self._device_id in self.coordinator.data


class SchluterPowerSensor(CoordinatorEntity[SchluterDataUpdateCoordinator], SensorEntity):
    """Sensor for estimated power consumption.
    
    NOTE: This is an ESTIMATE, not measured power consumption.
    The RS1 controller does not have built-in power metering.
    
    Power is calculated as:
        max_power = floor_area × wattage_per_sq_ft
        current_power = max_power × (heating_percent / 100)
    
    The heating_percent comes from the controller (accurate),
    but the total wattage is based on your configuration.
    
    Accuracy: ±5-10% for typical installations
    """

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = SensorDeviceClass.POWER

    def __init__(
        self, 
        coordinator: SchluterDataUpdateCoordinator, 
        device_id: int,
        entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{DOMAIN}_{device_id}_power"
        self._attr_name = "Estimated power"
        self._entry = entry
        
        # Link to device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(device_id))},
        }

    @property
    def native_value(self) -> float | None:
        """Return the estimated power consumption."""
        if self._device_id not in self.coordinator.data:
            return None
        
        thermostat = self.coordinator.data[self._device_id]
        heating_percent = thermostat.heating_percent or 0
        
        # Get floor configuration from options or data
        floor_area = self._entry.options.get(f"floor_area_{self._device_id}") or \
                     self._entry.data.get(f"floor_area_{self._device_id}", 0)
        floor_wattage = self._entry.options.get(f"floor_wattage_{self._device_id}") or \
                        self._entry.data.get(f"floor_wattage_{self._device_id}", 15)
        
        if floor_area == 0:
            # No floor area configured, can't estimate
            return None
        
        # Calculate: Total Watts = Area (sq ft) × Wattage per sq ft × (Heating % / 100)
        max_power = floor_area * floor_wattage
        current_power = max_power * (heating_percent / 100)
        
        return round(current_power, 1)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        floor_area = self._entry.options.get(f"floor_area_{self._device_id}") or \
                     self._entry.data.get(f"floor_area_{self._device_id}", 0)
        floor_wattage = self._entry.options.get(f"floor_wattage_{self._device_id}") or \
                        self._entry.data.get(f"floor_wattage_{self._device_id}", 15)
        
        attrs = {
            "floor_area_sq_ft": floor_area,
            "wattage_per_sq_ft": floor_wattage,
        }
        
        if floor_area > 0:
            attrs["max_power_watts"] = floor_area * floor_wattage
        
        return attrs

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and self._device_id in self.coordinator.data
