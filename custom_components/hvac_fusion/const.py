"""Constants for the HVAC Fusion integration."""

DOMAIN = "hvac_fusion"

CONF_OUTDOOR_TEMPERATURE_ENTITY = "outdoor_temperature_entity"
CONF_SOLAR_EXPORT_ENTITY = "solar_export_entity"
CONF_TARIFFS = "tariffs"
CONF_GAS_COST_PER_THERM = "gas_cost_per_therm"
CONF_PROPANE_COST_PER_GAL = "propane_cost_per_gal"
CONF_ELECTRIC_COST_PER_KWH = "electric_cost_per_kwh"
CONF_CONTROL_ENABLED = "control_enabled"
CONF_FUEL_TYPE = "fuel_type"

CONF_PRODUCERS = "producers"
CONF_SPACES = "spaces"
CONF_TEMP_SENSOR = "temp_sensor"
CONF_WINDOW_SENSOR = "window_sensor"
CONF_EMITTERS = "emitters"
CONF_PRODUCER = "producer"
CONF_TYPE = "type"
CONF_ZONE_ID = "zone_id"
CONF_NOMINAL_BTU = "nominal_btu"
CONF_SHARED_BOILER_ROLE = "shared_boiler_role"
CONF_PRIORITY = "priority"
CONF_FLOOR_AREA = "floor_area_sqft"
CONF_CEILING_HEIGHT = "ceiling_height_ft"
CONF_PROFILE = "profile"
CONF_RATED_AFUE = "rated_afue"
CONF_MIN_FIRE_BTU = "min_fire_btu"
CONF_OFFSET = "offset"
# Offset modifies the *commanded target setpoint* sent to physical devices:
# commanded_target = space_target + offset
# It does NOT alter the reported space temperature reading.
# Sign conventions:
# - HEATING:
#   - Room too warm (overheating): use NEGATIVE offset (e.g. -2.0) to command a lower setpoint.
#   - Room too cold (underheating, e.g. ceiling sensor reads warm): use POSITIVE offset (+2.0).
# - COOLING:
#   - Room too warm (undercooling): use NEGATIVE offset (e.g. -2.0) to command a lower setpoint.
#   - Room too cold (overcooling): use POSITIVE offset (+2.0) to command a higher setpoint.

CONF_EVALUATION_INTERVAL_MINUTES = "evaluation_interval_minutes"
DEFAULT_EVALUATION_INTERVAL_MINUTES = 5

CONF_CYCLING_BAND = "cycling_band_deg"
DEFAULT_CYCLING_BAND = 2.0

CONF_PRESETS = "presets"
PRESET_MANUAL = "manual"

DEFAULT_HEAT_TO = 68.0
DEFAULT_COOL_TO = 74.0
