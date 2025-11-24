"""Climate platform for Schluter DITRA-HEAT integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SchluterDataUpdateCoordinator
from .api import SchluterThermostat
from .const import (
    ATTR_GFCI_STATUS,
    ATTR_HEATING_PERCENT,
    ATTR_SETPOINT_MODE,
    ATTR_AIR_FLOOR_MODE,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    DOMAIN,
    MODE_MANUAL,
    MODE_SCHEDULE,
    OCCUPANCY_AWAY,
    OCCUPANCY_HOME,
    PRESET_AWAY,
    PRESET_HOME,
    PRESET_SCHEDULE,
    TEMP_STEP,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Schluter climate entities."""
    coordinator: SchluterDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Wait for first data fetch
    if not coordinator.data:
        return

    # Create climate entity for each thermostat
    entities = [
        SchluterClimate(coordinator, device_id)
        for device_id in coordinator.data
    ]

    async_add_entities(entities)


class SchluterClimate(CoordinatorEntity[SchluterDataUpdateCoordinator], ClimateEntity):
    """Representation of a Schluter DITRA-HEAT thermostat."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
    )
    _attr_target_temperature_step = TEMP_STEP

    def __init__(
        self, coordinator: SchluterDataUpdateCoordinator, device_id: int
    ) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{DOMAIN}_{device_id}"
        
        # Set device info
        device_name = coordinator.devices[device_id].get("name", f"Thermostat {device_id}")
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(device_id))},
            "name": device_name,
            "manufacturer": "Schluter Systems",
            "model": "DITRA-HEAT-E-RS1",
            "sw_version": "WiFi Thermostat",
            "via_device": (DOMAIN, "hub"),
        }

    @property
    def thermostat(self) -> SchluterThermostat:
        """Return the thermostat data."""
        return self.coordinator.data[self._device_id]

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self.thermostat.current_temp

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        return self.thermostat.target_temp

    @property
    def hvac_mode(self) -> HVACMode:
        """Return hvac operation mode."""
        # If target temp is set and above min, it's in heat mode
        if self.thermostat.target_temp and self.thermostat.target_temp > DEFAULT_MIN_TEMP:
            return HVACMode.HEAT
        return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction:
        """Return the current running hvac operation."""
        if self.thermostat.heating:
            return HVACAction.HEATING
        if self.hvac_mode == HVACMode.HEAT:
            return HVACAction.IDLE
        return HVACAction.OFF

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        # Map Schluter modes to HA preset modes
        if self.thermostat.setpoint_mode == MODE_SCHEDULE:
            return PRESET_SCHEDULE
        if self.thermostat.occupancy_mode == OCCUPANCY_AWAY:
            return PRESET_AWAY
        return PRESET_HOME

    @property
    def preset_modes(self) -> list[str]:
        """Return available preset modes."""
        return [PRESET_HOME, PRESET_AWAY, PRESET_SCHEDULE]

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        return self.thermostat.min_temp or DEFAULT_MIN_TEMP

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        return self.thermostat.max_temp or DEFAULT_MAX_TEMP

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        return {
            ATTR_SETPOINT_MODE: self.thermostat.setpoint_mode,
            ATTR_HEATING_PERCENT: self.thermostat.heating_percent,
            ATTR_GFCI_STATUS: self.thermostat.gfci_status,
            ATTR_AIR_FLOOR_MODE: self.thermostat.air_floor_mode,
        }

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        if hvac_mode == HVACMode.HEAT:
            # Set to a comfortable temperature if off
            if self.target_temperature is None or self.target_temperature <= DEFAULT_MIN_TEMP:
                await self.coordinator.api.set_temperature(self._device_id, 20.0)
        elif hvac_mode == HVACMode.OFF:
            # Set to minimum temperature to turn off
            await self.coordinator.api.set_temperature(self._device_id, DEFAULT_MIN_TEMP)
        
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return

        await self.coordinator.api.set_temperature(self._device_id, temperature)
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode == PRESET_SCHEDULE:
            # Set to schedule mode
            await self.coordinator.api.set_mode(self._device_id, MODE_SCHEDULE)
        elif preset_mode == PRESET_AWAY:
            # Set to manual mode with away occupancy
            await self.coordinator.api.set_mode(self._device_id, MODE_MANUAL)
            await self.coordinator.api.set_occupancy_mode(self._device_id, OCCUPANCY_AWAY)
        elif preset_mode == PRESET_HOME:
            # Set to manual mode with home occupancy
            await self.coordinator.api.set_mode(self._device_id, MODE_MANUAL)
            await self.coordinator.api.set_occupancy_mode(self._device_id, OCCUPANCY_HOME)
        
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and self._device_id in self.coordinator.data
