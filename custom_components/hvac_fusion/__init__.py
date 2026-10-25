"""Home Assistant Custom Component for HVAC Fusion Coordination."""

from __future__ import annotations

import logging
import os
from datetime import timedelta
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import (
    CONF_ENTITY_ID,
    CONF_ID,
    CONF_NAME,
    CONF_UNIQUE_ID,
    EVENT_HOMEASSISTANT_STARTED,
    Platform,
)
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.helpers import discovery
from homeassistant.helpers.event import async_track_time_interval
from hvac_crossover import (
    ComfortRange,
    CoordinatorConfig,
    DualFuelCoordinator,
    FuelType,
    HvacMode,
    HydronicEmitter,
    MiniSplitHead,
    ModulatingBoilerProducer,
    ProducerProfileFactory,
    SharedBoilerRole,
    Space,
    SpaceCondition,
    SystemSnapshot,
    SystemTopology,
    TariffSchedule,
)

from .const import (
    CONF_CEILING_HEIGHT,
    CONF_CONTROL_ENABLED,
    CONF_CYCLING_BAND,
    CONF_ELECTRIC_COST_PER_KWH,
    CONF_ELECTRIC_RATE_SENSOR,
    CONF_EMITTERS,
    CONF_EVALUATION_INTERVAL_MINUTES,
    CONF_FLOOR_AREA,
    CONF_FUEL_TYPE,
    CONF_GAS_COST_PER_THERM,
    CONF_GAS_RATE_SENSOR,
    CONF_MIN_FIRE_BTU,
    CONF_NOMINAL_BTU,
    CONF_OFFSET,
    CONF_OUTDOOR_TEMPERATURE_ENTITY,
    CONF_PRESETS,
    CONF_PRIORITY,
    CONF_PRODUCER,
    CONF_PRODUCERS,
    CONF_PROFILE,
    CONF_PROPANE_COST_PER_GAL,
    CONF_PROPANE_RATE_SENSOR,
    CONF_RATED_AFUE,
    CONF_SHARED_BOILER_ROLE,
    CONF_SOLAR_EXPORT_ENTITY,
    CONF_SPACES,
    CONF_TARIFFS,
    CONF_TEMP_SENSOR,
    CONF_TYPE,
    CONF_WINDOW_SENSOR,
    CONF_ZONE_ID,
    DEFAULT_COOL_TO,
    DEFAULT_CYCLING_BAND,
    DEFAULT_EVALUATION_INTERVAL_MINUTES,
    DEFAULT_HEAT_TO,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.CLIMATE, Platform.SENSOR]

EMITTER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TYPE): vol.In(["mini_split", "hydronic"]),
        vol.Required(CONF_PRODUCER): cv.string,
        vol.Required(CONF_ENTITY_ID): cv.entity_id,
        vol.Optional(CONF_NOMINAL_BTU, default=12000.0): vol.Coerce(float),
        vol.Optional(CONF_ZONE_ID, default="z1"): cv.string,
        vol.Optional(CONF_OFFSET, default=0.0): vol.Coerce(float),
    }
)

SPACE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ID): cv.string,
        vol.Required(CONF_NAME): cv.string,
        vol.Optional(CONF_UNIQUE_ID): cv.string,
        vol.Optional(CONF_TEMP_SENSOR): cv.entity_id,
        vol.Optional(CONF_WINDOW_SENSOR): cv.entity_id,
        vol.Optional(CONF_PRIORITY, default=5): cv.positive_int,
        vol.Optional(CONF_SHARED_BOILER_ROLE, default="independent"): vol.In(
            ["independent", "master", "slave"]
        ),
        vol.Optional(CONF_FLOOR_AREA, default=300.0): vol.Coerce(float),
        vol.Optional(CONF_CEILING_HEIGHT, default=9.0): vol.Coerce(float),
        vol.Optional(CONF_PRESETS, default={}): vol.Schema({cv.string: cv.entity_id}),
        vol.Required(CONF_EMITTERS): vol.All(cv.ensure_list, [EMITTER_SCHEMA]),
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_OUTDOOR_TEMPERATURE_ENTITY): cv.entity_id,
                vol.Optional(CONF_SOLAR_EXPORT_ENTITY): cv.entity_id,
                vol.Optional(CONF_CONTROL_ENABLED): vol.Coerce(bool),
                vol.Required(CONF_TARIFFS): vol.Schema(
                    {
                        vol.Optional(CONF_GAS_COST_PER_THERM, default=0.0): vol.Coerce(
                            float
                        ),
                        vol.Optional(
                            CONF_PROPANE_COST_PER_GAL, default=0.0
                        ): vol.Coerce(float),
                        vol.Required(CONF_ELECTRIC_COST_PER_KWH): vol.Coerce(float),
                    }
                ),
                vol.Required(CONF_PRODUCERS): vol.Schema(
                    {
                        cv.string: vol.Schema(
                            {
                                vol.Optional(CONF_NAME): cv.string,
                                vol.Optional(CONF_TYPE): cv.string,
                                vol.Optional(CONF_FUEL_TYPE): vol.In(
                                    [
                                        "natural_gas",
                                        "propane",
                                        "lp",
                                        "oil",
                                        "electricity",
                                    ]
                                ),
                                vol.Optional(CONF_PROFILE): cv.string,
                                vol.Optional(CONF_NOMINAL_BTU): vol.Coerce(float),
                                vol.Optional(CONF_RATED_AFUE, default=0.95): vol.Coerce(
                                    float
                                ),
                                vol.Optional(
                                    CONF_MIN_FIRE_BTU, default=20000.0
                                ): vol.Coerce(float),
                            }
                        )
                    }
                ),
                vol.Required(CONF_SPACES): vol.All(cv.ensure_list, [SPACE_SCHEMA]),
                vol.Optional(
                    CONF_CYCLING_BAND,
                    default=DEFAULT_CYCLING_BAND,
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_EVALUATION_INTERVAL_MINUTES,
                    default=DEFAULT_EVALUATION_INTERVAL_MINUTES,
                ): cv.positive_int,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


def _resolve_profile_path(profile_str: str) -> str:
    """Finds profile JSON in installed hvac_crossover library or user path."""
    if os.path.isabs(profile_str) and os.path.exists(profile_str):
        return profile_str

    try:
        import hvac_crossover

        pkg_dir = os.path.dirname(hvac_crossover.__file__)
        pkg_profiles_dir = os.path.join(pkg_dir, "profiles", "producers")
        candidate = os.path.join(pkg_profiles_dir, profile_str)
        if not candidate.endswith(".json"):
            candidate += ".json"
        if os.path.exists(candidate):
            return candidate
    except ImportError:
        pass

    if os.path.exists(profile_str):
        return profile_str
    if os.path.exists(profile_str + ".json"):
        return profile_str + ".json"

    return profile_str


class HvacFusionManager:
    """Manages coordinator lifecycle, sensor polling, and thermostat actuation."""

    def __init__(
        self,
        hass: HomeAssistant,
        conf: dict[str, Any],
        entry_id: str | None = None,
    ) -> None:
        self.hass = hass
        self.conf = conf
        self.entry_id = entry_id
        self.space_entities: dict[str, Any] = {}
        self.sensor_entities: list[Any] = []
        self.emitter_entity_map: dict[str, str] = {}
        self.emitter_types: dict[str, str] = {}
        self.emitter_zones: dict[str, str] = {}
        self.emitter_offsets: dict[str, float] = {}
        self.last_plan: Any | None = None
        self.control_enabled: bool = conf.get(CONF_CONTROL_ENABLED, True)
        self.cycling_band: float = float(
            conf.get(CONF_CYCLING_BAND, DEFAULT_CYCLING_BAND)
        )
        self._cycling_state: dict[str, bool] = {}
        self._cycling_logged: set[str] = set()

        self.topology: SystemTopology | None = None
        self.tariffs: TariffSchedule | None = None
        self.coordinator: DualFuelCoordinator | None = None

        # Collect schedule entities from configured presets
        self.schedule_entities: set[str] = set()
        for s_conf in self.spaces_config:
            for sched_id in s_conf.get(CONF_PRESETS, {}).values():
                self.schedule_entities.add(sched_id)

    @property
    def spaces_config(self) -> list[dict[str, Any]]:
        """Return spaces configuration normalized as a list."""
        raw = self.conf.get(CONF_SPACES, [])
        return list(raw.values()) if isinstance(raw, dict) else list(raw)

    def _resolve_sensor_or_float(
        self, sensor_entity: str | None, default_val: float
    ) -> float:
        """Resolve a rate from a sensor entity or fallback to float."""
        if sensor_entity:
            state = self.hass.states.get(sensor_entity)
            if state and state.state not in ("unavailable", "unknown"):
                try:
                    return float(state.state)
                except (ValueError, TypeError):
                    pass
        try:
            return float(default_val)
        except (ValueError, TypeError):
            return 0.0

    def get_current_tariffs(self) -> TariffSchedule:
        """Resolve current tariff rates (static or dynamic sensors)."""
        tariffs_conf = self.conf.get(CONF_TARIFFS, {})
        elec_sensor = tariffs_conf.get(CONF_ELECTRIC_RATE_SENSOR)
        elec_cost = self._resolve_sensor_or_float(
            elec_sensor, tariffs_conf.get(CONF_ELECTRIC_COST_PER_KWH, 0.0)
        )
        gas_sensor = tariffs_conf.get(CONF_GAS_RATE_SENSOR)
        gas_cost = self._resolve_sensor_or_float(
            gas_sensor, tariffs_conf.get(CONF_GAS_COST_PER_THERM, 0.0)
        )
        propane_sensor = tariffs_conf.get(CONF_PROPANE_RATE_SENSOR)
        propane_cost = self._resolve_sensor_or_float(
            propane_sensor, tariffs_conf.get(CONF_PROPANE_COST_PER_GAL, 0.0)
        )
        return TariffSchedule(
            gas_cost_per_therm=gas_cost,
            propane_cost_per_gal=propane_cost,
            elec_cost_per_kwh=elec_cost,
        )

    def register_sensor_entity(self, entity: Any) -> None:
        """Register a diagnostic sensor entity."""
        if entity not in self.sensor_entities:
            self.sensor_entities.append(entity)

    def unregister_sensor_entity(self, entity: Any) -> None:
        """Unregister a diagnostic sensor entity."""
        if entity in self.sensor_entities:
            self.sensor_entities.remove(entity)

    @property
    def primary_boiler(self) -> Any | None:
        """Returns the primary boiler producer if configured."""
        if not self.topology:
            return None
        from hvac_crossover import ProducerType

        boiler_types = (
            ProducerType.MODULATING_BOILER,
            ProducerType.ATMOSPHERIC_BOILER,
            ProducerType.STEAM_BOILER,
        )
        boilers = [
            p for p in self.topology.producers if p.producer_type in boiler_types
        ]
        return boilers[0] if boilers else None

    @property
    def primary_heat_pump(self) -> Any | None:
        """Returns the primary heat pump producer if configured."""
        if not self.topology:
            return None
        from hvac_crossover import ProducerType

        hps = [
            p
            for p in self.topology.producers
            if p.producer_type == ProducerType.INVERTER_HEAT_PUMP
        ]
        return hps[0] if hps else None

    @property
    def break_even_cop(self) -> float | None:
        """Derives critical break-even COP where Cost_HP ($/MMBtu) == Cost_Boiler ($/MMBtu)."""
        boiler = self.primary_boiler
        if not boiler or not self.coordinator:
            return None
        self.tariffs = self.get_current_tariffs()
        if not self.tariffs:
            return None
        from hvac_crossover import FuelType

        fuel_type = getattr(boiler, "fuel_type", FuelType.NATURAL_GAS)
        if fuel_type == FuelType.PROPANE and self.tariffs.propane_cost_per_gal <= 0:
            return None
        if fuel_type != FuelType.PROPANE and self.tariffs.gas_cost_per_therm <= 0:
            return None
        try:
            cop = self.coordinator.economics.compute_crossover_cop(self.tariffs, boiler)
            return round(cop, 2)
        except (ValueError, TypeError, ZeroDivisionError, AttributeError) as err:
            _LOGGER.debug("Could not compute break-even COP: %s", err)
            return None

    @property
    def economic_crossover_temperature(self) -> float | None:
        """Outdoor temperature where heat pump and boiler costs are equal."""
        boiler = self.primary_boiler
        hp = self.primary_heat_pump
        if not boiler or not hp or not self.coordinator:
            return None
        self.tariffs = self.get_current_tariffs()
        if not self.tariffs:
            return None
        from hvac_crossover import FuelType

        fuel_type = getattr(boiler, "fuel_type", FuelType.NATURAL_GAS)
        if fuel_type == FuelType.PROPANE and self.tariffs.propane_cost_per_gal <= 0:
            return None
        if fuel_type != FuelType.PROPANE and self.tariffs.gas_cost_per_therm <= 0:
            return None
        try:
            temp = self.coordinator.economics.compute_crossover_temperature(
                tariffs=self.tariffs,
                odu=hp,
                boiler=boiler,
            )
            return round(temp, 1) if temp is not None else None
        except (ValueError, TypeError, ZeroDivisionError, AttributeError) as err:
            _LOGGER.debug("Could not compute crossover temperature: %s", err)
            return None

    async def async_init(self) -> None:
        """Asynchronously load topology profiles and build coordinator."""
        self.topology = await self.hass.async_add_executor_job(self._build_topology)
        self.tariffs = self.get_current_tariffs()
        self.coordinator = DualFuelCoordinator(self.topology, CoordinatorConfig())

    def _build_topology(self) -> SystemTopology:
        producers = []
        for p_id, p_conf in self.conf.get(CONF_PRODUCERS, {}).items():
            p_name = p_conf.get(CONF_NAME, p_id)
            profile_name = p_conf.get(CONF_PROFILE)
            p_type = p_conf.get(CONF_TYPE, "inverter_heat_pump")
            fuel_str = p_conf.get(CONF_FUEL_TYPE, "natural_gas").lower()
            fuel = (
                FuelType.PROPANE
                if fuel_str in ("propane", "lp")
                else FuelType.NATURAL_GAS
            )

            if profile_name:
                resolved_path = _resolve_profile_path(profile_name)
                prod = ProducerProfileFactory.load_from_json(
                    file_path=resolved_path,
                    producer_id=p_id,
                    name=p_name,
                    fuel_type=fuel,
                )
                producers.append(prod)
            elif p_type == "modulating_boiler":
                prod = ModulatingBoilerProducer(
                    id=p_id,
                    name=p_name,
                    nominal_btu=float(p_conf.get(CONF_NOMINAL_BTU, 150000.0)),
                    fuel_type=fuel,
                    rated_afue=float(p_conf.get(CONF_RATED_AFUE, 0.95)),
                    min_fire_btu=float(p_conf.get(CONF_MIN_FIRE_BTU, 20000.0)),
                )
                producers.append(prod)
            else:
                _LOGGER.warning(
                    "Producer %s requires either a profile or modulating_boiler type",
                    p_id,
                )

        role_map = {
            "master": SharedBoilerRole.MASTER,
            "slave": SharedBoilerRole.SLAVE,
            "independent": SharedBoilerRole.INDEPENDENT,
        }

        spaces = []
        for s_conf in self.spaces_config:
            s_id = s_conf[CONF_ID]
            emitters = []
            for idx, e_conf in enumerate(s_conf[CONF_EMITTERS]):
                e_type = e_conf[CONF_TYPE]
                p_id = e_conf[CONF_PRODUCER]
                e_entity = e_conf[CONF_ENTITY_ID]
                e_id = f"{s_id}_{p_id}_{idx}"

                self.emitter_entity_map[e_id] = e_entity
                self.emitter_types[e_id] = e_type
                self.emitter_offsets[e_id] = float(e_conf.get(CONF_OFFSET, 0.0))

                if e_type == "mini_split":
                    emitters.append(
                        MiniSplitHead(
                            id=e_id,
                            producer_id=p_id,
                            nominal_btu=float(e_conf.get(CONF_NOMINAL_BTU, 12000.0)),
                        )
                    )
                elif e_type == "hydronic":
                    zone_id = e_conf.get(CONF_ZONE_ID, "z1")
                    self.emitter_zones[e_id] = zone_id
                    emitters.append(
                        HydronicEmitter(
                            id=e_id,
                            producer_id=p_id,
                            zone_id=zone_id,
                        )
                    )

            space = Space(
                id=s_id,
                name=s_conf[CONF_NAME],
                floor_area_sqft=float(s_conf.get(CONF_FLOOR_AREA, 300.0)),
                ceiling_height_ft=float(s_conf.get(CONF_CEILING_HEIGHT, 9.0)),
                priority=int(s_conf.get(CONF_PRIORITY, 5)),
                shared_boiler_role=role_map.get(
                    s_conf.get(CONF_SHARED_BOILER_ROLE, "independent"),
                    SharedBoilerRole.INDEPENDENT,
                ),
                emitters=emitters,
            )
            spaces.append(space)

        return SystemTopology(producers=producers, spaces=spaces)

    def register_space_entity(self, space_id: str, entity: Any) -> None:
        self.space_entities[space_id] = entity

    def get_space_current_temp(self, space_conf: dict[str, Any]) -> float | None:
        sensor_id = space_conf.get(CONF_TEMP_SENSOR)
        if sensor_id:
            state = self.hass.states.get(sensor_id)
            if state and state.state not in ("unavailable", "unknown"):
                if (
                    "current_temperature" in state.attributes
                    and state.attributes["current_temperature"] is not None
                ):
                    try:
                        return float(state.attributes["current_temperature"])
                    except (ValueError, TypeError):
                        pass
                try:
                    return float(state.state)
                except ValueError:
                    pass

        # Fallback to first emitter entity
        for e_conf in space_conf.get(CONF_EMITTERS, []):
            e_entity = e_conf.get(CONF_ENTITY_ID)
            if e_entity:
                state = self.hass.states.get(e_entity)
                if (
                    state
                    and "current_temperature" in state.attributes
                    and state.attributes["current_temperature"] is not None
                ):
                    try:
                        return float(state.attributes["current_temperature"])
                    except (ValueError, TypeError):
                        pass

        return None

    def get_space_window_open(self, space_conf: dict[str, Any]) -> bool:
        sensor_id = space_conf.get(CONF_WINDOW_SENSOR)
        if sensor_id:
            state = self.hass.states.get(sensor_id)
            if state and state.state == "on":
                return True
        return False

    def get_outdoor_temp(self) -> float:
        out_sensor = self.conf.get(CONF_OUTDOOR_TEMPERATURE_ENTITY)
        if out_sensor:
            state = self.hass.states.get(out_sensor)
            if state and state.state not in ("unavailable", "unknown"):
                if (
                    "temperature" in state.attributes
                    and state.attributes["temperature"] is not None
                ):
                    return float(state.attributes["temperature"])
                try:
                    return float(state.state)
                except ValueError:
                    pass
        return 35.0

    async def async_evaluate(self, now: Any | None = None) -> None:
        """Runs the coordination cycle and dispatches commands to physical thermostats."""
        outdoor_temp = self.get_outdoor_temp()
        self.tariffs = self.get_current_tariffs()

        space_conditions: dict[str, SpaceCondition] = {}
        for s_conf in self.spaces_config:
            s_id = s_conf[CONF_ID]
            curr_temp = self.get_space_current_temp(s_conf)
            if curr_temp is None:
                _LOGGER.debug(
                    "Space %s: temperature sensor unavailable, skipping this cycle",
                    s_id,
                )
                continue
            window_open = self.get_space_window_open(s_conf)

            entity = self.space_entities.get(s_id)
            if entity:
                heat_to, cool_to = entity.get_comfort_bounds()
            else:
                heat_to, cool_to = DEFAULT_HEAT_TO, DEFAULT_COOL_TO

            space_conditions[s_id] = SpaceCondition(
                current_temp=curr_temp,
                comfort=ComfortRange(heat_to=heat_to, cool_to=cool_to),
                window_open=window_open,
                occupied=True,
            )

        snapshot = SystemSnapshot(
            outdoor_temp=outdoor_temp,
            tariffs=self.tariffs,
            spaces=space_conditions,
        )

        plan = self.coordinator.evaluate(snapshot)
        self.last_plan = plan

        _LOGGER.info(
            "Evaluate, outdoor %s, conditions %s, plan %s",
            str(outdoor_temp),
            str(space_conditions),
            str(plan),
        )

        # Dispatch commands to subsidiary thermostats
        await self._dispatch_subsidiary_commands(plan, not self.control_enabled)

        # Update virtual climate entity states
        for entity in self.space_entities.values():
            s_dir = plan.space_directives.get(s_id)
            entity.update_from_directive(s_dir, plan.diagnostics)
            entity.async_write_ha_state()

        # Update diagnostic sensor entities
        for sensor in self.sensor_entities:
            sensor.async_write_ha_state()

    async def _dispatch_subsidiary_commands(self, plan: Any, dry_run: bool) -> None:
        """Actuates physical climate entities according to plan directives."""
        # Index spaces by s_id for quick lookup
        spaces_by_id = {s[CONF_ID]: s for s in self.spaces_config}

        # 1. Hydronic Boiler Zones
        # Determine active boiler zones
        active_boiler_zones = set()
        for prod_dir in plan.producer_directives.values():
            if prod_dir.active_zones:
                active_boiler_zones.update(prod_dir.active_zones)

        for e_id, e_type in self.emitter_types.items():
            if e_type != "hydronic":
                continue
            entity_id = self.emitter_entity_map[e_id]
            zone_id = self.emitter_zones.get(e_id, "z1")
            state = self.hass.states.get(entity_id)

            if zone_id in active_boiler_zones:
                # Find calling space target temp & space config
                target_temp = DEFAULT_HEAT_TO
                calling_s_conf = None
                for s_id, s_dir in plan.space_directives.items():
                    if (
                        e_id in s_dir.active_delivery_unit_ids
                        and s_dir.target_temp is not None
                    ):
                        target_temp = s_dir.target_temp
                        calling_s_conf = spaces_by_id.get(s_id)
                        break
                ideal_temp = target_temp + self.emitter_offsets.get(e_id, 0.0)

                # Check min/max clamping
                mn = None
                mx = None
                if state:
                    raw_mn = state.attributes.get("min_temp")
                    raw_mx = state.attributes.get("max_temp")
                    if raw_mn is not None:
                        mn = float(raw_mn)
                    if raw_mx is not None:
                        mx = float(raw_mx)

                clamped_temp = ideal_temp
                if mn is not None:
                    clamped_temp = max(clamped_temp, mn)
                if mx is not None:
                    clamped_temp = min(clamped_temp, mx)

                is_clamped = clamped_temp != ideal_temp

                if is_clamped:
                    if e_id not in self._cycling_logged:
                        _LOGGER.warning(
                            "Hydronic %s: ideal_temp %.1f clamped to %.1f (min=%s, max=%s). Engaging setpoint cycling.",
                            entity_id,
                            ideal_temp,
                            clamped_temp,
                            mn,
                            mx,
                        )
                        self._cycling_logged.add(e_id)

                    curr_space_temp = (
                        self.get_space_current_temp(calling_s_conf)
                        if calling_s_conf
                        else None
                    )
                    if curr_space_temp is None:
                        _LOGGER.warning(
                            "Hydronic %s: space temp sensor unavailable; falling back to direct clamped setpoint %.1f",
                            entity_id,
                            clamped_temp,
                        )
                        if e_id in self._cycling_state:
                            del self._cycling_state[e_id]
                        # Fallback normal actuation
                        curr_mode = state.state if state else None
                        curr_temp = (
                            state.attributes.get("temperature") if state else None
                        )
                        if curr_mode != "heat":
                            _LOGGER.info("Set hydronic %s to hvac_mode heat", entity_id)
                            if not dry_run:
                                await self.hass.services.async_call(
                                    "climate",
                                    "set_hvac_mode",
                                    {"entity_id": entity_id, "hvac_mode": "heat"},
                                    blocking=True,
                                )
                        if curr_temp != clamped_temp:
                            _LOGGER.info(
                                "Set hydronic %s to heat target %s",
                                entity_id,
                                clamped_temp,
                            )
                            if not dry_run:
                                await self.hass.services.async_call(
                                    "climate",
                                    "set_temperature",
                                    {
                                        "entity_id": entity_id,
                                        "temperature": clamped_temp,
                                        "hvac_mode": "heat",
                                    },
                                    blocking=True,
                                )
                    else:
                        # Cycling hysteresis for heating
                        on_threshold = ideal_temp - self.cycling_band
                        off_threshold = ideal_temp + self.cycling_band
                        cycle_on_temp = (
                            max(off_threshold, mn) if mn is not None else off_threshold
                        )
                        currently_on = self._cycling_state.get(e_id, False)

                        if not currently_on and curr_space_temp < on_threshold:
                            self._cycling_state[e_id] = True
                            _LOGGER.info(
                                "Cycling ON hydronic %s: space_temp %.1f < on_thresh %.1f (setpoint=%.1f)",
                                entity_id,
                                curr_space_temp,
                                on_threshold,
                                cycle_on_temp,
                            )
                            if not dry_run:
                                await self.hass.services.async_call(
                                    "climate",
                                    "set_hvac_mode",
                                    {"entity_id": entity_id, "hvac_mode": "heat"},
                                    blocking=True,
                                )
                                await self.hass.services.async_call(
                                    "climate",
                                    "set_temperature",
                                    {
                                        "entity_id": entity_id,
                                        "temperature": cycle_on_temp,
                                        "hvac_mode": "heat",
                                    },
                                    blocking=True,
                                )
                        elif currently_on and curr_space_temp >= off_threshold:
                            self._cycling_state[e_id] = False
                            _LOGGER.info(
                                "Cycling OFF hydronic %s: space_temp %.1f >= off_thresh %.1f",
                                entity_id,
                                curr_space_temp,
                                off_threshold,
                            )
                            if not dry_run:
                                await self.hass.services.async_call(
                                    "climate",
                                    "set_hvac_mode",
                                    {"entity_id": entity_id, "hvac_mode": "off"},
                                    blocking=True,
                                )
                        elif currently_on:
                            # Hold ON state: ensure mode is heat and setpoint is cycle_on_temp
                            curr_mode = state.state if state else None
                            curr_temp = (
                                state.attributes.get("temperature") if state else None
                            )
                            if curr_mode != "heat" and not dry_run:
                                await self.hass.services.async_call(
                                    "climate",
                                    "set_hvac_mode",
                                    {"entity_id": entity_id, "hvac_mode": "heat"},
                                    blocking=True,
                                )
                            if curr_temp != cycle_on_temp and not dry_run:
                                await self.hass.services.async_call(
                                    "climate",
                                    "set_temperature",
                                    {
                                        "entity_id": entity_id,
                                        "temperature": cycle_on_temp,
                                        "hvac_mode": "heat",
                                    },
                                    blocking=True,
                                )
                        else:
                            # Hold OFF state
                            if state and state.state != "off" and not dry_run:
                                await self.hass.services.async_call(
                                    "climate",
                                    "set_hvac_mode",
                                    {"entity_id": entity_id, "hvac_mode": "off"},
                                    blocking=True,
                                )
                else:
                    # Not clamped: clear cycling tracking and normal actuation
                    if e_id in self._cycling_state:
                        del self._cycling_state[e_id]
                    self._cycling_logged.discard(e_id)

                    curr_mode = state.state if state else None
                    curr_temp = state.attributes.get("temperature") if state else None

                    if curr_mode != "heat":
                        _LOGGER.info("Set hydronic %s to hvac_mode heat", entity_id)
                        if not dry_run:
                            await self.hass.services.async_call(
                                "climate",
                                "set_hvac_mode",
                                {"entity_id": entity_id, "hvac_mode": "heat"},
                                blocking=True,
                            )
                    if curr_temp != clamped_temp:
                        _LOGGER.info(
                            "Set hydronic %s to heat target %s", entity_id, clamped_temp
                        )
                        if not dry_run:
                            await self.hass.services.async_call(
                                "climate",
                                "set_temperature",
                                {
                                    "entity_id": entity_id,
                                    "temperature": clamped_temp,
                                    "hvac_mode": "heat",
                                },
                                blocking=True,
                            )
            else:
                # Hydronic zone inactive -> clear cycling and set hvac_mode: "off"
                if e_id in self._cycling_state:
                    del self._cycling_state[e_id]
                self._cycling_logged.discard(e_id)
                if state and state.state != "off":
                    _LOGGER.info("Set hydronic %s to off", entity_id)
                    if not dry_run:
                        await self.hass.services.async_call(
                            "climate",
                            "set_hvac_mode",
                            {"entity_id": entity_id, "hvac_mode": "off"},
                            blocking=True,
                        )

        # 2. Mini-Split Indoor Heads
        for s_id, s_dir in plan.space_directives.items():
            s_conf = spaces_by_id.get(s_id)
            for e_id, e_type in self.emitter_types.items():
                if e_type != "mini_split" or not e_id.startswith(f"{s_id}_"):
                    continue
                entity_id = self.emitter_entity_map[e_id]
                state = self.hass.states.get(entity_id)

                if (
                    e_id in s_dir.active_delivery_unit_ids
                    and s_dir.hvac_mode != HvacMode.OFF
                ):
                    desired_mode = s_dir.hvac_mode.value
                    base_temp = s_dir.target_temp or (
                        DEFAULT_HEAT_TO if desired_mode == "heat" else DEFAULT_COOL_TO
                    )
                    ideal_temp = base_temp + self.emitter_offsets.get(e_id, 0.0)

                    mn = None
                    mx = None
                    if state:
                        raw_mn = state.attributes.get("min_temp")
                        raw_mx = state.attributes.get("max_temp")
                        if raw_mn is not None:
                            mn = float(raw_mn)
                        if raw_mx is not None:
                            mx = float(raw_mx)

                    clamped_temp = ideal_temp
                    if mn is not None:
                        clamped_temp = max(clamped_temp, mn)
                    if mx is not None:
                        clamped_temp = min(clamped_temp, mx)

                    is_clamped = clamped_temp != ideal_temp

                    if is_clamped:
                        if e_id not in self._cycling_logged:
                            _LOGGER.warning(
                                "Mini-split %s: ideal_temp %.1f clamped to %.1f (min=%s, max=%s). Engaging setpoint cycling.",
                                entity_id,
                                ideal_temp,
                                clamped_temp,
                                mn,
                                mx,
                            )
                            self._cycling_logged.add(e_id)

                        curr_space_temp = (
                            self.get_space_current_temp(s_conf) if s_conf else None
                        )
                        if curr_space_temp is None:
                            _LOGGER.warning(
                                "Mini-split %s: space temp sensor unavailable; falling back to direct clamped setpoint %.1f",
                                entity_id,
                                clamped_temp,
                            )
                            if e_id in self._cycling_state:
                                del self._cycling_state[e_id]
                            # Normal fallback actuation
                            curr_mode = state.state if state else None
                            curr_temp = (
                                state.attributes.get("temperature") if state else None
                            )
                            if curr_mode != desired_mode:
                                _LOGGER.info(
                                    "Set mini-split %s mode to %s",
                                    entity_id,
                                    desired_mode,
                                )
                                if not dry_run:
                                    await self.hass.services.async_call(
                                        "climate",
                                        "set_hvac_mode",
                                        {
                                            "entity_id": entity_id,
                                            "hvac_mode": desired_mode,
                                        },
                                        blocking=True,
                                    )
                            if curr_temp != clamped_temp:
                                _LOGGER.info(
                                    "Set mini-split %s target temp to %s",
                                    entity_id,
                                    clamped_temp,
                                )
                                if not dry_run:
                                    await self.hass.services.async_call(
                                        "climate",
                                        "set_temperature",
                                        {
                                            "entity_id": entity_id,
                                            "temperature": clamped_temp,
                                        },
                                        blocking=True,
                                    )
                        else:
                            currently_on = self._cycling_state.get(e_id, False)

                            if desired_mode == "heat":
                                on_threshold = ideal_temp - self.cycling_band
                                off_threshold = ideal_temp + self.cycling_band
                                cycle_on_temp = (
                                    max(off_threshold, mn)
                                    if mn is not None
                                    else off_threshold
                                )

                                if not currently_on and curr_space_temp < on_threshold:
                                    self._cycling_state[e_id] = True
                                    _LOGGER.info(
                                        "Cycling ON mini-split %s: space_temp %.1f < on_thresh %.1f (heat setpoint=%.1f)",
                                        entity_id,
                                        curr_space_temp,
                                        on_threshold,
                                        cycle_on_temp,
                                    )
                                    if not dry_run:
                                        await self.hass.services.async_call(
                                            "climate",
                                            "set_hvac_mode",
                                            {
                                                "entity_id": entity_id,
                                                "hvac_mode": "heat",
                                            },
                                            blocking=True,
                                        )
                                        await self.hass.services.async_call(
                                            "climate",
                                            "set_temperature",
                                            {
                                                "entity_id": entity_id,
                                                "temperature": cycle_on_temp,
                                            },
                                            blocking=True,
                                        )
                                elif currently_on and curr_space_temp >= off_threshold:
                                    self._cycling_state[e_id] = False
                                    _LOGGER.info(
                                        "Cycling OFF mini-split %s: space_temp %.1f >= off_thresh %.1f",
                                        entity_id,
                                        curr_space_temp,
                                        off_threshold,
                                    )
                                    if not dry_run:
                                        await self.hass.services.async_call(
                                            "climate",
                                            "set_hvac_mode",
                                            {
                                                "entity_id": entity_id,
                                                "hvac_mode": "off",
                                            },
                                            blocking=True,
                                        )
                                elif currently_on:
                                    curr_mode = state.state if state else None
                                    curr_temp = (
                                        state.attributes.get("temperature")
                                        if state
                                        else None
                                    )
                                    if curr_mode != "heat" and not dry_run:
                                        await self.hass.services.async_call(
                                            "climate",
                                            "set_hvac_mode",
                                            {
                                                "entity_id": entity_id,
                                                "hvac_mode": "heat",
                                            },
                                            blocking=True,
                                        )
                                    if curr_temp != cycle_on_temp and not dry_run:
                                        await self.hass.services.async_call(
                                            "climate",
                                            "set_temperature",
                                            {
                                                "entity_id": entity_id,
                                                "temperature": cycle_on_temp,
                                            },
                                            blocking=True,
                                        )
                                else:
                                    if state and state.state != "off" and not dry_run:
                                        await self.hass.services.async_call(
                                            "climate",
                                            "set_hvac_mode",
                                            {
                                                "entity_id": entity_id,
                                                "hvac_mode": "off",
                                            },
                                            blocking=True,
                                        )
                            else:
                                # desired_mode == "cool"
                                on_threshold = ideal_temp + self.cycling_band
                                off_threshold = ideal_temp - self.cycling_band
                                cycle_on_temp = (
                                    min(off_threshold, mx)
                                    if mx is not None
                                    else off_threshold
                                )

                                if not currently_on and curr_space_temp > on_threshold:
                                    self._cycling_state[e_id] = True
                                    _LOGGER.info(
                                        "Cycling ON mini-split %s: space_temp %.1f > on_thresh %.1f (cool setpoint=%.1f)",
                                        entity_id,
                                        curr_space_temp,
                                        on_threshold,
                                        cycle_on_temp,
                                    )
                                    if not dry_run:
                                        await self.hass.services.async_call(
                                            "climate",
                                            "set_hvac_mode",
                                            {
                                                "entity_id": entity_id,
                                                "hvac_mode": "cool",
                                            },
                                            blocking=True,
                                        )
                                        await self.hass.services.async_call(
                                            "climate",
                                            "set_temperature",
                                            {
                                                "entity_id": entity_id,
                                                "temperature": cycle_on_temp,
                                            },
                                            blocking=True,
                                        )
                                elif currently_on and curr_space_temp <= off_threshold:
                                    self._cycling_state[e_id] = False
                                    _LOGGER.info(
                                        "Cycling OFF mini-split %s: space_temp %.1f <= off_thresh %.1f",
                                        entity_id,
                                        curr_space_temp,
                                        off_threshold,
                                    )
                                    if not dry_run:
                                        await self.hass.services.async_call(
                                            "climate",
                                            "set_hvac_mode",
                                            {
                                                "entity_id": entity_id,
                                                "hvac_mode": "off",
                                            },
                                            blocking=True,
                                        )
                                elif currently_on:
                                    curr_mode = state.state if state else None
                                    curr_temp = (
                                        state.attributes.get("temperature")
                                        if state
                                        else None
                                    )
                                    if curr_mode != "cool" and not dry_run:
                                        await self.hass.services.async_call(
                                            "climate",
                                            "set_hvac_mode",
                                            {
                                                "entity_id": entity_id,
                                                "hvac_mode": "cool",
                                            },
                                            blocking=True,
                                        )
                                    if curr_temp != cycle_on_temp and not dry_run:
                                        await self.hass.services.async_call(
                                            "climate",
                                            "set_temperature",
                                            {
                                                "entity_id": entity_id,
                                                "temperature": cycle_on_temp,
                                            },
                                            blocking=True,
                                        )
                                else:
                                    if state and state.state != "off" and not dry_run:
                                        await self.hass.services.async_call(
                                            "climate",
                                            "set_hvac_mode",
                                            {
                                                "entity_id": entity_id,
                                                "hvac_mode": "off",
                                            },
                                            blocking=True,
                                        )
                    else:
                        # Not clamped: clear cycling tracking and normal actuation
                        if e_id in self._cycling_state:
                            del self._cycling_state[e_id]
                        self._cycling_logged.discard(e_id)

                        curr_mode = state.state if state else None
                        curr_temp = (
                            state.attributes.get("temperature") if state else None
                        )

                        if curr_mode != desired_mode:
                            _LOGGER.info(
                                "Set mini-split %s mode to %s", entity_id, desired_mode
                            )
                            if not dry_run:
                                await self.hass.services.async_call(
                                    "climate",
                                    "set_hvac_mode",
                                    {"entity_id": entity_id, "hvac_mode": desired_mode},
                                    blocking=True,
                                )
                        if curr_temp != clamped_temp:
                            _LOGGER.info(
                                "Set mini-split %s target temp to %s",
                                entity_id,
                                clamped_temp,
                            )
                            if not dry_run:
                                await self.hass.services.async_call(
                                    "climate",
                                    "set_temperature",
                                    {
                                        "entity_id": entity_id,
                                        "temperature": clamped_temp,
                                    },
                                    blocking=True,
                                )
                else:
                    # Mini-split head inactive -> clear cycling and set hvac_mode: "off"
                    if e_id in self._cycling_state:
                        del self._cycling_state[e_id]
                    self._cycling_logged.discard(e_id)
                    if state and state.state != "off":
                        _LOGGER.info("Set mini-split %s mode to off", entity_id)
                        if not dry_run:
                            await self.hass.services.async_call(
                                "climate",
                                "set_hvac_mode",
                                {"entity_id": entity_id, "hvac_mode": "off"},
                                blocking=True,
                            )

    async def async_handle_schedule_change(self, event: Any) -> None:
        """Handles schedule block transitions."""
        entity_id = event.data.get("entity_id")
        for entity in self.space_entities.values():
            if getattr(entity, "active_schedule_entity", None) == entity_id:
                await entity.async_update_from_schedule()
        await self.async_evaluate()


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the HVAC Fusion integration from YAML configuration."""
    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]
    manager = HvacFusionManager(hass, conf)
    await manager.async_init()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["manager"] = manager

    # Forward platform setup to climate and sensor
    hass.async_create_task(
        discovery.async_load_platform(hass, Platform.CLIMATE, DOMAIN, {}, config)
    )
    hass.async_create_task(
        discovery.async_load_platform(hass, Platform.SENSOR, DOMAIN, {}, config)
    )

    # Listen to schedule transitions
    if manager.schedule_entities:
        from homeassistant.helpers.event import async_track_state_change_event

        async_track_state_change_event(
            hass, list(manager.schedule_entities), manager.async_handle_schedule_change
        )

    # Trigger evaluation once Home Assistant is fully started and entity states are ready
    async def _on_started(_event: Any) -> None:
        await manager.async_evaluate()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _on_started)

    interval_minutes = conf.get(
        CONF_EVALUATION_INTERVAL_MINUTES, DEFAULT_EVALUATION_INTERVAL_MINUTES
    )
    async_track_time_interval(
        hass, manager.async_evaluate, timedelta(minutes=interval_minutes)
    )

    async def handle_get_report(call: ServiceCall) -> ServiceResponse:
        resp = {"directives": "", "diagnostics": ""}
        manager = hass.data[DOMAIN].get("manager")
        if not manager or not manager.last_plan:
            return resp
        plan = manager.last_plan
        topology = manager.topology

        # Summarize the plan
        if topology.spaces:
            spaces = []
            for space in topology.spaces:
                s_id = space.id
                s_dir = plan.space_directives[s_id]

                target_str = "Off"
                if s_dir.target_temp is not None:
                    target_str = f"{s_dir.target_temp:.1f} °F"

                action_str = s_dir.action.value
                active_unit = (
                    ", ".join([u_id for u_id in s_dir.active_delivery_unit_ids])
                    or "None"
                )
                active_unit = active_unit.replace(s_id, "")

                space_plan = f"{s_id}: {action_str} to {target_str} via {active_unit}"
                spaces.append(space_plan)
            resp["dir"] = "; ".join(spaces)
        if plan.diagnostics:
            phase = plan.diagnostics.system_phase.value
            crossover = round(plan.diagnostics.economic_crossover_temp, 2)
            xp = plan.diagnostics.explanations
            explanations = "; ".join(xp) if xp else ""
            resp["diag"] = f"Phase: {phase} Xover: {crossover}: {explanations}"
        return resp

    hass.services.async_register(
        DOMAIN,
        "get_report",
        handle_get_report,
        supports_response=SupportsResponse.ONLY,
    )
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Set up HVAC Fusion from a config entry."""
    conf = dict(entry.data)
    conf.update(entry.options)

    manager = HvacFusionManager(hass, conf, entry_id=entry.entry_id)
    await manager.async_init()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = manager
    hass.data[DOMAIN]["manager"] = manager

    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])

    if manager.topology and manager.topology.spaces:
        await hass.config_entries.async_forward_entry_setups(entry, [Platform.CLIMATE])

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Unload a config entry."""
    manager = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    unload_platforms = [Platform.SENSOR]
    if Platform.CLIMATE in getattr(entry, "loaded_platforms", set()):
        unload_platforms.append(Platform.CLIMATE)
    elif manager and manager.topology and manager.topology.spaces:
        unload_platforms.append(Platform.CLIMATE)

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, unload_platforms
    )
    if unload_ok and entry.entry_id in hass.data.get(DOMAIN, {}):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
