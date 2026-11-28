"""Home Assistant Custom Component for HVAC Fusion Coordination."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
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
    AtmosphericBoilerProducer,
    ComfortRange,
    CoordinatorConfig,
    DualFuelCoordinator,
    EmitterType,
    FuelType,
    FurnaceProducer,
    FurnaceRegister,
    HvacMode,
    HydronicEmitter,
    InverterHeatPumpProducer,
    MiniSplitHead,
    ModulatingBoilerProducer,
    ProducerProfileFactory,
    SharedBoilerRole,
    Space,
    SpaceCondition,
    SteamBoilerProducer,
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
    CONF_ENVELOPE_SCORE,
    CONF_EVALUATION_INTERVAL_MINUTES,
    CONF_FLOOR_AREA,
    CONF_FUEL_TYPE,
    CONF_GAS_COST_PER_THERM,
    CONF_GAS_RATE_SENSOR,
    CONF_HAS_OUTDOOR_RESET,
    CONF_HYDRONIC_TYPE,
    CONF_MIN_FIRE_BTU,
    CONF_NOMINAL_BTU,
    CONF_OFFSET,
    CONF_OIL_COST_PER_GAL,
    CONF_OIL_RATE_SENSOR,
    CONF_OUTDOOR_TEMPERATURE_ENTITY,
    CONF_PRESETS,
    CONF_PRIMARY_FLOW_GPM,
    CONF_PRIORITY,
    CONF_PRODUCER,
    CONF_PRODUCERS,
    CONF_PROFILE,
    CONF_PROFILES_BASE_URL,
    CONF_PROPANE_COST_PER_GAL,
    CONF_PROPANE_RATE_SENSOR,
    CONF_RATED_AFUE,
    CONF_SHARED_BOILER_ROLE,
    CONF_SOLAR_EXPORT_ENTITY,
    CONF_SPACES,
    CONF_TARIFFS,
    CONF_TEMP_SENSOR,
    CONF_THERMAL_MASS,
    CONF_TYPE,
    CONF_WINDOW_SENSOR,
    CONF_ZONE_ID,
    DEFAULT_COOL_TO,
    DEFAULT_CYCLING_BAND,
    DEFAULT_ENVELOPE_SCORE,
    DEFAULT_EVALUATION_INTERVAL_MINUTES,
    DEFAULT_HEAT_TO,
    DEFAULT_PROFILES_BASE_URL,
    DEFAULT_THERMAL_MASS,
    DOMAIN,
    PROFILE_REVALIDATE_INTERVAL_SECONDS,
)
from .profile_store import async_ensure_profiles, resolve_profile_path

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.CLIMATE, Platform.SENSOR]

EMITTER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TYPE): vol.In(["mini_split", "hydronic", "furnace"]),
        vol.Required(CONF_PRODUCER): cv.string,
        vol.Optional(CONF_ENTITY_ID): vol.Any(cv.entity_id, None),
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
            ["independent", "primary", "secondary"]
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
                                vol.Optional(CONF_MIN_FIRE_BTU): vol.Coerce(float),
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


def _resolve_profile_path(profile_str: str, hass: HomeAssistant | None = None) -> str:
    """Finds profile JSON in installed hvac_crossover, local cache, or user path."""
    return resolve_profile_path(profile_str, hass)


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

        self._schedule_locks: dict[str, float] = {}
        self._dynamic_schedule_unsubs: dict[str, Any] = {}

        self.cost_estimates: dict[str, float | None] = {
            "chosen_cost_per_hr": None,
            "fossil_fuel_baseline_cost_per_hr": None,
            "heat_pump_baseline_cost_per_hr": None,
            "savings_vs_fossil_fuel_per_hr": None,
            "savings_vs_heat_pump_per_hr": None,
            "total_heat_loss_btu_per_hr": None,
        }
        self.cumulative_estimated_cost: float = 0.0
        self.cumulative_fossil_fuel_baseline_cost: float = 0.0
        self.cumulative_heat_pump_baseline_cost: float = 0.0
        self.cumulative_savings_vs_fossil_fuel: float = 0.0
        self.cumulative_savings_vs_heat_pump: float = 0.0
        self._last_cost_eval_utc: datetime | None = None
        self._space_mass_temps: dict[str, float] = {}
        self._last_profile_check: datetime | None = None

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
                    _LOGGER.warning(
                        "Tariff entity %s state %r cannot be parsed as a float; falling back to static rate %.4f",
                        sensor_entity,
                        state.state,
                        default_val,
                    )
            else:
                _LOGGER.debug(
                    "Tariff entity %s is %s; falling back to static rate %.4f",
                    sensor_entity,
                    state.state if state else "not found",
                    default_val,
                )
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
        oil_sensor = tariffs_conf.get(CONF_OIL_RATE_SENSOR)
        oil_cost = self._resolve_sensor_or_float(
            oil_sensor, tariffs_conf.get(CONF_OIL_COST_PER_GAL, 0.0)
        )
        return TariffSchedule(
            gas_cost_per_therm=gas_cost,
            propane_cost_per_gal=propane_cost,
            oil_cost_per_gal=oil_cost,
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
            ProducerType.FURNACE,
        )
        boilers = [
            p for p in self.topology.producers if p.producer_type in boiler_types
        ]
        return boilers[0] if boilers else None

    @property
    def estimated_boiler_return_temp_f(self) -> float | None:
        """Estimated return water temperature for the primary boiler."""
        if self.last_plan:
            diag = self.last_plan.diagnostics
            if diag and diag.boiler_return_temps:
                primary = self.primary_boiler
                if primary and primary.id in diag.boiler_return_temps:
                    return diag.boiler_return_temps[primary.id]
                return next(iter(diag.boiler_return_temps.values()))
        return None

    @property
    def estimated_boiler_efficiency(self) -> float | None:
        """Estimated in-situ efficiency for the primary boiler."""
        if self.last_plan:
            diag = self.last_plan.diagnostics
            if diag and diag.boiler_efficiencies:
                primary = self.primary_boiler
                if primary and primary.id in diag.boiler_efficiencies:
                    return diag.boiler_efficiencies[primary.id]
                return next(iter(diag.boiler_efficiencies.values()))
        return None

    @property
    def boiler_condensing_state(self) -> str | None:
        """Condensing operational state (condensing, marginal, dry)."""
        if self.last_plan:
            diag = self.last_plan.diagnostics
            if diag and diag.boiler_condensing_states:
                primary = self.primary_boiler
                if primary and primary.id in diag.boiler_condensing_states:
                    return diag.boiler_condensing_states[primary.id]
                return next(iter(diag.boiler_condensing_states.values()))
        return None

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
        if self.tariffs.elec_cost_per_kwh <= 0:
            return None
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
        if self.tariffs.elec_cost_per_kwh <= 0:
            return None
        if fuel_type == FuelType.PROPANE and self.tariffs.propane_cost_per_gal <= 0:
            return None
        if fuel_type != FuelType.PROPANE and self.tariffs.gas_cost_per_therm <= 0:
            return None
        if (
            self.last_plan
            and self.last_plan.diagnostics
            and self.last_plan.diagnostics.economic_crossover_temp is not None
        ):
            return round(self.last_plan.diagnostics.economic_crossover_temp, 1)
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

    @property
    def system_phase(self) -> str | None:
        """Return the current macro system operational phase."""
        if self.last_plan and self.last_plan.diagnostics:
            phase = self.last_plan.diagnostics.system_phase
            return phase.value if hasattr(phase, "value") else str(phase)
        return None

    def _get_configured_profile_names(self) -> list[str]:
        """Return all configured non-empty producer profile identifiers."""
        return [
            str(p_conf[CONF_PROFILE])
            for p_conf in self.conf.get(CONF_PRODUCERS, {}).values()
            if p_conf.get(CONF_PROFILE)
        ]

    async def _async_refresh_profiles(self, force: bool = False) -> bool:
        """Ensure configured remote profiles are downloaded and periodically revalidated."""
        now_utc = datetime.now(UTC)
        if (
            not force
            and self._last_profile_check is not None
            and (now_utc - self._last_profile_check).total_seconds()
            < PROFILE_REVALIDATE_INTERVAL_SECONDS
        ):
            return False

        base_url = str(self.conf.get(CONF_PROFILES_BASE_URL, DEFAULT_PROFILES_BASE_URL))
        changed = await async_ensure_profiles(
            self.hass,
            self._get_configured_profile_names(),
            base_url=base_url,
            revalidate=True,
        )
        self._last_profile_check = now_utc
        return changed

    async def async_init(self) -> None:
        """Asynchronously load topology profiles and build coordinator."""
        await self._async_refresh_profiles(force=True)
        self.topology = await self.hass.async_add_executor_job(self._build_topology)
        self.tariffs = self.get_current_tariffs()
        self.coordinator = DualFuelCoordinator(self.topology, CoordinatorConfig())

    def _build_topology(self) -> SystemTopology:
        producers = []
        for p_id, p_conf in self.conf.get(CONF_PRODUCERS, {}).items():
            p_name = p_conf.get(CONF_NAME, p_id)
            profile_name = p_conf.get(CONF_PROFILE)
            p_type = p_conf.get(CONF_TYPE, "heat_pump")
            fuel_str = str(p_conf.get(CONF_FUEL_TYPE, "natural_gas")).lower()
            if fuel_str in ("propane", "lp"):
                fuel = FuelType.PROPANE
            elif fuel_str in ("oil", "fuel_oil", "oil_no2"):
                fuel = FuelType.OIL
            else:
                fuel = FuelType.NATURAL_GAS

            if profile_name:
                resolved_path = _resolve_profile_path(profile_name, self.hass)
                nominal_val = p_conf.get(CONF_NOMINAL_BTU)
                prod = ProducerProfileFactory.load_from_json(
                    file_path=resolved_path,
                    producer_id=p_id,
                    name=p_name,
                    fuel_type=fuel,
                    nominal_btu=float(nominal_val) if nominal_val is not None else None,
                )
                if isinstance(prod, ModulatingBoilerProducer):
                    if CONF_HAS_OUTDOOR_RESET in p_conf:
                        prod.has_outdoor_reset = bool(p_conf[CONF_HAS_OUTDOOR_RESET])
                    if CONF_PRIMARY_FLOW_GPM in p_conf:
                        prod.primary_flow_gpm = float(p_conf[CONF_PRIMARY_FLOW_GPM])
                producers.append(prod)
            elif p_type in ("boiler", "modulating_boiler"):
                prod = ModulatingBoilerProducer(
                    id=p_id,
                    name=p_name,
                    nominal_btu=float(p_conf.get(CONF_NOMINAL_BTU, 150000.0)),
                    fuel_type=fuel,
                    rated_afue=float(p_conf.get(CONF_RATED_AFUE, 0.95)),
                    min_fire_btu=float(p_conf[CONF_MIN_FIRE_BTU])
                    if CONF_MIN_FIRE_BTU in p_conf
                    else None,
                    has_outdoor_reset=bool(p_conf.get(CONF_HAS_OUTDOOR_RESET, False)),
                    primary_flow_gpm=float(p_conf.get(CONF_PRIMARY_FLOW_GPM, 12.0)),
                )
                producers.append(prod)
            elif p_type == "atmospheric_boiler":
                prod = AtmosphericBoilerProducer(
                    id=p_id,
                    name=p_name,
                    nominal_btu=float(p_conf.get(CONF_NOMINAL_BTU, 100000.0)),
                    fuel_type=fuel,
                    rated_afue=float(p_conf.get(CONF_RATED_AFUE, 0.83)),
                )
                producers.append(prod)
            elif p_type == "steam_boiler":
                prod = SteamBoilerProducer(
                    id=p_id,
                    name=p_name,
                    nominal_btu=float(p_conf.get(CONF_NOMINAL_BTU, 100000.0)),
                    fuel_type=fuel,
                    rated_afue=float(p_conf.get(CONF_RATED_AFUE, 0.81)),
                )
                producers.append(prod)
            elif p_type == "furnace":
                prod = FurnaceProducer(
                    id=p_id,
                    name=p_name,
                    nominal_btu=float(p_conf.get(CONF_NOMINAL_BTU, 80000.0)),
                    fuel_type=fuel,
                    rated_afue=float(p_conf.get(CONF_RATED_AFUE, 0.80)),
                )
                producers.append(prod)
            else:
                _LOGGER.warning(
                    "Producer %s requires either a profile or known producer type",
                    p_id,
                )

        role_map = {
            "primary": SharedBoilerRole.PRIMARY,
            "secondary": SharedBoilerRole.SECONDARY,
            "independent": SharedBoilerRole.INDEPENDENT,
        }

        spaces = []
        for s_conf in self.spaces_config:
            s_id = s_conf[CONF_ID]
            emitters = []
            for idx, e_conf in enumerate(s_conf[CONF_EMITTERS]):
                e_type = e_conf[CONF_TYPE]
                p_id = e_conf[CONF_PRODUCER]
                e_entity = e_conf.get(CONF_ENTITY_ID)
                e_id = f"{s_id}_{p_id}_{idx}"

                if e_entity:
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
                    hydronic_type_str = e_conf.get(
                        CONF_HYDRONIC_TYPE, "fin_tube_baseboard"
                    )
                    hydronic_type_map = {
                        "fin_tube_baseboard": EmitterType.FIN_TUBE_BASEBOARD,
                        "cast_iron_radiator": EmitterType.CAST_IRON_RADIATOR,
                        "in_floor_radiant": EmitterType.IN_FLOOR_RADIANT,
                        "kickspace": EmitterType.KICKSPACE,
                        "hydro_air": EmitterType.HYDRO_AIR,
                    }
                    emitter_type_enum = hydronic_type_map.get(
                        hydronic_type_str, EmitterType.FIN_TUBE_BASEBOARD
                    )
                    emitters.append(
                        HydronicEmitter(
                            id=e_id,
                            producer_id=p_id,
                            zone_id=zone_id,
                            emitter_type=emitter_type_enum,
                        )
                    )
                elif e_type == "furnace":
                    emitters.append(
                        FurnaceRegister(
                            id=e_id,
                            producer_id=p_id,
                        )
                    )

            raw_env = s_conf.get(CONF_ENVELOPE_SCORE, DEFAULT_ENVELOPE_SCORE)
            raw_mass = s_conf.get(CONF_THERMAL_MASS, DEFAULT_THERMAL_MASS)
            space = Space(
                id=s_id,
                name=s_conf[CONF_NAME],
                floor_area_sqft=float(s_conf.get(CONF_FLOOR_AREA, 300.0)),
                ceiling_height_ft=float(s_conf.get(CONF_CEILING_HEIGHT, 9.0)),
                envelope_score=float(raw_env),
                thermal_mass=int(raw_mass),
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

    def _resolve_schedule_keys(self, schedule_id: str) -> set[str]:
        """Resolve all aliases (entity_id slug and unique_id) for a schedule."""
        keys = {schedule_id, schedule_id.removeprefix("schedule.")}
        try:
            from homeassistant.helpers import entity_registry as er

            ent_reg = er.async_get(self.hass)
            entry = ent_reg.async_get(
                f"schedule.{schedule_id.removeprefix('schedule.')}"
            )
            if entry and entry.unique_id:
                keys.add(entry.unique_id)
            else:
                e_id = ent_reg.async_get_entity_id("schedule", "schedule", schedule_id)
                if e_id:
                    keys.add(e_id)
                    keys.add(e_id.removeprefix("schedule."))
        except Exception:
            pass
        return keys

    def acquire_schedule_lock(self, schedule_id: str, duration: int = 300) -> None:
        """Acquire a temporary edit lock on a schedule for human editing."""
        import time

        exp = time.time() + duration
        for key in self._resolve_schedule_keys(schedule_id):
            self._schedule_locks[key] = exp

        schedule_key = schedule_id.removeprefix("schedule.")
        self._notify_schedule_lock_change()
        self.hass.bus.async_fire(
            "hvac_fusion_schedule_lock_acquired",
            {"schedule_id": schedule_key, "duration": duration},
        )

    def release_schedule_lock(self, schedule_id: str) -> None:
        """Release a human edit lock on a schedule."""
        for key in self._resolve_schedule_keys(schedule_id):
            self._schedule_locks.pop(key, None)

        schedule_key = schedule_id.removeprefix("schedule.")
        self._notify_schedule_lock_change()
        self.hass.bus.async_fire(
            "hvac_fusion_schedule_lock_released",
            {"schedule_id": schedule_key},
        )

    def is_schedule_locked(self, schedule_id: str) -> bool:
        """Check if a schedule is currently locked by a human editor."""
        import time

        now = time.time()
        for key in self._resolve_schedule_keys(schedule_id):
            exp = self._schedule_locks.get(key)
            if exp is not None:
                if now <= exp:
                    return True
                self._schedule_locks.pop(key, None)
        return False

    def _notify_schedule_lock_change(self) -> None:
        """Notify registered space entities to update their state attributes."""
        for entity in self.space_entities.values():
            if hasattr(entity, "async_write_ha_state"):
                entity.async_write_ha_state()

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

    # Space is definitely not calling when indoor temp exceeds heating setpoint by this margin
    COST_NOT_CALLING_OVERSHOOT_F = 2.0
    # 15-minute RC time constant for smoothed thermal-mass temperature tracking
    COST_MASS_EMA_TAU_HOURS = 0.25

    def _update_cost_estimates(
        self,
        plan: Any,
        outdoor_temp: float,
        space_conditions: dict[str, SpaceCondition],
    ) -> None:
        """Compute instantaneous $/hr heating cost and baseline savings, and integrate totals."""
        if not self.topology or not self.coordinator or not self.tariffs:
            return
        if not self.topology.spaces:
            return

        now_utc = datetime.now(UTC)
        dt_hours = (
            min(
                1.0,
                max(
                    0.0,
                    (now_utc - self._last_cost_eval_utc).total_seconds() / 3600.0,
                ),
            )
            if self._last_cost_eval_utc is not None
            else 0.0
        )

        total_heat_loss_btu = 0.0
        total_chosen_hr = 0.0
        has_chosen = False
        total_boiler_hr = 0.0
        total_chosen_with_boiler = 0.0
        has_boiler_baseline = False
        total_hp_hr = 0.0
        total_chosen_with_hp = 0.0
        has_hp_baseline = False

        safety_band = self.coordinator.config.heat_pump_min_temp_safety_band_f

        for space in self.topology.spaces:
            cond = space_conditions.get(space.id)
            if cond is None:
                continue

            # Continuously track smoothed thermal-mass temperature (15-min EMA)
            prev_mass_temp = self._space_mass_temps.get(space.id)
            if prev_mass_temp is None or dt_hours <= 0.0:
                new_mass_temp = cond.current_temp
                dt_mass = 0.0
            else:
                alpha = min(1.0, dt_hours / self.COST_MASS_EMA_TAU_HOURS)
                new_mass_temp = prev_mass_temp + alpha * (
                    cond.current_temp - prev_mass_temp
                )
                dt_mass = new_mass_temp - prev_mass_temp
            self._space_mass_temps[space.id] = new_mass_temp

            if cond.window_open or cond.comfort.heat_to is None:
                continue

            entity = self.space_entities.get(space.id)
            if entity is not None and getattr(entity, "hvac_mode", None) in (
                "off",
                "cool",
            ):
                continue

            # Classify available producers so zero-load spaces still report $0.00/hr rather than unknown
            space_has_hp = False
            space_has_fuel = False
            for emitter in space.emitters:
                producer = self.topology.get_producer(emitter.producer_id)
                if producer is None:
                    continue
                if isinstance(producer, InverterHeatPumpProducer):
                    space_has_hp = True
                else:
                    space_has_fuel = True

            if not space_has_hp and not space_has_fuel:
                continue

            # If space is clearly above heating setpoint (setback coast-down, solar/cooking/stairwell heat),
            # emitters are not calling: instantaneous heating load is 0.0.
            if (
                cond.current_temp
                >= cond.comfort.heat_to + self.COST_NOT_CALLING_OVERSHOOT_F
            ):
                load_btu = 0.0
            else:
                load_btu = space.estimated_heat_loss_btu_per_hr(
                    cond.comfort.heat_to, outdoor_temp
                )
                # Add thermal-mass pull-up energy when actively warming toward setpoint
                if (
                    dt_hours > 0.0
                    and dt_mass > 0.0
                    and cond.current_temp < cond.comfort.heat_to + 1.0
                ):
                    load_btu += space.thermal_capacitance_btu_per_f * (
                        dt_mass / dt_hours
                    )

            if load_btu <= 0.0:
                has_chosen = True
                if space_has_fuel:
                    has_boiler_baseline = True
                if space_has_hp:
                    has_hp_baseline = True
                continue
            total_heat_loss_btu += load_btu
            mmbtu_hr = load_btu / 1_000_000.0

            hp_costs: list[float] = []
            fuel_costs: list[float] = []
            unit_costs: dict[str, float] = {}
            has_hp_emitter = False

            for emitter in space.emitters:
                producer = self.topology.get_producer(emitter.producer_id)
                if producer is None:
                    continue
                if isinstance(producer, InverterHeatPumpProducer):
                    has_hp_emitter = True
                try:
                    cost_mmbtu, _ = (
                        self.coordinator.economics.evaluate_delivery_unit_cost(
                            delivery_unit=emitter,
                            outdoor_temp_f=outdoor_temp,
                            tariffs=self.tariffs,
                            topology=self.topology,
                            load_btu=load_btu,
                            part_load=True,
                            safety_band_f=safety_band,
                        )
                    )
                except (ZeroDivisionError, ValueError, TypeError):
                    continue
                if cost_mmbtu == float("inf") or cost_mmbtu < 0:
                    continue
                unit_costs[emitter.id] = cost_mmbtu
                if isinstance(producer, InverterHeatPumpProducer):
                    hp_costs.append(cost_mmbtu)
                else:
                    fuel_costs.append(cost_mmbtu)

            # When a space has an HP emitter that is locked out by low ambient,
            # the pure-HP baseline falls back to COP=1.0 electric resistance heat.
            if has_hp_emitter and not hp_costs:
                elec_rate = self.tariffs.marginal_electric_cost(0.0)
                if elec_rate > 0:
                    hp_costs.append(elec_rate / 0.0034121416)

            if not unit_costs:
                continue

            s_dir = plan.space_directives.get(space.id) if plan else None
            active_costs = [
                unit_costs[e_id]
                for e_id in (s_dir.active_delivery_unit_ids if s_dir else [])
                if e_id in unit_costs
            ]
            chosen_mmbtu = (
                min(active_costs) if active_costs else min(unit_costs.values())
            )
            chosen_hr = mmbtu_hr * chosen_mmbtu
            total_chosen_hr += chosen_hr
            has_chosen = True

            if fuel_costs:
                total_boiler_hr += mmbtu_hr * min(fuel_costs)
                total_chosen_with_boiler += chosen_hr
                has_boiler_baseline = True

            if hp_costs:
                total_hp_hr += mmbtu_hr * min(hp_costs)
                total_chosen_with_hp += chosen_hr
                has_hp_baseline = True

        savings_boiler_hr = (
            (total_boiler_hr - total_chosen_with_boiler)
            if has_boiler_baseline
            else None
        )
        savings_hp_hr = (
            (total_hp_hr - total_chosen_with_hp) if has_hp_baseline else None
        )

        self.cost_estimates = {
            "chosen_cost_per_hr": round(total_chosen_hr, 4) if has_chosen else None,
            "fossil_fuel_baseline_cost_per_hr": (
                round(total_boiler_hr, 4) if has_boiler_baseline else None
            ),
            "heat_pump_baseline_cost_per_hr": (
                round(total_hp_hr, 4) if has_hp_baseline else None
            ),
            "savings_vs_fossil_fuel_per_hr": (
                round(savings_boiler_hr, 4) if savings_boiler_hr is not None else None
            ),
            "savings_vs_heat_pump_per_hr": (
                round(savings_hp_hr, 4) if savings_hp_hr is not None else None
            ),
            "total_heat_loss_btu_per_hr": round(total_heat_loss_btu, 1),
        }

        if dt_hours > 0.0:
            if has_chosen:
                self.cumulative_estimated_cost += total_chosen_hr * dt_hours
            if has_boiler_baseline:
                self.cumulative_fossil_fuel_baseline_cost += total_boiler_hr * dt_hours
            if has_hp_baseline:
                self.cumulative_heat_pump_baseline_cost += total_hp_hr * dt_hours
            if savings_boiler_hr is not None:
                self.cumulative_savings_vs_fossil_fuel += savings_boiler_hr * dt_hours
            if savings_hp_hr is not None:
                self.cumulative_savings_vs_heat_pump += savings_hp_hr * dt_hours
        self._last_cost_eval_utc = now_utc

    async def async_evaluate(self, now: Any | None = None) -> None:
        """Runs the coordination cycle and dispatches commands to physical thermostats."""
        if await self._async_refresh_profiles(force=False):
            self.topology = await self.hass.async_add_executor_job(self._build_topology)
            self.coordinator = DualFuelCoordinator(self.topology, CoordinatorConfig())

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

        try:
            plan = self.coordinator.evaluate(snapshot)
            self.last_plan = plan
        except ZeroDivisionError as err:
            _LOGGER.warning(
                "Cannot evaluate crossover plan due to missing or zero tariffs: %s",
                err,
            )
            return

        self._update_cost_estimates(plan, outdoor_temp, space_conditions)

        _LOGGER.debug(
            "Evaluate, outdoor %s, conditions %s, plan %s",
            str(outdoor_temp),
            str(space_conditions),
            str(plan),
        )

        # Dispatch commands to subsidiary thermostats
        await self._dispatch_subsidiary_commands(plan, not self.control_enabled)

        # Update virtual climate entity states
        for s_id, entity in self.space_entities.items():
            s_dir = plan.space_directives.get(s_id)
            entity.update_from_directive(s_dir, plan.diagnostics)
            if getattr(entity, "hass", None) is not None:
                entity.async_write_ha_state()

        # Update diagnostic sensor entities
        for sensor in self.sensor_entities:
            if getattr(sensor, "hass", None) is not None:
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
            entity_id = self.emitter_entity_map.get(e_id)
            if not entity_id:
                continue
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
                        currently_on = self._cycling_state.setdefault(e_id, False)

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
                entity_id = self.emitter_entity_map.get(e_id)
                if not entity_id:
                    continue
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
                                "Mini-split %s: ideal_temp %.1f clamped to %.1f (min=%s, max=%s)."
                                " Engaging setpoint cycling.",
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
                                "Mini-split %s: space temp sensor unavailable; "
                                "falling back to direct clamped setpoint %.1f",
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
                            currently_on = self._cycling_state.setdefault(e_id, False)

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
                                        "Cycling ON mini-split %s: space_temp %.1f < on_thresh %.1f "
                                        "(heat setpoint=%.1f)",
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
                                        "Cycling ON mini-split %s: space_temp %.1f > on_thresh %.1f "
                                        "(cool setpoint=%.1f)",
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

    async def async_register_space_preset(
        self, target: str, preset_name: str, schedule_entity: str
    ) -> bool:
        """Dynamically attach a schedule-backed preset to a managed space."""
        if not preset_name or not schedule_entity:
            return False

        dynamic_presets: dict[str, dict[str, str]] = self.hass.data.setdefault(
            DOMAIN, {}
        ).setdefault("dynamic_presets", {})
        dynamic_presets.setdefault(target, {})[preset_name] = schedule_entity

        matched = False
        for space_id, climate_entity in self.space_entities.items():
            c_id = getattr(climate_entity, "entity_id", None)
            if target in (space_id, c_id):
                await climate_entity.async_register_preset(preset_name, schedule_entity)
                matched = True

        if matched and schedule_entity not in self.schedule_entities:
            self.schedule_entities.add(schedule_entity)
            from homeassistant.helpers.event import async_track_state_change_event

            self._dynamic_schedule_unsubs[schedule_entity] = (
                async_track_state_change_event(
                    self.hass, [schedule_entity], self.async_handle_schedule_change
                )
            )
        return matched

    async def async_unregister_space_preset(
        self, target: str, preset_name: str
    ) -> bool:
        """Dynamically detach a schedule-backed preset from a managed space."""
        if not preset_name:
            return False

        matched = False
        removed_schedules: set[str] = set()
        keys_to_clean: set[str] = {target}
        for space_id, climate_entity in self.space_entities.items():
            c_id = getattr(climate_entity, "entity_id", None)
            if target in (space_id, c_id):
                keys_to_clean.add(space_id)
                if c_id:
                    keys_to_clean.add(c_id)
                removed = await climate_entity.async_unregister_preset(preset_name)
                if removed is not None:
                    matched = True
                    removed_schedules.add(removed)

        dynamic_presets: dict[str, dict[str, str]] = self.hass.data.get(DOMAIN, {}).get(
            "dynamic_presets", {}
        )
        for key in keys_to_clean:
            if key in dynamic_presets:
                dynamic_presets[key].pop(preset_name, None)
                if not dynamic_presets[key]:
                    dynamic_presets.pop(key, None)

        for sched_eid in removed_schedules:
            still_used = any(
                sched_eid in getattr(ent, "_presets", {}).values()
                for ent in self.space_entities.values()
            )
            if not still_used:
                self.schedule_entities.discard(sched_eid)
                if unsub := self._dynamic_schedule_unsubs.pop(sched_eid, None):
                    unsub()

        return matched

    async def async_handle_schedule_change(self, event: Any) -> None:
        """Handles schedule block transitions."""
        entity_id = event.data.get("entity_id")
        for entity in self.space_entities.values():
            if getattr(entity, "active_schedule_entity", None) == entity_id:
                await entity.async_update_from_schedule()
        await self.async_evaluate()

    @property
    def window_sensor_entities(self) -> list[str]:
        """Return deduplicated list of configured window/door sensor entity IDs."""
        sensors: list[str] = []
        seen: set[str] = set()
        for space_conf in self.conf.get(CONF_SPACES, []):
            if not isinstance(space_conf, dict):
                continue
            eid = space_conf.get(CONF_WINDOW_SENSOR)
            if isinstance(eid, str) and eid and eid not in seen:
                seen.add(eid)
                sensors.append(eid)
        return sensors

    async def async_handle_window_sensor_change(self, event: Any) -> None:
        """Trigger immediate re-evaluation when a window/door sensor opens or closes."""
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        if new_state is None:
            return
        new_val = str(new_state.state).lower()
        old_val = str(old_state.state).lower() if old_state is not None else ""
        if new_val not in ("on", "off") or new_val == old_val:
            return
        await self.async_evaluate()


def get_manager(hass: HomeAssistant) -> HvacFusionManager | None:
    """Retrieve the active HvacFusionManager instance."""
    data = hass.data.get(DOMAIN)
    if isinstance(data, HvacFusionManager):
        return data
    if isinstance(data, dict):
        if "manager" in data and isinstance(data["manager"], HvacFusionManager):
            return data["manager"]
        for val in data.values():
            if isinstance(val, HvacFusionManager):
                return val
    return None


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the HVAC Fusion integration from YAML configuration."""
    from .frontend_loader import async_register_frontend

    await async_register_frontend(hass)

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
        manager = get_manager(hass)
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
    async_register_services(hass)
    return True


def async_register_services(hass: HomeAssistant) -> None:
    """Register hvac_fusion integration services."""
    if not hass.services.has_service(DOMAIN, "acquire_schedule_lock"):

        async def handle_acquire_lock(call: ServiceCall) -> None:
            schedule_id = call.data.get("schedule_id", "")
            duration = int(call.data.get("duration", 300))
            if manager := get_manager(hass):
                manager.acquire_schedule_lock(schedule_id, duration)

        hass.services.async_register(
            DOMAIN,
            "acquire_schedule_lock",
            handle_acquire_lock,
        )

    if not hass.services.has_service(DOMAIN, "release_schedule_lock"):

        async def handle_release_lock(call: ServiceCall) -> None:
            schedule_id = call.data.get("schedule_id", "")
            if manager := get_manager(hass):
                manager.release_schedule_lock(schedule_id)

        hass.services.async_register(
            DOMAIN,
            "release_schedule_lock",
            handle_release_lock,
        )

    if not hass.services.has_service(DOMAIN, "comfort_boost"):

        async def handle_comfort_boost(call: ServiceCall) -> None:
            feeling = str(call.data.get("feeling", "too_cold")).lower()
            delta_f = float(call.data.get("delta_f", 2.0))
            duration_minutes = int(call.data.get("duration_minutes", 120))
            decay = bool(call.data.get("decay", True))

            target_entities = call.data.get("entity_id")
            if isinstance(target_entities, str):
                target_entities = [target_entities]
            elif target_entities is None:
                target_entities = []

            manager = get_manager(hass)
            if not manager:
                return

            for space_id, climate_entity in manager.space_entities.items():
                c_id = getattr(climate_entity, "entity_id", None)
                if (
                    not target_entities
                    or (c_id and c_id in target_entities)
                    or space_id in target_entities
                ):
                    await climate_entity.async_comfort_boost(
                        feeling=feeling,
                        delta_f=delta_f,
                        duration_minutes=duration_minutes,
                        decay=decay,
                    )

        hass.services.async_register(
            DOMAIN,
            "comfort_boost",
            handle_comfort_boost,
        )

    if not hass.services.has_service(DOMAIN, "clear_comfort_boost"):

        async def handle_clear_boost(call: ServiceCall) -> None:
            target_entities = call.data.get("entity_id")
            if isinstance(target_entities, str):
                target_entities = [target_entities]
            elif target_entities is None:
                target_entities = []

            manager = get_manager(hass)
            if not manager:
                return

            for space_id, climate_entity in manager.space_entities.items():
                c_id = getattr(climate_entity, "entity_id", None)
                if (
                    not target_entities
                    or (c_id and c_id in target_entities)
                    or space_id in target_entities
                ):
                    await climate_entity.async_clear_comfort_boost()

        hass.services.async_register(
            DOMAIN,
            "clear_comfort_boost",
            handle_clear_boost,
        )

    if not hass.services.has_service(DOMAIN, "register_space_preset"):

        async def handle_register_space_preset(call: ServiceCall) -> None:
            preset_name = str(call.data.get("preset_name", "")).strip()
            schedule_entity = str(call.data.get("schedule_entity", "")).strip()
            target_entities = call.data.get("entity_id")
            if isinstance(target_entities, str):
                target_entities = [target_entities]
            elif target_entities is None:
                target_entities = []

            manager = get_manager(hass)
            if not manager or not preset_name or not schedule_entity:
                return

            for target in target_entities:
                await manager.async_register_space_preset(
                    str(target), preset_name, schedule_entity
                )

        hass.services.async_register(
            DOMAIN,
            "register_space_preset",
            handle_register_space_preset,
        )

    if not hass.services.has_service(DOMAIN, "unregister_space_preset"):

        async def handle_unregister_space_preset(call: ServiceCall) -> None:
            preset_name = str(call.data.get("preset_name", "")).strip()
            target_entities = call.data.get("entity_id")
            if isinstance(target_entities, str):
                target_entities = [target_entities]
            elif target_entities is None:
                target_entities = []

            manager = get_manager(hass)
            if not manager or not preset_name:
                return

            for target in target_entities:
                await manager.async_unregister_space_preset(str(target), preset_name)

        hass.services.async_register(
            DOMAIN,
            "unregister_space_preset",
            handle_unregister_space_preset,
        )


async def async_setup_entry(
    hass: HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Set up HVAC Fusion from a config entry."""
    from .frontend_loader import async_register_frontend

    await async_register_frontend(hass)

    conf = dict(entry.data)
    conf.update(entry.options)

    manager = HvacFusionManager(hass, conf, entry_id=entry.entry_id)
    await manager.async_init()
    async_register_services(hass)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = manager
    hass.data[DOMAIN]["manager"] = manager

    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])

    if manager.topology and manager.topology.spaces:
        await hass.config_entries.async_forward_entry_setups(entry, [Platform.CLIMATE])

        # Replay any runtime-registered dynamic presets (e.g. from hvac_butler)
        # so in-place config reloads do not drop active companion presets.
        for target, presets in list(
            hass.data[DOMAIN].get("dynamic_presets", {}).items()
        ):
            for preset_name, schedule_entity in list(presets.items()):
                await manager.async_register_space_preset(
                    target, preset_name, schedule_entity
                )

    # Listen to schedule transitions
    if manager.schedule_entities:
        from homeassistant.helpers.event import async_track_state_change_event

        entry.async_on_unload(
            async_track_state_change_event(
                hass,
                list(manager.schedule_entities),
                manager.async_handle_schedule_change,
            )
        )

    # Listen to window/door sensor open/close transitions for immediate interlock response
    if manager.window_sensor_entities:
        from homeassistant.helpers.event import async_track_state_change_event

        entry.async_on_unload(
            async_track_state_change_event(
                hass,
                manager.window_sensor_entities,
                manager.async_handle_window_sensor_change,
            )
        )

    interval_minutes = conf.get(
        CONF_EVALUATION_INTERVAL_MINUTES, DEFAULT_EVALUATION_INTERVAL_MINUTES
    )
    entry.async_on_unload(
        async_track_time_interval(
            hass, manager.async_evaluate, timedelta(minutes=interval_minutes)
        )
    )

    async def _on_started(_event: Any) -> None:
        await manager.async_evaluate()

    if hass.is_running:
        await manager.async_evaluate()
    else:
        unsub = hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _on_started)

        def _cleanup_started_listener() -> None:
            try:
                unsub()
            except (ValueError, KeyError):
                pass

        entry.async_on_unload(_cleanup_started_listener)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Unload a config entry."""
    manager = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    unload_platforms = [Platform.SENSOR]
    if Platform.CLIMATE in getattr(entry, "loaded_platforms", set()) or (
        manager and manager.topology and manager.topology.spaces
    ):
        unload_platforms.append(Platform.CLIMATE)

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, unload_platforms
    )
    if unload_ok and DOMAIN in hass.data:
        if manager is not None:
            for unsub in getattr(manager, "_dynamic_schedule_unsubs", {}).values():
                unsub()
            if hasattr(manager, "_dynamic_schedule_unsubs"):
                manager._dynamic_schedule_unsubs.clear()
        hass.data[DOMAIN].pop(entry.entry_id, None)
        hass.data[DOMAIN].pop("manager", None)
    return unload_ok
