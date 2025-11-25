"""The Schluter DITRA-HEAT integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SchluterAPI, SchluterAPIError, SchluterAuthenticationError
from .const import (
    CONF_LOCATION_ID,
    CONF_REFRESH_TOKEN,
    DOMAIN,
    SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.CLIMATE, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Schluter DITRA-HEAT from a config entry."""
    session = async_get_clientsession(hass)
    api = SchluterAPI(session)
    
    # Authenticate
    try:
        await api.login(entry.data[CONF_REFRESH_TOKEN])
    except (SchluterAuthenticationError, SchluterAPIError) as err:
        _LOGGER.error("Failed to authenticate with Schluter API: %s", err)
        return False

    # Create coordinator
    coordinator = SchluterDataUpdateCoordinator(
        hass,
        api=api,
        location_id=entry.data[CONF_LOCATION_ID],
        entry=entry,
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class SchluterDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Schluter data from the API."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: SchluterAPI,
        location_id: int,
        entry: ConfigEntry,
    ) -> None:
        """Initialize."""
        self.api = api
        self.location_id = location_id
        self.devices: dict[int, dict] = {}
        self.config_entry = entry
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL),
        )

    async def _async_update_data(self):
        """Update data via library."""
        try:
            # Get list of devices (only on first call or if empty)
            if not self.devices:
                device_list = await self.api.get_devices(self.location_id)
                for device in device_list:
                    self.devices[device["id"]] = device
                _LOGGER.debug("Discovered %d devices", len(self.devices))

            # Get status for all devices
            data = {}
            for device_id in self.devices:
                try:
                    status = await self.api.get_thermostat_status(device_id)
                    # Update device name from initial discovery
                    status.name = self.devices[device_id].get("name", f"Device {device_id}")
                    data[device_id] = status
                except SchluterAPIError as err:
                    _LOGGER.warning("Failed to update device %s: %s", device_id, err)
                    continue

            return data

        except SchluterAuthenticationError as err:
            # Try to reconnect once by re-logging in
            _LOGGER.warning("Authentication error, attempting to re-login: %s", err)
            try:
                refresh_token = self.config_entry.data[CONF_REFRESH_TOKEN]
                await self.api.login(refresh_token)
                # Retry the update
                return await self._async_update_data()
            except SchluterAuthenticationError:
                # Refresh token is expired/invalid - trigger reauth flow
                _LOGGER.error("Refresh token expired or invalid. Triggering reauth flow.")
                entry = self.config_entry
                self.hass.async_create_task(
                    self.hass.config_entries.flow.async_init(
                        DOMAIN,
                        context={"source": "reauth", "entry_id": entry.entry_id},
                        data=entry.data,
                    )
                )
                raise UpdateFailed(
                    "Authentication failed. Please update your refresh token."
                ) from err
            except Exception as reconnect_err:
                raise UpdateFailed(f"Connection failed: {reconnect_err}") from reconnect_err

        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
