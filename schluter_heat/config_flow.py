"""Config flow for Schluter DITRA-HEAT integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from aiohttp import ClientSession

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SchluterAPI, SchluterAuthenticationError, SchluterAPIError
from .const import CONF_LOCATION_ID, CONF_REFRESH_TOKEN, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

STEP_REAUTH_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    session = async_get_clientsession(hass)
    api = SchluterAPI(session)

    # Test authentication with username/password
    try:
        # Login with credentials to get refresh token
        login_response = await api.login_with_credentials(
            data[CONF_USERNAME], 
            data[CONF_PASSWORD]
        )
        
        # Extract refresh token from response
        refresh_token = login_response.get("refreshToken") or login_response.get("refresh_token")
        
        if not refresh_token:
            _LOGGER.error(f"Login response missing refresh token: {login_response.keys()}")
            raise ValueError("No refresh token received from login")
        
        # Connect to get session
        await api.connect()
        
        # Get all locations for this user
        locations = await api.get_locations()
        
        if not locations:
            raise ValueError("No locations found for this account")
        
        # If location_id is provided (from location selection step), validate it
        if CONF_LOCATION_ID in data:
            location_id = data[CONF_LOCATION_ID]
            devices = await api.get_devices(location_id)
            
            if not devices:
                raise ValueError("No devices found at this location")
            
            device_count = len(devices)
            
            # Find location name
            location_name = next(
                (loc.get("name", f"Location {location_id}") 
                 for loc in locations if loc.get("id") == location_id),
                f"Location {location_id}"
            )
            
            return {
                "title": f"Schluter Heat - {location_name}",
                "device_count": device_count,
                "refresh_token": refresh_token,
                "locations": locations,
            }
        else:
            # Initial validation - just return locations
            return {
                "refresh_token": refresh_token,
                "locations": locations,
            }
        
    except SchluterAuthenticationError as err:
        _LOGGER.error("Authentication failed: %s", err)
        raise ValueError("invalid_auth") from err
    except SchluterAPIError as err:
        _LOGGER.error("API error: %s", err)
        raise ValueError("cannot_connect") from err
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.exception("Unexpected exception: %s", err)
        raise ValueError("unknown") from err


class SchluterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Schluter DITRA-HEAT."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._refresh_token = None
        self._locations = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - username/password entry."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                
                # Store refresh token and locations for next step
                self._refresh_token = info["refresh_token"]
                self._locations = info["locations"]
                
                # If only one location, auto-select it
                if len(self._locations) == 1:
                    location = self._locations[0]
                    location_id = location["id"]
                    
                    # Validate this location has devices
                    validation_data = {
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_LOCATION_ID: location_id,
                    }
                    info = await validate_input(self.hass, validation_data)
                    
                    # Check if already configured
                    await self.async_set_unique_id(str(location_id))
                    self._abort_if_unique_id_configured()
                    
                    # Create entry with auto-selected location
                    return self.async_create_entry(
                        title=info["title"],
                        data={
                            CONF_REFRESH_TOKEN: self._refresh_token,
                            CONF_LOCATION_ID: location_id,
                        }
                    )
                else:
                    # Multiple locations - show picker
                    return await self.async_step_location()
                
            except ValueError as err:
                error_str = str(err)
                if "invalid_auth" in error_str:
                    errors["base"] = "invalid_auth"
                elif "cannot_connect" in error_str:
                    errors["base"] = "cannot_connect"
                elif "No locations found" in error_str:
                    errors["base"] = "no_locations"
                elif "No devices found" in error_str:
                    errors["base"] = "no_devices"
                else:
                    errors["base"] = "unknown"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "username_help": "Your Schluter account email address",
                "password_help": "Your password (used once, never stored)",
            }
        )
    
    async def async_step_location(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle location selection when multiple locations exist."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            location_id = user_input[CONF_LOCATION_ID]
            
            # Check if already configured
            await self.async_set_unique_id(str(location_id))
            self._abort_if_unique_id_configured()
            
            # Find location name for title
            location_name = next(
                (loc.get("name", f"Location {location_id}") 
                 for loc in self._locations if loc.get("id") == location_id),
                f"Location {location_id}"
            )
            
            # Create entry
            return self.async_create_entry(
                title=f"Schluter Heat - {location_name}",
                data={
                    CONF_REFRESH_TOKEN: self._refresh_token,
                    CONF_LOCATION_ID: location_id,
                }
            )
        
        # Build location choices
        location_options = {
            str(loc["id"]): loc.get("name", f"Location {loc['id']}")
            for loc in self._locations
        }
        
        return self.async_show_form(
            step_id="location",
            data_schema=vol.Schema({
                vol.Required(CONF_LOCATION_ID): vol.In(location_options),
            }),
            errors=errors,
            description_placeholders={
                "location_help": "Select which location to add to Home Assistant"
            }
        )
            errors=errors,
            description_placeholders={
                "username_help": "Your Schluter account email address",
                "password_help": "Your Schluter account password (never stored)",
                "location_id_help": "Found in the URL when viewing your thermostats (e.g., /location/103355)"
            }
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Handle reauth when refresh token expires."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reauth confirmation."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            # Get the existing entry
            entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
            
            if entry is None:
                return self.async_abort(reason="reauth_failed")
            
            try:
                # Validate credentials and get new refresh token
                # Pass username/password but only location_id for validation
                validation_data = {
                    CONF_USERNAME: user_input[CONF_USERNAME],
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                    CONF_LOCATION_ID: entry.data[CONF_LOCATION_ID],
                }
                
                info = await validate_input(self.hass, validation_data)
                
                # Store only the new refresh token, NOT the credentials
                new_data = {
                    CONF_LOCATION_ID: entry.data[CONF_LOCATION_ID],
                    CONF_REFRESH_TOKEN: info["refresh_token"],
                }
                
            except ValueError as err:
                error_str = str(err)
                if "invalid_auth" in error_str:
                    errors["base"] = "invalid_auth"
                elif "cannot_connect" in error_str:
                    errors["base"] = "cannot_connect"
                else:
                    errors["base"] = "unknown"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during reauth")
                errors["base"] = "unknown"
            else:
                # Update the config entry with new refresh token
                self.hass.config_entries.async_update_entry(
                    entry,
                    data=new_data,
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "username_help": "Your Schluter account email address",
                "password_help": "Your password (used once to generate new token, never stored)",
            }
        )
