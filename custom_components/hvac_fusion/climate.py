"""Climate entity platform for HVAC Fusion living spaces."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
    ATTR_HVAC_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_ID,
    CONF_NAME,
    CONF_UNIQUE_ID,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import (
    DOMAIN,
    DEFAULT_HEAT_TO,
    DEFAULT_COOL_TO,
    CONF_SPACES,
    CONF_PRESETS,
    PRESET_MANUAL,
)
from hvac_crossover import HvacAction, SpaceDirective, Diagnostics

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the climate entities from discovery."""
    if discovery_info is None or DOMAIN not in hass.data:
        return

    manager = hass.data[DOMAIN]["manager"]
    entities = []

    for s_conf in manager.conf[CONF_SPACES]:
        entity = HvacFusionSpaceClimate(manager, s_conf)
        manager.register_space_entity(s_conf[CONF_ID], entity)
        entities.append(entity)

    async_add_entities(entities)

    # Initialize schedule states
    for entity in entities:
        await entity.async_update_from_schedule()

    # Trigger initial evaluation once entities are added
    hass.async_create_task(manager.async_evaluate())


class HvacFusionSpaceClimate(ClimateEntity):
    """Virtual climate entity representing a managed living space."""

    _attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
    _attr_hvac_modes = [
        HVACMode.HEAT_COOL,
        HVACMode.HEAT,
        HVACMode.COOL,
        HVACMode.OFF,
    ]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
        | ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
    )

    def __init__(self, manager: Any, space_conf: Dict[str, Any]) -> None:
        self._manager = manager
        self._space_conf = space_conf
        self._space_id = space_conf[CONF_ID]

        self._attr_name = space_conf[CONF_NAME]
        self._attr_unique_id = space_conf.get(
            CONF_UNIQUE_ID, f"hvac_fusion_{self._space_id}"
        )

        self._attr_hvac_mode = HVACMode.HEAT_COOL
        self._attr_hvac_action = HVACAction.IDLE

        # Presets & Schedules
        self._presets: Dict[str, str] = dict(space_conf.get(CONF_PRESETS, {}))
        self._attr_preset_modes = [PRESET_MANUAL] + list(self._presets.keys())
        self._attr_preset_mode = (
            list(self._presets.keys())[0] if self._presets else PRESET_MANUAL
        )

        self._target_temp_low = DEFAULT_HEAT_TO
        self._target_temp_high = DEFAULT_COOL_TO
        self._target_temp = DEFAULT_HEAT_TO

        self._active_delivery_units: List[str] = []
        self._active_producer: Optional[str] = None
        self._economic_crossover: Optional[float] = None
        self._system_phase: Optional[str] = None
        self._plan_explanation: Optional[str] = None

    @property
    def preset_mode(self) -> Optional[str]:
        return self._attr_preset_mode

    @property
    def active_schedule_entity(self) -> Optional[str]:
        """Returns the active schedule entity ID if currently obeying a schedule preset."""
        if self._attr_preset_mode == PRESET_MANUAL:
            return None
        return self._presets.get(self._attr_preset_mode)

    @property
    def target_temperature_low(self) -> Optional[float]:
        return self._target_temp_low

    @property
    def target_temperature_high(self) -> Optional[float]:
        return self._target_temp_high

    @property
    def target_temperature(self) -> Optional[float]:
        if self._attr_hvac_mode == HVACMode.HEAT:
            return self._target_temp_low
        if self._attr_hvac_mode == HVACMode.COOL:
            return self._target_temp_high
        return self._target_temp

    @property
    def current_temperature(self) -> Optional[float]:
        return self._manager.get_space_current_temp(self._space_conf)

    @property
    def hvac_action(self) -> Optional[HVACAction]:
        """Pass through active calling state from underlying physical climate entities."""
        if self._attr_hvac_mode == HVACMode.OFF:
            return HVACAction.OFF

        if self._active_delivery_units:
            actions = []
            for e_id in self._active_delivery_units:
                entity_id = self._manager.emitter_entity_map.get(e_id)
                if not entity_id:
                    continue
                state = self._manager.hass.states.get(entity_id)
                if state:
                    sub_action = state.attributes.get("hvac_action")
                    if sub_action:
                        actions.append(str(sub_action).lower())

            if "heating" in actions:
                return HVACAction.HEATING
            if "cooling" in actions:
                return HVACAction.COOLING
            if any(a in ("idle", "fan") for a in actions):
                return HVACAction.IDLE

        return self._attr_hvac_action

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        # Determine any emitters in cycling mode for this space
        cycling_emitters = [
            e_id
            for e_id in self._active_delivery_units
            if e_id in getattr(self._manager, "_cycling_state", {})
        ]
        attrs = {
            "space_id": self._space_id,
            "preset_mode": self._attr_preset_mode,
            "active_schedule": self.active_schedule_entity,
            "active_delivery_units": self._active_delivery_units,
            "cycling_emitters": cycling_emitters,
            "active_producer": self._active_producer,
            "economic_crossover_temp": self._economic_crossover,
            "system_phase": self._system_phase,
            "window_open": self._manager.get_space_window_open(self._space_conf),
            "explanation": self._plan_explanation,
        }
        return attrs

    def get_comfort_bounds(self) -> Tuple[Optional[float], Optional[float]]:
        """Returns (heat_to, cool_to) according to current mode and setpoints."""
        if self._attr_hvac_mode == HVACMode.OFF:
            return None, None
        if self._attr_hvac_mode == HVACMode.HEAT:
            return self._target_temp_low, None
        if self._attr_hvac_mode == HVACMode.COOL:
            return None, self._target_temp_high
        return self._target_temp_low, self._target_temp_high

    async def async_update_from_schedule(self) -> None:
        """Reads mode and setpoints from active schedule entity data."""
        if self._attr_preset_mode == PRESET_MANUAL:
            return

        sched_id = self.active_schedule_entity
        if not sched_id:
            return

        state = self._manager.hass.states.get(sched_id)
        if not state or state.state == "off":
            # Schedule has an unconfigured gap -> space is turned OFF
            self._attr_hvac_mode = HVACMode.OFF
            self.async_write_ha_state()
            return

        if state.state == "on":
            data_dict = state.attributes.get("data")
            if not isinstance(data_dict, dict):
                data_dict = state.attributes

            mode_str = str(
                data_dict.get("hvac_mode") or data_dict.get("mode", "heat_cool")
            ).lower()
            if mode_str == "heat":
                self._attr_hvac_mode = HVACMode.HEAT
            elif mode_str == "cool":
                self._attr_hvac_mode = HVACMode.COOL
            elif mode_str == "off":
                self._attr_hvac_mode = HVACMode.OFF
            else:
                self._attr_hvac_mode = HVACMode.HEAT_COOL

            heat_to = (
                data_dict.get("heat_to")
                or data_dict.get("target_temp_low")
                or data_dict.get("temperature")
            )
            if heat_to is not None:
                try:
                    self._target_temp_low = float(heat_to)
                    self._target_temp = float(heat_to)
                except (ValueError, TypeError):
                    pass

            cool_to = data_dict.get("cool_to") or data_dict.get("target_temp_high")
            if cool_to is not None:
                try:
                    self._target_temp_high = float(cool_to)
                except (ValueError, TypeError):
                    pass

            self.async_write_ha_state()

    def update_from_directive(
        self, directive: Optional[SpaceDirective], diagnostics: Optional[Diagnostics]
    ) -> None:
        """Updates internal status from the coordinator evaluation."""
        if not directive:
            self._attr_hvac_action = HVACAction.OFF
            self._active_delivery_units = None
            self._active_producer = None
            return

        if directive.action == HvacAction.HEATING:
            self._attr_hvac_action = HVACAction.HEATING
        elif directive.action == HvacAction.COOLING:
            self._attr_hvac_action = HVACAction.COOLING
        elif directive.action in (HvacAction.OFF, HvacAction.PASSIVE_VENTILATION):
            self._attr_hvac_action = HVACAction.OFF
        else:
            self._attr_hvac_action = HVACAction.IDLE

        self._active_delivery_units = directive.active_delivery_unit_ids
        self._active_producer = directive.active_producer_id
        self._plan_explanation = directive.explanation

        if diagnostics:
            self._economic_crossover = diagnostics.economic_crossover_temp
            self._system_phase = (
                diagnostics.system_phase.value
                if hasattr(diagnostics.system_phase, "value")
                else str(diagnostics.system_phase)
            )

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Handle preset selection."""
        if preset_mode not in self._attr_preset_modes:
            _LOGGER.warning(
                "Preset %s is not supported for %s", preset_mode, self._attr_name
            )
            return
        self._attr_preset_mode = preset_mode
        await self.async_update_from_schedule()
        self.async_write_ha_state()
        await self._manager.async_evaluate()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Handle manual setpoint adjustments (switches to manual preset)."""
        self._attr_preset_mode = PRESET_MANUAL

        if ATTR_TARGET_TEMP_LOW in kwargs:
            self._target_temp_low = float(kwargs[ATTR_TARGET_TEMP_LOW])
        if ATTR_TARGET_TEMP_HIGH in kwargs:
            self._target_temp_high = float(kwargs[ATTR_TARGET_TEMP_HIGH])
        if ATTR_TEMPERATURE in kwargs:
            val = float(kwargs[ATTR_TEMPERATURE])
            self._target_temp = val
            if self._attr_hvac_mode == HVACMode.HEAT:
                self._target_temp_low = val
            elif self._attr_hvac_mode == HVACMode.COOL:
                self._target_temp_high = val
            else:
                if abs(val - self._target_temp_low) <= abs(
                    val - self._target_temp_high
                ):
                    self._target_temp_low = val
                else:
                    self._target_temp_high = val

        if ATTR_HVAC_MODE in kwargs:
            self._attr_hvac_mode = kwargs[ATTR_HVAC_MODE]

        self.async_write_ha_state()
        await self._manager.async_evaluate()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Handle manual HVAC mode change (switches to manual preset)."""
        self._attr_preset_mode = PRESET_MANUAL
        self._attr_hvac_mode = hvac_mode
        self.async_write_ha_state()
        await self._manager.async_evaluate()
