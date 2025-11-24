"""Constants for the Schluter DITRA-HEAT integration."""
from typing import Final

DOMAIN: Final = "schluter_heat"

# Configuration
CONF_REFRESH_TOKEN: Final = "refresh_token"
CONF_LOCATION_ID: Final = "location_id"

# API URLs
BASE_URL: Final = "https://schluterditraheat.com/api/"
AUTH_BASE_URL: Final = "https://mobile-api.neviweb.com/api/"

# Update intervals
SCAN_INTERVAL: Final = 30  # seconds

# Device attributes
ATTR_SETPOINT_MODE: Final = "setpoint_mode"
ATTR_OCCUPANCY_MODE: Final = "occupancy_mode"
ATTR_GFCI_STATUS: Final = "gfci_status"
ATTR_HEATING_PERCENT: Final = "heating_percent"
ATTR_AIR_FLOOR_MODE: Final = "air_floor_mode"

# Operating modes
MODE_MANUAL: Final = "manual"
MODE_SCHEDULE: Final = "schedule"

# Occupancy modes
OCCUPANCY_HOME: Final = "home"
OCCUPANCY_AWAY: Final = "away"

# Preset modes (for HA)
PRESET_HOME: Final = "home"
PRESET_AWAY: Final = "away"
PRESET_SCHEDULE: Final = "schedule"

# Temperature limits (Celsius)
DEFAULT_MIN_TEMP: Final = 5.0
DEFAULT_MAX_TEMP: Final = 33.0
TEMP_STEP: Final = 0.5

# Energy monitoring
DEFAULT_FLOOR_WATTAGE: Final = 15  # Watts per square foot (typical)
CONF_FLOOR_AREA: Final = "floor_area"  # Square feet
CONF_FLOOR_WATTAGE: Final = "floor_wattage"  # Watts per square foot
