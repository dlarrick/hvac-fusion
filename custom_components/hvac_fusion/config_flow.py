"""Config flow for HVAC Fusion integration."""

from __future__ import annotations

import copy
import json
import logging
import os
import re
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_ENTITY_ID, CONF_ID, CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import Optional, section
from homeassistant.helpers import selector

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
    CONF_HAS_OUTDOOR_RESET,
    CONF_HEAT_PUMP_SAFETY_BAND_F,
    CONF_HYDRONIC_TYPE,
    CONF_NOMINAL_BTU,
    CONF_OFFSET,
    CONF_OIL_COST_PER_GAL,
    CONF_OIL_RATE_SENSOR,
    CONF_OUTDOOR_TEMPERATURE_ENTITY,
    CONF_PRESETS,
    CONF_PRIORITY,
    CONF_PRODUCER,
    CONF_PRODUCERS,
    CONF_PROFILE,
    CONF_PROPANE_COST_PER_GAL,
    CONF_PROPANE_RATE_SENSOR,
    CONF_SHARED_BOILER_ROLE,
    CONF_SOLAR_EXPORT_ENTITY,
    CONF_SPACES,
    CONF_TARIFFS,
    CONF_TEMP_SENSOR,
    CONF_TYPE,
    CONF_WINDOW_SENSOR,
    CONF_ZONE_ID,
    DEFAULT_CYCLING_BAND,
    DEFAULT_EVALUATION_INTERVAL_MINUTES,
    DEFAULT_HEAT_PUMP_SAFETY_BAND_F,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


_PROFILES_CACHE: list[dict[str, Any]] | None = None


def _scan_profiles_sync() -> list[dict[str, Any]]:
    """Scan and read profiles metadata from hvac_crossover."""
    profiles: list[dict[str, Any]] = []
    try:
        import hvac_crossover

        pkg_dir = os.path.dirname(hvac_crossover.__file__)
        pkg_profiles_dir = os.path.join(pkg_dir, "profiles", "producers")
        if os.path.isdir(pkg_profiles_dir):
            for root, _, files in os.walk(pkg_profiles_dir):
                for f in sorted(files):
                    if f.endswith(".json") and not f.endswith(".orig"):
                        full_path = os.path.join(root, f)
                        rel_path = os.path.relpath(full_path, pkg_profiles_dir)
                        try:
                            with open(full_path, encoding="utf-8") as fp:
                                data = json.load(fp)
                            raw_type = data.get("producer_type", "")
                            if "heat_pump" in raw_type:
                                category = "heat_pump"
                            elif raw_type in (
                                "modulating_boiler",
                                "atmospheric_boiler",
                                "steam_boiler",
                                "furnace",
                            ):
                                category = raw_type
                            else:
                                category = "boiler"
                            make = data.get("make")
                            model = data.get("model")
                            series = data.get("series")
                            btu = data.get("nominal_heating_btu") or data.get(
                                "nominal_cooling_btu"
                            )
                            fuel = data.get("fuel_type")
                            turndown = data.get("turndown_ratio")

                            parts = []
                            if make:
                                parts.append(make)
                            if model:
                                parts.append(model)
                            elif series:
                                parts.append(series)

                            label = " ".join(parts) if parts else rel_path
                            extra_info = []
                            if fuel:
                                extra_info.append(fuel.replace("_", " ").title())
                            if turndown:
                                extra_info.append(f"{turndown}:1 Turndown")
                            if btu:
                                extra_info.append(
                                    f"{int(btu) // 1000}k BTU"
                                    if int(btu) >= 1000
                                    else f"{btu} BTU"
                                )
                            if extra_info:
                                label += f" ({', '.join(extra_info)})"

                            profiles.append(
                                {
                                    "value": rel_path,
                                    "label": label,
                                    "category": category,
                                }
                            )
                        except (OSError, json.JSONDecodeError, KeyError, ValueError):
                            cat = "heat_pump" if "heat_pump" in rel_path else "boiler"
                            profiles.append(
                                {
                                    "value": rel_path,
                                    "label": rel_path,
                                    "category": cat,
                                }
                            )
    except OSError as err:
        _LOGGER.debug("Could not scan profiles: %s", err)
    return profiles


def _filter_profiles(
    raw_profiles: list[dict[str, Any]], category: str | None = None
) -> list[dict[str, str]]:
    """Filter scanned profiles by category and append tailored custom/none option."""
    if category == "heat_pump":
        res = [
            {"value": p["value"], "label": p["label"]}
            for p in raw_profiles
            if p.get("category") == "heat_pump"
        ]
        res.append({"value": "none", "label": "None / Custom Heat Pump"})
        return res
    if category == "modulating_boiler":
        res = [
            {"value": p["value"], "label": p["label"]}
            for p in raw_profiles
            if p.get("category") in ("modulating_boiler", "boiler")
        ]
        res.append({"value": "none", "label": "None / Custom Mod-Con Boiler"})
        return res
    if category == "atmospheric_boiler":
        res = [
            {"value": p["value"], "label": p["label"]}
            for p in raw_profiles
            if p.get("category") == "atmospheric_boiler"
        ]
        res.append({"value": "none", "label": "None / Custom Atmospheric Boiler"})
        return res
    if category == "steam_boiler":
        res = [
            {"value": p["value"], "label": p["label"]}
            for p in raw_profiles
            if p.get("category") in ("steam_boiler", "atmospheric_boiler")
        ]
        res.append({"value": "none", "label": "None / Custom Steam Boiler"})
        return res
    if category == "furnace":
        res = [
            {"value": p["value"], "label": p["label"]}
            for p in raw_profiles
            if p.get("category") == "furnace"
        ]
        res.append({"value": "none", "label": "None / Custom Warm-Air Furnace"})
        return res
    if category == "boiler":
        res = [
            {"value": p["value"], "label": p["label"]}
            for p in raw_profiles
            if p.get("category")
            in ("boiler", "modulating_boiler", "atmospheric_boiler", "steam_boiler")
        ]
        res.append({"value": "none", "label": "None / Custom Boiler"})
        return res

    res = [{"value": p["value"], "label": p["label"]} for p in raw_profiles]
    res.append({"value": "none", "label": "None / Custom Equipment"})
    return res


async def async_get_available_producer_profiles(
    hass: HomeAssistant,
    category: str | None = None,
) -> list[dict[str, str]]:
    """Asynchronously return available producer profile choices without blocking."""
    global _PROFILES_CACHE
    if _PROFILES_CACHE is None:
        _PROFILES_CACHE = await hass.async_add_executor_job(_scan_profiles_sync)
    return _filter_profiles(_PROFILES_CACHE, category)


def get_available_producer_profiles(
    category: str | None = None,
) -> list[dict[str, str]]:
    """Return available producer profile choices."""
    global _PROFILES_CACHE
    if _PROFILES_CACHE is None:
        _PROFILES_CACHE = _scan_profiles_sync()
    return _filter_profiles(_PROFILES_CACHE, category)


class HvacFusionConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HVAC Fusion."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return HvacFusionOptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial coordinator configuration step."""
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        errors: dict[str, str] = {}

        if user_input is not None:
            title = user_input.get(CONF_NAME, "HVAC Fusion")

            # Structure data for manager compatibility
            entry_data = {
                CONF_NAME: title,
                CONF_OUTDOOR_TEMPERATURE_ENTITY: user_input[
                    CONF_OUTDOOR_TEMPERATURE_ENTITY
                ],
                CONF_CONTROL_ENABLED: user_input.get(CONF_CONTROL_ENABLED, False),
                CONF_TARIFFS: {},
                CONF_PRODUCERS: {},
                CONF_SPACES: [],
            }
            if user_input.get(CONF_SOLAR_EXPORT_ENTITY):
                entry_data[CONF_SOLAR_EXPORT_ENTITY] = user_input[
                    CONF_SOLAR_EXPORT_ENTITY
                ]

            return self.async_create_entry(title=title, data=entry_data)

        schema = vol.Schema(
            {
                vol.Optional(CONF_NAME, default="HVAC Fusion"): str,
                vol.Required(CONF_OUTDOOR_TEMPERATURE_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_SOLAR_EXPORT_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(
                    CONF_CONTROL_ENABLED, default=False
                ): selector.BooleanSelector(),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)


class HvacFusionOptionsFlowHandler(config_entries.OptionsFlowWithReload):
    """Handle options flow for HVAC Fusion."""

    def __init__(self) -> None:
        """Initialize options flow."""
        self._working_options: dict[str, Any] | None = None
        self._selected_producer_id: str | None = None
        self._selected_space_id: str | None = None
        self._selected_emitter_idx: int | None = None
        self._selected_preset_name: str | None = None

    @property
    def _options(self) -> dict[str, Any]:
        """Return or lazily initialize working options copy."""
        if self._working_options is None:
            opts = copy.deepcopy(dict(self.config_entry.options))
            if not opts:
                opts = copy.deepcopy(dict(self.config_entry.data))
            opts.setdefault(CONF_TARIFFS, {})
            opts.setdefault(CONF_PRODUCERS, {})
            opts.setdefault(CONF_SPACES, [])
            self._working_options = opts
        return self._working_options

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show main options menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "global_settings",
                "producers_menu",
                "spaces_menu",
                "policies_menu",
                "finish",
            ],
        )

    async def async_step_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Save options and finish flow."""
        return self.async_create_entry(title="", data=self._options)

    async def async_step_global_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure environmental sensors."""
        if user_input is not None:
            env_sec = user_input.get("environment_section") or user_input

            self._options[CONF_OUTDOOR_TEMPERATURE_ENTITY] = env_sec[
                CONF_OUTDOOR_TEMPERATURE_ENTITY
            ]
            if env_sec.get(CONF_SOLAR_EXPORT_ENTITY):
                self._options[CONF_SOLAR_EXPORT_ENTITY] = env_sec[
                    CONF_SOLAR_EXPORT_ENTITY
                ]
            else:
                self._options.pop(CONF_SOLAR_EXPORT_ENTITY, None)

            return await self.async_step_init()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_OUTDOOR_TEMPERATURE_ENTITY,
                    default=self._options.get(CONF_OUTDOOR_TEMPERATURE_ENTITY, ""),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(
                    CONF_SOLAR_EXPORT_ENTITY,
                    description={
                        "suggested_value": self._options.get(CONF_SOLAR_EXPORT_ENTITY)
                    },
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
            }
        )
        return self.async_show_form(step_id="global_settings", data_schema=schema)

    async def async_step_policies_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure tariffs, safety limits, and operational policies."""
        if user_input is not None:
            elec_sec = user_input.get("electricity_section") or user_input
            gas_sec = user_input.get("gas_section") or user_input
            propane_sec = user_input.get("propane_section") or user_input
            oil_sec = user_input.get("oil_section") or user_input
            limits_sec = user_input.get("limits_section") or user_input
            pol_sec = user_input.get("policies_section") or user_input

            tariffs = self._options.setdefault(CONF_TARIFFS, {})
            if CONF_ELECTRIC_COST_PER_KWH in elec_sec:
                if elec_sec[CONF_ELECTRIC_COST_PER_KWH] is not None:
                    tariffs[CONF_ELECTRIC_COST_PER_KWH] = float(
                        elec_sec[CONF_ELECTRIC_COST_PER_KWH]
                    )
                else:
                    tariffs.pop(CONF_ELECTRIC_COST_PER_KWH, None)
            if CONF_ELECTRIC_RATE_SENSOR in elec_sec:
                if elec_sec[CONF_ELECTRIC_RATE_SENSOR]:
                    tariffs[CONF_ELECTRIC_RATE_SENSOR] = elec_sec[
                        CONF_ELECTRIC_RATE_SENSOR
                    ]
                else:
                    tariffs.pop(CONF_ELECTRIC_RATE_SENSOR, None)

            if CONF_GAS_COST_PER_THERM in gas_sec:
                if gas_sec[CONF_GAS_COST_PER_THERM] is not None:
                    tariffs[CONF_GAS_COST_PER_THERM] = float(
                        gas_sec[CONF_GAS_COST_PER_THERM]
                    )
                else:
                    tariffs.pop(CONF_GAS_COST_PER_THERM, None)
            if CONF_GAS_RATE_SENSOR in gas_sec:
                if gas_sec[CONF_GAS_RATE_SENSOR]:
                    tariffs[CONF_GAS_RATE_SENSOR] = gas_sec[CONF_GAS_RATE_SENSOR]
                else:
                    tariffs.pop(CONF_GAS_RATE_SENSOR, None)

            if CONF_PROPANE_COST_PER_GAL in propane_sec:
                if propane_sec[CONF_PROPANE_COST_PER_GAL] is not None:
                    tariffs[CONF_PROPANE_COST_PER_GAL] = float(
                        propane_sec[CONF_PROPANE_COST_PER_GAL]
                    )
                else:
                    tariffs.pop(CONF_PROPANE_COST_PER_GAL, None)
            if CONF_PROPANE_RATE_SENSOR in propane_sec:
                if propane_sec[CONF_PROPANE_RATE_SENSOR]:
                    tariffs[CONF_PROPANE_RATE_SENSOR] = propane_sec[
                        CONF_PROPANE_RATE_SENSOR
                    ]
                else:
                    tariffs.pop(CONF_PROPANE_RATE_SENSOR, None)

            if CONF_OIL_COST_PER_GAL in oil_sec:
                if oil_sec[CONF_OIL_COST_PER_GAL] is not None:
                    tariffs[CONF_OIL_COST_PER_GAL] = float(
                        oil_sec[CONF_OIL_COST_PER_GAL]
                    )
                else:
                    tariffs.pop(CONF_OIL_COST_PER_GAL, None)
            if CONF_OIL_RATE_SENSOR in oil_sec:
                if oil_sec[CONF_OIL_RATE_SENSOR]:
                    tariffs[CONF_OIL_RATE_SENSOR] = oil_sec[CONF_OIL_RATE_SENSOR]
                else:
                    tariffs.pop(CONF_OIL_RATE_SENSOR, None)

            if CONF_HEAT_PUMP_SAFETY_BAND_F in limits_sec:
                self._options[CONF_HEAT_PUMP_SAFETY_BAND_F] = float(
                    limits_sec[CONF_HEAT_PUMP_SAFETY_BAND_F]
                )

            if CONF_CONTROL_ENABLED in pol_sec:
                self._options[CONF_CONTROL_ENABLED] = pol_sec[CONF_CONTROL_ENABLED]
            if CONF_CYCLING_BAND in pol_sec:
                self._options[CONF_CYCLING_BAND] = float(pol_sec[CONF_CYCLING_BAND])
            if CONF_EVALUATION_INTERVAL_MINUTES in pol_sec:
                self._options[CONF_EVALUATION_INTERVAL_MINUTES] = int(
                    pol_sec[CONF_EVALUATION_INTERVAL_MINUTES]
                )

            return await self.async_step_init()

        producers = self._options.get(CONF_PRODUCERS, {})
        has_heat_pumps = any(
            p.get(CONF_TYPE) in ("heat_pump", "inverter_heat_pump")
            for p in producers.values()
        )
        fossil_types = (
            "boiler",
            "modulating_boiler",
            "atmospheric_boiler",
            "steam_boiler",
            "furnace",
        )
        has_gas = any(
            p.get(CONF_TYPE) in fossil_types
            and p.get(CONF_FUEL_TYPE, "natural_gas") in ("natural_gas", "ng")
            for p in producers.values()
        )
        has_propane = any(
            p.get(CONF_TYPE) in fossil_types
            and p.get(CONF_FUEL_TYPE) in ("propane", "lp")
            for p in producers.values()
        )
        has_oil = any(
            p.get(CONF_TYPE) in fossil_types
            and p.get(CONF_FUEL_TYPE) in ("oil", "fuel_oil", "oil_no2")
            for p in producers.values()
        )

        tariffs = self._options.get(CONF_TARIFFS, {})
        schema_dict: dict[Any, Any] = {}

        if has_heat_pumps or not producers:
            schema_dict[vol.Optional("electricity_section")] = section(
                vol.Schema(
                    {
                        vol.Optional(
                            CONF_ELECTRIC_COST_PER_KWH,
                            description={
                                "suggested_value": tariffs.get(
                                    CONF_ELECTRIC_COST_PER_KWH
                                )
                            },
                        ): selector.NumberSelector(
                            selector.NumberSelectorConfig(
                                min=0.0,
                                max=2.0,
                                step="any",
                                mode=selector.NumberSelectorMode.BOX,
                            )
                        ),
                        vol.Optional(
                            CONF_ELECTRIC_RATE_SENSOR,
                            description={
                                "suggested_value": tariffs.get(
                                    CONF_ELECTRIC_RATE_SENSOR
                                )
                            },
                        ): selector.EntitySelector(
                            selector.EntitySelectorConfig(
                                domain=["sensor", "input_number", "number"]
                            )
                        ),
                    }
                )
            )

        if has_gas or not producers:
            schema_dict[vol.Optional("gas_section")] = section(
                vol.Schema(
                    {
                        vol.Optional(
                            CONF_GAS_COST_PER_THERM,
                            description={
                                "suggested_value": tariffs.get(CONF_GAS_COST_PER_THERM)
                            },
                        ): selector.NumberSelector(
                            selector.NumberSelectorConfig(
                                min=0.0,
                                max=10.0,
                                step="any",
                                mode=selector.NumberSelectorMode.BOX,
                            )
                        ),
                        vol.Optional(
                            CONF_GAS_RATE_SENSOR,
                            description={
                                "suggested_value": tariffs.get(CONF_GAS_RATE_SENSOR)
                            },
                        ): selector.EntitySelector(
                            selector.EntitySelectorConfig(
                                domain=["sensor", "input_number", "number"]
                            )
                        ),
                    }
                )
            )

        if has_propane:
            schema_dict[vol.Optional("propane_section")] = section(
                vol.Schema(
                    {
                        vol.Optional(
                            CONF_PROPANE_COST_PER_GAL,
                            description={
                                "suggested_value": tariffs.get(
                                    CONF_PROPANE_COST_PER_GAL
                                )
                            },
                        ): selector.NumberSelector(
                            selector.NumberSelectorConfig(
                                min=0.0,
                                max=15.0,
                                step="any",
                                mode=selector.NumberSelectorMode.BOX,
                            )
                        ),
                        vol.Optional(
                            CONF_PROPANE_RATE_SENSOR,
                            description={
                                "suggested_value": tariffs.get(CONF_PROPANE_RATE_SENSOR)
                            },
                        ): selector.EntitySelector(
                            selector.EntitySelectorConfig(
                                domain=["sensor", "input_number", "number"]
                            )
                        ),
                    }
                )
            )

        if has_oil:
            schema_dict[vol.Optional("oil_section")] = section(
                vol.Schema(
                    {
                        vol.Optional(
                            CONF_OIL_COST_PER_GAL,
                            description={
                                "suggested_value": tariffs.get(CONF_OIL_COST_PER_GAL)
                            },
                        ): selector.NumberSelector(
                            selector.NumberSelectorConfig(
                                min=0.0,
                                max=15.0,
                                step="any",
                                mode=selector.NumberSelectorMode.BOX,
                            )
                        ),
                        vol.Optional(
                            CONF_OIL_RATE_SENSOR,
                            description={
                                "suggested_value": tariffs.get(CONF_OIL_RATE_SENSOR)
                            },
                        ): selector.EntitySelector(
                            selector.EntitySelectorConfig(
                                domain=["sensor", "input_number", "number"]
                            )
                        ),
                    }
                )
            )

        if has_heat_pumps:
            schema_dict[vol.Optional("limits_section")] = section(
                vol.Schema(
                    {
                        vol.Optional(
                            CONF_HEAT_PUMP_SAFETY_BAND_F,
                            default=self._options.get(
                                CONF_HEAT_PUMP_SAFETY_BAND_F,
                                DEFAULT_HEAT_PUMP_SAFETY_BAND_F,
                            ),
                        ): selector.NumberSelector(
                            selector.NumberSelectorConfig(
                                min=0.0,
                                max=20.0,
                                step=0.5,
                                mode=selector.NumberSelectorMode.BOX,
                            )
                        ),
                    }
                )
            )

        schema_dict[vol.Optional("policies_section")] = section(
            vol.Schema(
                {
                    vol.Optional(
                        CONF_CONTROL_ENABLED,
                        default=self._options.get(CONF_CONTROL_ENABLED, False),
                    ): selector.BooleanSelector(),
                    vol.Optional(
                        CONF_CYCLING_BAND,
                        default=self._options.get(
                            CONF_CYCLING_BAND, DEFAULT_CYCLING_BAND
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0.5,
                            max=10.0,
                            step=0.5,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional(
                        CONF_EVALUATION_INTERVAL_MINUTES,
                        default=self._options.get(
                            CONF_EVALUATION_INTERVAL_MINUTES,
                            DEFAULT_EVALUATION_INTERVAL_MINUTES,
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1,
                            max=60,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                }
            )
        )

        return self.async_show_form(
            step_id="policies_menu", data_schema=vol.Schema(schema_dict)
        )

    async def async_step_producers_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show producers list or action menu."""
        if user_input is not None:
            choice = user_input["producer_action"]
            if choice == "add":
                return await self.async_step_producer_add()
            if choice == "back":
                return await self.async_step_init()
            self._selected_producer_id = choice
            return await self.async_step_producer_edit()

        producers = self._options.setdefault(CONF_PRODUCERS, {})
        options = [{"value": "add", "label": "+ Add a new producer"}]
        for p_id, p_conf in producers.items():
            p_name = p_conf.get(CONF_NAME, p_id)
            options.append({"value": p_id, "label": f"{p_name} ({p_id})"})
        options.append({"value": "back", "label": "Back to Main Menu"})

        schema = vol.Schema(
            {
                vol.Required("producer_action", default="add"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                )
            }
        )
        return self.async_show_form(step_id="producers_menu", data_schema=schema)

    async def async_step_producer_manage(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Redirect directly to producer edit."""
        return await self.async_step_producer_edit(user_input)

    async def async_step_producer_add(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Add a new producer."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input.get("cancel"):
                return await self.async_step_producers_menu()

            name = (
                user_input.get(CONF_NAME, "").strip()
                if user_input.get(CONF_NAME)
                else ""
            )
            if not name:
                errors[CONF_NAME] = "name_required"
            else:
                raw_id = (
                    user_input.get(CONF_ID, "").strip()
                    if user_input.get(CONF_ID)
                    else ""
                )
                if raw_id:
                    p_id = re.sub(r"[^a-z0-9_]+", "_", raw_id.lower()).strip("_")
                else:
                    base_slug = re.sub(r"[^a-z0-9_]+", "_", name.lower()).strip("_")
                    if not base_slug:
                        base_slug = "producer"
                    p_id = base_slug
                    counter = 2
                    while p_id in self._options.get(CONF_PRODUCERS, {}):
                        p_id = f"{base_slug}_{counter}"
                        counter += 1

                if raw_id and p_id in self._options.get(CONF_PRODUCERS, {}):
                    errors["base"] = "producer_id_exists"
                else:
                    p_type = user_input.get(CONF_TYPE, "heat_pump")
                    if p_type in ("heat_pump", "inverter_heat_pump"):
                        profile = user_input.get("heat_pump_profile") or user_input.get(
                            CONF_PROFILE
                        )
                    elif p_type in ("boiler", "modulating_boiler"):
                        profile = (
                            user_input.get("modulating_boiler_profile")
                            or user_input.get("boiler_profile")
                            or user_input.get(CONF_PROFILE)
                        )
                    elif p_type == "atmospheric_boiler":
                        profile = user_input.get(
                            "atmospheric_boiler_profile"
                        ) or user_input.get(CONF_PROFILE)
                    elif p_type == "steam_boiler":
                        profile = user_input.get(
                            "steam_boiler_profile"
                        ) or user_input.get(CONF_PROFILE)
                    elif p_type == "furnace":
                        profile = user_input.get("furnace_profile") or user_input.get(
                            CONF_PROFILE
                        )
                    else:
                        profile = user_input.get(CONF_PROFILE)

                    if profile == "none":
                        profile = None

                    producer_entry = {
                        CONF_NAME: name,
                        CONF_TYPE: p_type,
                        CONF_PROFILE: profile,
                    }
                    if user_input.get(CONF_NOMINAL_BTU):
                        producer_entry[CONF_NOMINAL_BTU] = float(
                            user_input[CONF_NOMINAL_BTU]
                        )
                    if p_type in (
                        "boiler",
                        "modulating_boiler",
                        "atmospheric_boiler",
                        "steam_boiler",
                        "furnace",
                    ):
                        producer_entry[CONF_FUEL_TYPE] = user_input.get(
                            CONF_FUEL_TYPE, "natural_gas"
                        )
                    if p_type in ("boiler", "modulating_boiler"):
                        producer_entry[CONF_HAS_OUTDOOR_RESET] = bool(
                            user_input.get(CONF_HAS_OUTDOOR_RESET, False)
                        )
                    self._options.setdefault(CONF_PRODUCERS, {})[p_id] = producer_entry
                    return await self.async_step_producers_menu()

        hp_profiles = await async_get_available_producer_profiles(
            self.hass, category="heat_pump"
        )
        mod_con_profiles = await async_get_available_producer_profiles(
            self.hass, category="modulating_boiler"
        )
        atmos_profiles = await async_get_available_producer_profiles(
            self.hass, category="atmospheric_boiler"
        )
        steam_profiles = await async_get_available_producer_profiles(
            self.hass, category="steam_boiler"
        )
        furnace_profiles = await async_get_available_producer_profiles(
            self.hass, category="furnace"
        )

        hp_default = "generic/cold_climate_heat_pump.json"
        if not any(p["value"] == hp_default for p in hp_profiles):
            hp_default = hp_profiles[0]["value"] if hp_profiles else "none"

        mod_con_default = "generic/modulating_condensing_boiler.json"
        if not any(p["value"] == mod_con_default for p in mod_con_profiles):
            mod_con_default = (
                mod_con_profiles[0]["value"] if mod_con_profiles else "none"
            )

        atmos_default = "generic/atmospheric_cast_iron_boiler_gas.json"
        if not any(p["value"] == atmos_default for p in atmos_profiles):
            atmos_default = atmos_profiles[0]["value"] if atmos_profiles else "none"

        steam_default = "generic/steam_boiler_gas.json"
        if not any(p["value"] == steam_default for p in steam_profiles):
            steam_default = steam_profiles[0]["value"] if steam_profiles else "none"

        furnace_default = "generic/furnace_gas_standard.json"
        if not any(p["value"] == furnace_default for p in furnace_profiles):
            furnace_default = (
                furnace_profiles[0]["value"] if furnace_profiles else "none"
            )

        prod_type_options = [
            {"value": "heat_pump", "label": "Heat Pump / Mini-Split"},
            {"value": "modulating_boiler", "label": "Modulating Condensing Boiler"},
            {
                "value": "atmospheric_boiler",
                "label": "Standard Atmospheric Boiler (Cast Iron)",
            },
            {"value": "steam_boiler", "label": "Steam Boiler"},
            {"value": "furnace", "label": "Warm-Air Furnace"},
        ]

        fuel_options = [
            {"value": "natural_gas", "label": "Natural Gas"},
            {"value": "propane", "label": "Propane"},
            {"value": "oil", "label": "Heating Oil (#2)"},
        ]

        schema = vol.Schema(
            {
                vol.Optional(CONF_NAME): str,
                vol.Optional(CONF_ID): str,
                vol.Optional(CONF_TYPE, default="heat_pump"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=prod_type_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                Optional(
                    "heat_pump_profile",
                    default=hp_default,
                    visible={"field": CONF_TYPE, "value": "heat_pump"},
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=hp_profiles,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                Optional(
                    "modulating_boiler_profile",
                    default=mod_con_default,
                    visible={"field": CONF_TYPE, "value": "modulating_boiler"},
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=mod_con_profiles,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                Optional(
                    "atmospheric_boiler_profile",
                    default=atmos_default,
                    visible={"field": CONF_TYPE, "value": "atmospheric_boiler"},
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=atmos_profiles,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                Optional(
                    "steam_boiler_profile",
                    default=steam_default,
                    visible={"field": CONF_TYPE, "value": "steam_boiler"},
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=steam_profiles,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                Optional(
                    "furnace_profile",
                    default=furnace_default,
                    visible={"field": CONF_TYPE, "value": "furnace"},
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=furnace_profiles,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                Optional(
                    CONF_FUEL_TYPE,
                    default="natural_gas",
                    visible={
                        "field": CONF_TYPE,
                        "operator": "not_eq",
                        "value": "heat_pump",
                    },
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=fuel_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                Optional(
                    CONF_NOMINAL_BTU,
                    default=24000.0,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=6000.0,
                        max=500000.0,
                        step=1000.0,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                Optional(
                    CONF_HAS_OUTDOOR_RESET,
                    default=False,
                    visible={"field": CONF_TYPE, "value": "modulating_boiler"},
                ): selector.BooleanSelector(),
                vol.Optional("cancel", default=False): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(
            step_id="producer_add", data_schema=schema, errors=errors
        )

    async def async_step_producer_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Edit an existing producer."""
        p_id = self._selected_producer_id or ""
        p_conf = self._options.get(CONF_PRODUCERS, {}).get(p_id, {})

        if user_input is not None:
            if user_input.get("cancel"):
                return await self.async_step_producers_menu()

            if user_input.get("delete_producer"):
                self._options.get(CONF_PRODUCERS, {}).pop(p_id, None)
                for sp in self._options.get(CONF_SPACES, []):
                    sp[CONF_EMITTERS] = [
                        e
                        for e in sp.get(CONF_EMITTERS, [])
                        if e.get(CONF_PRODUCER) != p_id
                    ]
                return await self.async_step_producers_menu()

            p_type = user_input[CONF_TYPE]
            if p_type in ("heat_pump", "inverter_heat_pump"):
                profile = user_input.get("heat_pump_profile") or user_input.get(
                    CONF_PROFILE
                )
            elif p_type in ("boiler", "modulating_boiler"):
                profile = (
                    user_input.get("modulating_boiler_profile")
                    or user_input.get("boiler_profile")
                    or user_input.get(CONF_PROFILE)
                )
            elif p_type == "atmospheric_boiler":
                profile = user_input.get(
                    "atmospheric_boiler_profile"
                ) or user_input.get(CONF_PROFILE)
            elif p_type == "steam_boiler":
                profile = user_input.get("steam_boiler_profile") or user_input.get(
                    CONF_PROFILE
                )
            elif p_type == "furnace":
                profile = user_input.get("furnace_profile") or user_input.get(
                    CONF_PROFILE
                )
            else:
                profile = user_input.get(CONF_PROFILE)

            if profile == "none":
                profile = None

            p_conf[CONF_NAME] = user_input.get(CONF_NAME, p_id)
            p_conf[CONF_TYPE] = p_type
            p_conf[CONF_PROFILE] = profile
            if user_input.get(CONF_NOMINAL_BTU):
                p_conf[CONF_NOMINAL_BTU] = float(user_input[CONF_NOMINAL_BTU])

            if p_type in (
                "boiler",
                "modulating_boiler",
                "atmospheric_boiler",
                "steam_boiler",
                "furnace",
            ):
                p_conf[CONF_FUEL_TYPE] = user_input.get(CONF_FUEL_TYPE, "natural_gas")
            else:
                p_conf.pop(CONF_FUEL_TYPE, None)

            if p_type in ("boiler", "modulating_boiler"):
                p_conf[CONF_HAS_OUTDOOR_RESET] = bool(
                    user_input.get(CONF_HAS_OUTDOOR_RESET, False)
                )
            else:
                p_conf.pop(CONF_HAS_OUTDOOR_RESET, None)

            return await self.async_step_producers_menu()

        hp_profiles = await async_get_available_producer_profiles(
            self.hass, category="heat_pump"
        )
        mod_con_profiles = await async_get_available_producer_profiles(
            self.hass, category="modulating_boiler"
        )
        atmos_profiles = await async_get_available_producer_profiles(
            self.hass, category="atmospheric_boiler"
        )
        steam_profiles = await async_get_available_producer_profiles(
            self.hass, category="steam_boiler"
        )
        furnace_profiles = await async_get_available_producer_profiles(
            self.hass, category="furnace"
        )

        raw_type = p_conf.get(CONF_TYPE, "heat_pump")
        if raw_type in ("heat_pump", "inverter_heat_pump"):
            norm_type = "heat_pump"
        elif raw_type in ("boiler", "modulating_boiler"):
            norm_type = "modulating_boiler"
        elif raw_type in ("atmospheric_boiler", "steam_boiler", "furnace"):
            norm_type = raw_type
        else:
            norm_type = "modulating_boiler"

        current_profile = p_conf.get(CONF_PROFILE) or "none"

        hp_default = "generic/cold_climate_heat_pump.json"
        hp_selected = (
            current_profile
            if any(p["value"] == current_profile for p in hp_profiles)
            else (
                hp_default
                if any(p["value"] == hp_default for p in hp_profiles)
                else (hp_profiles[0]["value"] if hp_profiles else "none")
            )
        )

        mod_con_default = "generic/modulating_condensing_boiler.json"
        mod_con_selected = (
            current_profile
            if any(p["value"] == current_profile for p in mod_con_profiles)
            else (
                mod_con_default
                if any(p["value"] == mod_con_default for p in mod_con_profiles)
                else (mod_con_profiles[0]["value"] if mod_con_profiles else "none")
            )
        )

        atmos_default = "generic/atmospheric_cast_iron_boiler_gas.json"
        atmos_selected = (
            current_profile
            if any(p["value"] == current_profile for p in atmos_profiles)
            else (
                atmos_default
                if any(p["value"] == atmos_default for p in atmos_profiles)
                else (atmos_profiles[0]["value"] if atmos_profiles else "none")
            )
        )

        steam_default = "generic/steam_boiler_gas.json"
        steam_selected = (
            current_profile
            if any(p["value"] == current_profile for p in steam_profiles)
            else (
                steam_default
                if any(p["value"] == steam_default for p in steam_profiles)
                else (steam_profiles[0]["value"] if steam_profiles else "none")
            )
        )

        furnace_default = "generic/furnace_gas_standard.json"
        furnace_selected = (
            current_profile
            if any(p["value"] == current_profile for p in furnace_profiles)
            else (
                furnace_default
                if any(p["value"] == furnace_default for p in furnace_profiles)
                else (furnace_profiles[0]["value"] if furnace_profiles else "none")
            )
        )

        prod_type_options = [
            {"value": "heat_pump", "label": "Heat Pump / Mini-Split"},
            {"value": "modulating_boiler", "label": "Modulating Condensing Boiler"},
            {
                "value": "atmospheric_boiler",
                "label": "Standard Atmospheric Boiler (Cast Iron)",
            },
            {"value": "steam_boiler", "label": "Steam Boiler"},
            {"value": "furnace", "label": "Warm-Air Furnace"},
        ]

        fuel_options = [
            {"value": "natural_gas", "label": "Natural Gas"},
            {"value": "propane", "label": "Propane"},
            {"value": "oil", "label": "Heating Oil (#2)"},
        ]

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=p_conf.get(CONF_NAME, p_id)): str,
                vol.Required(CONF_TYPE, default=norm_type): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=prod_type_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                Optional(
                    "heat_pump_profile",
                    default=hp_selected,
                    visible={"field": CONF_TYPE, "value": "heat_pump"},
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=hp_profiles,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                Optional(
                    "modulating_boiler_profile",
                    default=mod_con_selected,
                    visible={"field": CONF_TYPE, "value": "modulating_boiler"},
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=mod_con_profiles,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                Optional(
                    "atmospheric_boiler_profile",
                    default=atmos_selected,
                    visible={"field": CONF_TYPE, "value": "atmospheric_boiler"},
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=atmos_profiles,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                Optional(
                    "steam_boiler_profile",
                    default=steam_selected,
                    visible={"field": CONF_TYPE, "value": "steam_boiler"},
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=steam_profiles,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                Optional(
                    "furnace_profile",
                    default=furnace_selected,
                    visible={"field": CONF_TYPE, "value": "furnace"},
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=furnace_profiles,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                Optional(
                    CONF_FUEL_TYPE,
                    default=p_conf.get(CONF_FUEL_TYPE, "natural_gas"),
                    visible={
                        "field": CONF_TYPE,
                        "operator": "not_eq",
                        "value": "heat_pump",
                    },
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=fuel_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                Optional(
                    CONF_NOMINAL_BTU,
                    default=p_conf.get(
                        CONF_NOMINAL_BTU,
                        24000.0
                        if norm_type in ("heat_pump", "inverter_heat_pump")
                        else 100000.0,
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=6000.0,
                        max=500000.0,
                        step=1000.0,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                Optional(
                    CONF_HAS_OUTDOOR_RESET,
                    default=p_conf.get(CONF_HAS_OUTDOOR_RESET, False),
                    visible={"field": CONF_TYPE, "value": "modulating_boiler"},
                ): selector.BooleanSelector(),
                vol.Optional("cancel", default=False): selector.BooleanSelector(),
                vol.Optional(
                    "delete_producer", default=False
                ): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(
            step_id="producer_edit",
            data_schema=schema,
            description_placeholders={"producer_name": p_conf.get(CONF_NAME, p_id)},
        )

    async def async_step_producer_delete(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Redirect delete to producer edit."""
        return await self.async_step_producer_edit(user_input)

    async def async_step_spaces_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show spaces list or action menu."""
        if user_input is not None:
            choice = user_input["space_action"]
            if choice == "add":
                return await self.async_step_space_add()
            if choice == "back":
                return await self.async_step_init()
            self._selected_space_id = choice
            return await self.async_step_space_manage()

        spaces = self._options.setdefault(CONF_SPACES, [])
        options = [{"value": "add", "label": "+ Add a new space"}]
        for s in spaces:
            s_id = s.get(CONF_ID, "")
            s_name = s.get(CONF_NAME, s_id)
            options.append({"value": s_id, "label": f"{s_name} ({s_id})"})
        options.append({"value": "back", "label": "Back to Main Menu"})

        schema = vol.Schema(
            {
                vol.Required("space_action", default="add"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                )
            }
        )
        return self.async_show_form(step_id="spaces_menu", data_schema=schema)

    async def async_step_space_manage(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage selected space."""
        if user_input is not None:
            act = user_input["action"]
            if act == "edit":
                return await self.async_step_space_edit()
            if act == "presets":
                return await self.async_step_presets_menu()
            if act == "emitters":
                return await self.async_step_emitters_menu()
            if act == "delete":
                return await self.async_step_space_delete()
            return await self.async_step_spaces_menu()

        s_id = self._selected_space_id or ""
        space = next(
            (s for s in self._options.get(CONF_SPACES, []) if s.get(CONF_ID) == s_id),
            {},
        )
        s_name = space.get(CONF_NAME, s_id)

        schema = vol.Schema(
            {
                vol.Required("action", default="edit"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "edit", "label": f"Edit {s_name} Settings"},
                            {
                                "value": "presets",
                                "label": f"Manage Schedule Presets ({len(space.get(CONF_PRESETS, {}))})",
                            },
                            {
                                "value": "emitters",
                                "label": f"Manage Emitters ({len(space.get(CONF_EMITTERS, []))})",
                            },
                            {"value": "delete", "label": f"Delete {s_name}"},
                            {"value": "back", "label": "Back to Spaces List"},
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                    )
                )
            }
        )
        return self.async_show_form(
            step_id="space_manage",
            data_schema=schema,
            description_placeholders={"space_name": s_name},
        )

    async def async_step_space_add(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Add a new space."""
        errors: dict[str, str] = {}
        producers = self._options.get(CONF_PRODUCERS, {})
        has_boilers = any(
            p.get(CONF_TYPE) in ("boiler", "modulating_boiler")
            for p in producers.values()
        )

        if user_input is not None:
            if user_input.get("cancel"):
                return await self.async_step_spaces_menu()

            name = (
                user_input.get(CONF_NAME, "").strip()
                if user_input.get(CONF_NAME)
                else ""
            )
            temp_sensor = user_input.get(CONF_TEMP_SENSOR)
            if not name:
                errors[CONF_NAME] = "name_required"
            if not temp_sensor:
                errors[CONF_TEMP_SENSOR] = "temp_sensor_required"

            if not errors:
                raw_id = (
                    user_input.get(CONF_ID, "").strip()
                    if user_input.get(CONF_ID)
                    else ""
                )
                if raw_id:
                    s_id = re.sub(r"[^a-z0-9_]+", "_", raw_id.lower()).strip("_")
                else:
                    base_slug = re.sub(r"[^a-z0-9_]+", "_", name.lower()).strip("_")
                    if not base_slug:
                        base_slug = "space"
                    s_id = base_slug
                    existing_ids = [
                        s.get(CONF_ID) for s in self._options.get(CONF_SPACES, [])
                    ]
                    counter = 2
                    while s_id in existing_ids:
                        s_id = f"{base_slug}_{counter}"
                        counter += 1

                existing_ids = [
                    s.get(CONF_ID) for s in self._options.get(CONF_SPACES, [])
                ]
                if raw_id and s_id in existing_ids:
                    errors["base"] = "space_id_exists"
                else:
                    emitters = []
                    if user_input.get("configure_primary_emitter"):
                        emitter_entity = user_input.get("emitter_entity_id")
                        emitter_type = user_input.get("emitter_type", "mini_split")
                        if emitter_type == "mini_split":
                            emitter_prod = user_input.get(
                                "hp_emitter_producer"
                            ) or user_input.get("emitter_producer")
                        else:
                            emitter_prod = user_input.get(
                                "boiler_emitter_producer"
                            ) or user_input.get("emitter_producer")

                        if emitter_entity and emitter_prod:
                            emitter_entry = {
                                CONF_TYPE: emitter_type,
                                CONF_PRODUCER: emitter_prod,
                                CONF_ENTITY_ID: emitter_entity,
                                CONF_OFFSET: 0.0,
                            }
                            if emitter_type == "mini_split":
                                emitter_entry[CONF_NOMINAL_BTU] = float(
                                    user_input.get("emitter_nominal_btu", 12000.0)
                                )
                            elif emitter_type == "hydronic":
                                emitter_entry[CONF_ZONE_ID] = user_input.get(
                                    "emitter_zone_id", "z1"
                                )
                            emitters.append(emitter_entry)

                    space_entry = {
                        CONF_ID: s_id,
                        CONF_NAME: name,
                        CONF_TEMP_SENSOR: temp_sensor,
                        CONF_FLOOR_AREA: float(user_input.get(CONF_FLOOR_AREA, 300.0)),
                        CONF_CEILING_HEIGHT: float(
                            user_input.get(CONF_CEILING_HEIGHT, 8.0)
                        ),
                        CONF_PRIORITY: int(user_input.get(CONF_PRIORITY, 5)),
                        CONF_SHARED_BOILER_ROLE: user_input.get(
                            CONF_SHARED_BOILER_ROLE, "independent"
                        ),
                        CONF_PRESETS: {},
                        CONF_EMITTERS: emitters,
                    }
                    if user_input.get(CONF_WINDOW_SENSOR):
                        space_entry[CONF_WINDOW_SENSOR] = user_input[CONF_WINDOW_SENSOR]

                    self._options.setdefault(CONF_SPACES, []).append(space_entry)
                    self._selected_space_id = s_id
                    return await self.async_step_space_manage()

        schema_dict: dict[Any, Any] = {
            vol.Optional(CONF_NAME): str,
            vol.Optional(CONF_ID): str,
            vol.Optional(CONF_TEMP_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_FLOOR_AREA, default=300.0): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=10.0,
                    max=10000.0,
                    step=10.0,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(CONF_CEILING_HEIGHT, default=8.0): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=5.0,
                    max=30.0,
                    step=0.5,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(CONF_PRIORITY, default=5): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=10, step=1, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Optional(CONF_WINDOW_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="binary_sensor")
            ),
            Optional(
                CONF_SHARED_BOILER_ROLE,
                default="independent",
                visible=has_boilers,
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {
                            "value": "independent",
                            "label": "Independent (Dedicated or non-shared zone)",
                        },
                        {
                            "value": "primary",
                            "label": "Primary (Drives the shared boiler loop)",
                        },
                        {
                            "value": "secondary",
                            "label": "Secondary (Passively follows shared boiler loop)",
                        },
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        }

        if producers:
            schema_dict[vol.Optional("configure_primary_emitter", default=False)] = (
                selector.BooleanSelector()
            )

            hp_options = [
                {"value": p_id, "label": f"{p_conf.get(CONF_NAME, p_id)} ({p_id})"}
                for p_id, p_conf in producers.items()
                if p_conf.get(CONF_TYPE) in ("heat_pump", "inverter_heat_pump")
            ]
            boiler_options = [
                {"value": p_id, "label": f"{p_conf.get(CONF_NAME, p_id)} ({p_id})"}
                for p_id, p_conf in producers.items()
                if p_conf.get(CONF_TYPE) in ("boiler", "modulating_boiler")
            ]
            all_prod_options = [
                {"value": p_id, "label": f"{p_conf.get(CONF_NAME, p_id)} ({p_id})"}
                for p_id, p_conf in producers.items()
            ]
            if not hp_options:
                hp_options = all_prod_options
            if not boiler_options:
                boiler_options = all_prod_options

            has_hp = any(
                p.get(CONF_TYPE) in ("heat_pump", "inverter_heat_pump")
                for p in producers.values()
            )
            default_emitter_type = (
                "hydronic" if not has_hp and boiler_options else "mini_split"
            )

            schema_dict[
                Optional(
                    "emitter_type",
                    default=default_emitter_type,
                    visible={"field": "configure_primary_emitter", "value": True},
                )
            ] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": "mini_split", "label": "Mini-Split Head"},
                        {
                            "value": "hydronic",
                            "label": "Hydronic Baseboard / Radiator",
                        },
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
            schema_dict[
                Optional(
                    "hp_emitter_producer",
                    default=hp_options[0]["value"],
                    visible=[
                        {"field": "configure_primary_emitter", "value": True},
                        {"field": "emitter_type", "value": "mini_split"},
                    ],
                )
            ] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=hp_options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
            schema_dict[
                Optional(
                    "boiler_emitter_producer",
                    default=boiler_options[0]["value"],
                    visible=[
                        {"field": "configure_primary_emitter", "value": True},
                        {"field": "emitter_type", "value": "hydronic"},
                    ],
                )
            ] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=boiler_options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
            schema_dict[
                Optional(
                    "emitter_entity_id",
                    visible={"field": "configure_primary_emitter", "value": True},
                )
            ] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["climate", "switch"])
            )
            schema_dict[
                Optional(
                    "emitter_nominal_btu",
                    default=12000.0,
                    visible=[
                        {"field": "configure_primary_emitter", "value": True},
                        {"field": "emitter_type", "value": "mini_split"},
                    ],
                )
            ] = selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1000.0,
                    max=60000.0,
                    step=1000.0,
                    mode=selector.NumberSelectorMode.BOX,
                )
            )
            schema_dict[
                Optional(
                    "emitter_zone_id",
                    default="z1",
                    visible=[
                        {"field": "configure_primary_emitter", "value": True},
                        {"field": "emitter_type", "value": "hydronic"},
                    ],
                )
            ] = str

        schema_dict[vol.Optional("cancel", default=False)] = selector.BooleanSelector()

        schema = vol.Schema(schema_dict)
        return self.async_show_form(
            step_id="space_add", data_schema=schema, errors=errors
        )

    async def async_step_space_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Edit an existing space."""
        s_id = self._selected_space_id or ""
        space = next(
            (s for s in self._options.get(CONF_SPACES, []) if s.get(CONF_ID) == s_id),
            None,
        )
        if not space:
            return await self.async_step_spaces_menu()

        producers = self._options.get(CONF_PRODUCERS, {})
        has_boilers = any(
            p.get(CONF_TYPE) in ("boiler", "modulating_boiler")
            for p in producers.values()
        )

        if user_input is not None:
            if user_input.get("cancel"):
                return await self.async_step_space_manage()

            if user_input.get("delete_space"):
                self._options[CONF_SPACES] = [
                    s
                    for s in self._options.get(CONF_SPACES, [])
                    if s.get(CONF_ID) != s_id
                ]
                return await self.async_step_spaces_menu()

            space[CONF_NAME] = user_input[CONF_NAME]
            space[CONF_TEMP_SENSOR] = user_input[CONF_TEMP_SENSOR]
            if user_input.get(CONF_WINDOW_SENSOR):
                space[CONF_WINDOW_SENSOR] = user_input[CONF_WINDOW_SENSOR]
            else:
                space.pop(CONF_WINDOW_SENSOR, None)
            space[CONF_FLOOR_AREA] = float(user_input.get(CONF_FLOOR_AREA, 300.0))
            space[CONF_CEILING_HEIGHT] = float(user_input.get(CONF_CEILING_HEIGHT, 8.0))
            space[CONF_PRIORITY] = int(user_input.get(CONF_PRIORITY, 5))
            space[CONF_SHARED_BOILER_ROLE] = user_input.get(
                CONF_SHARED_BOILER_ROLE,
                space.get(CONF_SHARED_BOILER_ROLE, "independent"),
            )
            return await self.async_step_space_manage()

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=space.get(CONF_NAME, s_id)): str,
                vol.Required(
                    CONF_TEMP_SENSOR, default=space.get(CONF_TEMP_SENSOR, "")
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(
                    CONF_FLOOR_AREA, default=space.get(CONF_FLOOR_AREA, 300.0)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=10.0,
                        max=10000.0,
                        step=10.0,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_CEILING_HEIGHT,
                    default=space.get(CONF_CEILING_HEIGHT, 8.0),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=5.0,
                        max=30.0,
                        step=0.5,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_PRIORITY, default=space.get(CONF_PRIORITY, 5)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=10, step=1, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_WINDOW_SENSOR,
                    description={"suggested_value": space.get(CONF_WINDOW_SENSOR)},
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor")
                ),
                Optional(
                    CONF_SHARED_BOILER_ROLE,
                    default=space.get(CONF_SHARED_BOILER_ROLE, "independent"),
                    visible=has_boilers,
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {
                                "value": "independent",
                                "label": "Independent (Dedicated or non-shared zone)",
                            },
                            {
                                "value": "primary",
                                "label": "Primary (Drives the shared boiler loop)",
                            },
                            {
                                "value": "secondary",
                                "label": "Secondary (Passively follows shared boiler loop)",
                            },
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional("cancel", default=False): selector.BooleanSelector(),
                vol.Optional("delete_space", default=False): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(
            step_id="space_edit",
            data_schema=schema,
            description_placeholders={"space_name": space.get(CONF_NAME, s_id)},
        )

    async def async_step_space_delete(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Delete a space."""
        s_id = self._selected_space_id or ""
        space = next(
            (s for s in self._options.get(CONF_SPACES, []) if s.get(CONF_ID) == s_id),
            None,
        )
        s_name = space.get(CONF_NAME, s_id) if space else s_id

        if user_input is not None:
            if user_input.get("confirm", False):
                self._options[CONF_SPACES] = [
                    s
                    for s in self._options.get(CONF_SPACES, [])
                    if s.get(CONF_ID) != s_id
                ]
            return await self.async_step_spaces_menu()

        schema = vol.Schema(
            {vol.Required("confirm", default=True): selector.BooleanSelector()}
        )
        return self.async_show_form(
            step_id="space_delete",
            data_schema=schema,
            description_placeholders={"space_name": s_name},
        )

    async def async_step_presets_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show schedule presets list for selected space."""
        s_id = self._selected_space_id or ""
        space = next(
            (s for s in self._options.get(CONF_SPACES, []) if s.get(CONF_ID) == s_id),
            None,
        )
        if not space:
            return await self.async_step_spaces_menu()

        if user_input is not None:
            choice = user_input["preset_action"]
            if choice == "add":
                return await self.async_step_preset_add()
            if choice == "back":
                return await self.async_step_space_manage()
            self._selected_preset_name = choice
            return await self.async_step_preset_edit()

        presets = space.setdefault(CONF_PRESETS, {})
        options = [{"value": "add", "label": "+ Add a schedule preset"}]
        for p_name, sched_entity in presets.items():
            options.append(
                {
                    "value": p_name,
                    "label": f"{p_name} ({sched_entity})",
                }
            )
        options.append(
            {"value": "back", "label": f"Back to {space.get(CONF_NAME, s_id)}"}
        )

        schema = vol.Schema(
            {
                vol.Required("preset_action", default="add"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                )
            }
        )
        return self.async_show_form(
            step_id="presets_menu",
            data_schema=schema,
            description_placeholders={"space_name": space.get(CONF_NAME, s_id)},
        )

    async def async_step_preset_manage(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Redirect directly to preset edit."""
        return await self.async_step_preset_edit(user_input)

    def _derive_preset_name_from_schedule(
        self, sched_entity: str, custom_name: str | None
    ) -> str:
        """Derive preset name from custom name or schedule entity attributes."""
        if custom_name and custom_name.strip():
            return custom_name.strip()
        state = self.hass.states.get(sched_entity)
        if state and state.attributes.get("friendly_name"):
            return str(state.attributes["friendly_name"]).strip()
        if state and state.name:
            return str(state.name).strip()
        slug = sched_entity.split(".", 1)[-1]
        return slug.replace("_", " ").title()

    async def async_step_preset_add(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Add a schedule preset to the space."""
        errors: dict[str, str] = {}
        s_id = self._selected_space_id or ""
        space = next(
            (s for s in self._options.get(CONF_SPACES, []) if s.get(CONF_ID) == s_id),
            None,
        )
        if not space:
            return await self.async_step_spaces_menu()

        if user_input is not None:
            if user_input.get("cancel"):
                return await self.async_step_presets_menu()

            sched_entity = user_input.get("schedule_entity")
            if not sched_entity:
                errors["schedule_entity"] = "schedule_required"
            else:
                custom_name = user_input.get("preset_name")
                p_name = self._derive_preset_name_from_schedule(
                    sched_entity, custom_name
                )

                presets = space.setdefault(CONF_PRESETS, {})
                if p_name in presets:
                    errors["base"] = "preset_exists"
                else:
                    presets[p_name] = sched_entity
                    return await self.async_step_presets_menu()

        schema = vol.Schema(
            {
                vol.Optional("schedule_entity"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="schedule")
                ),
                vol.Optional(
                    "custom_name_toggle", default=False
                ): selector.BooleanSelector(),
                Optional(
                    "preset_name",
                    visible={"field": "custom_name_toggle", "value": True},
                ): selector.TextSelector(),
                vol.Optional("cancel", default=False): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(
            step_id="preset_add",
            data_schema=schema,
            errors=errors,
            description_placeholders={"space_name": space.get(CONF_NAME, s_id)},
        )

    async def async_step_preset_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Edit an existing schedule preset."""
        errors: dict[str, str] = {}
        s_id = self._selected_space_id or ""
        space = next(
            (s for s in self._options.get(CONF_SPACES, []) if s.get(CONF_ID) == s_id),
            None,
        )
        if not space:
            return await self.async_step_spaces_menu()

        presets = space.setdefault(CONF_PRESETS, {})
        old_name = self._selected_preset_name or ""
        old_entity = presets.get(old_name, "")

        if user_input is not None:
            if user_input.get("cancel"):
                return await self.async_step_presets_menu()

            if user_input.get("delete_preset"):
                presets.pop(old_name, None)
                return await self.async_step_presets_menu()

            sched_entity = user_input["schedule_entity"]
            custom_name = user_input.get("preset_name")
            new_name = self._derive_preset_name_from_schedule(sched_entity, custom_name)

            if new_name != old_name and new_name in presets:
                errors["base"] = "preset_exists"
            else:
                presets.pop(old_name, None)
                presets[new_name] = sched_entity
                self._selected_preset_name = new_name
                return await self.async_step_presets_menu()

        schema = vol.Schema(
            {
                vol.Required(
                    "schedule_entity", default=old_entity
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="schedule")
                ),
                vol.Optional(
                    "preset_name",
                    description={"suggested_value": old_name},
                ): selector.TextSelector(),
                vol.Optional("cancel", default=False): selector.BooleanSelector(),
                vol.Optional(
                    "delete_preset", default=False
                ): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(
            step_id="preset_edit",
            data_schema=schema,
            errors=errors,
            description_placeholders={"preset_name": old_name},
        )

    async def async_step_preset_delete(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Redirect delete to preset edit."""
        return await self.async_step_preset_edit(user_input)

    async def async_step_emitters_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show emitters list for selected space."""
        s_id = self._selected_space_id or ""
        space = next(
            (s for s in self._options.get(CONF_SPACES, []) if s.get(CONF_ID) == s_id),
            None,
        )
        if not space:
            return await self.async_step_spaces_menu()

        if user_input is not None:
            choice = user_input["emitter_action"]
            if choice == "add":
                return await self.async_step_emitter_add()
            if choice == "back":
                return await self.async_step_space_manage()
            self._selected_emitter_idx = int(choice)
            return await self.async_step_emitter_edit()

        emitters = space.setdefault(CONF_EMITTERS, [])
        options = [{"value": "add", "label": "+ Add an emitter"}]
        for idx, e in enumerate(emitters):
            e_type = e.get(CONF_TYPE, "emitter")
            e_prod = e.get(CONF_PRODUCER, "")
            e_entity = e.get(CONF_ENTITY_ID, "")
            options.append(
                {
                    "value": str(idx),
                    "label": f"[{idx + 1}] {e_type} ({e_prod} -> {e_entity})",
                }
            )
        options.append(
            {"value": "back", "label": f"Back to {space.get(CONF_NAME, s_id)}"}
        )

        schema = vol.Schema(
            {
                vol.Required("emitter_action", default="add"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                )
            }
        )
        return self.async_show_form(
            step_id="emitters_menu",
            data_schema=schema,
            description_placeholders={"space_name": space.get(CONF_NAME, s_id)},
        )

    async def async_step_emitter_manage(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Redirect directly to emitter edit."""
        return await self.async_step_emitter_edit(user_input)

    async def async_step_emitter_add(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Add an emitter to space."""
        errors: dict[str, str] = {}
        producers = self._options.get(CONF_PRODUCERS, {})
        s_id = self._selected_space_id or ""
        space = next(
            (s for s in self._options.get(CONF_SPACES, []) if s.get(CONF_ID) == s_id),
            None,
        )
        if not space:
            return await self.async_step_spaces_menu()

        if not producers:
            return self.async_show_form(
                step_id="emitter_add",
                data_schema=vol.Schema({}),
                errors={"base": "no_producers"},
                description_placeholders={"space_name": space.get(CONF_NAME, s_id)},
            )

        hp_options = [
            {"value": p_id, "label": f"{p_conf.get(CONF_NAME, p_id)} ({p_id})"}
            for p_id, p_conf in producers.items()
            if p_conf.get(CONF_TYPE) in ("heat_pump", "inverter_heat_pump")
        ]
        boiler_options = [
            {"value": p_id, "label": f"{p_conf.get(CONF_NAME, p_id)} ({p_id})"}
            for p_id, p_conf in producers.items()
            if p_conf.get(CONF_TYPE)
            in ("boiler", "modulating_boiler", "atmospheric_boiler", "steam_boiler")
        ]
        furnace_options = [
            {"value": p_id, "label": f"{p_conf.get(CONF_NAME, p_id)} ({p_id})"}
            for p_id, p_conf in producers.items()
            if p_conf.get(CONF_TYPE) == "furnace"
        ]
        all_prod_options = [
            {"value": p_id, "label": f"{p_conf.get(CONF_NAME, p_id)} ({p_id})"}
            for p_id, p_conf in producers.items()
        ]
        if not hp_options:
            hp_options = all_prod_options
        if not boiler_options:
            boiler_options = all_prod_options
        if not furnace_options:
            furnace_options = all_prod_options

        has_hp = any(
            p.get(CONF_TYPE) in ("heat_pump", "inverter_heat_pump")
            for p in producers.values()
        )
        default_emitter_type = (
            "hydronic" if not has_hp and boiler_options else "mini_split"
        )

        emitter_type_options = [
            {"value": "mini_split", "label": "Mini-Split Head"},
            {"value": "hydronic", "label": "Hydronic Emitter"},
            {"value": "furnace", "label": "Warm-Air Furnace Register"},
        ]
        hydronic_type_options = [
            {"value": "fin_tube_baseboard", "label": "Fin-Tube Baseboard"},
            {"value": "cast_iron_radiator", "label": "Cast-Iron Radiator"},
            {"value": "in_floor_radiant", "label": "Radiant Floor"},
            {"value": "kickspace", "label": "Kickspace Fan-Coil"},
            {"value": "hydro_air", "label": "Hydro-Air (Hydronic Air Handler)"},
        ]

        if user_input is not None:
            if user_input.get("cancel"):
                return await self.async_step_emitters_menu()

            entity_id = user_input.get(CONF_ENTITY_ID)
            if not entity_id:
                errors[CONF_ENTITY_ID] = "entity_required"
            else:
                emitter_type = user_input.get(CONF_TYPE, default_emitter_type)
                if emitter_type == "mini_split":
                    emitter_prod = user_input.get(
                        "hp_emitter_producer"
                    ) or user_input.get(CONF_PRODUCER, hp_options[0]["value"])
                elif emitter_type == "furnace":
                    emitter_prod = user_input.get(
                        "furnace_emitter_producer"
                    ) or user_input.get(CONF_PRODUCER, furnace_options[0]["value"])
                else:
                    emitter_prod = user_input.get(
                        "boiler_emitter_producer"
                    ) or user_input.get(CONF_PRODUCER, boiler_options[0]["value"])

                emitter_data = {
                    CONF_TYPE: emitter_type,
                    CONF_PRODUCER: emitter_prod,
                    CONF_ENTITY_ID: entity_id,
                    CONF_OFFSET: float(user_input.get(CONF_OFFSET, 0.0)),
                }
                if emitter_type == "mini_split":
                    emitter_data[CONF_NOMINAL_BTU] = float(
                        user_input.get(CONF_NOMINAL_BTU, 12000.0)
                    )
                elif emitter_type == "hydronic":
                    emitter_data[CONF_ZONE_ID] = user_input.get(CONF_ZONE_ID, "z1")
                    emitter_data[CONF_HYDRONIC_TYPE] = user_input.get(
                        CONF_HYDRONIC_TYPE, "fin_tube_baseboard"
                    )

                space.setdefault(CONF_EMITTERS, []).append(emitter_data)
                return await self.async_step_emitters_menu()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_TYPE, default=default_emitter_type
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=emitter_type_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                Optional(
                    "hp_emitter_producer",
                    default=hp_options[0]["value"],
                    visible={"field": CONF_TYPE, "value": "mini_split"},
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=hp_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                Optional(
                    "boiler_emitter_producer",
                    default=boiler_options[0]["value"],
                    visible={"field": CONF_TYPE, "value": "hydronic"},
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=boiler_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                Optional(
                    "furnace_emitter_producer",
                    default=furnace_options[0]["value"],
                    visible={"field": CONF_TYPE, "value": "furnace"},
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=furnace_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_ENTITY_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["climate", "switch"])
                ),
                vol.Optional(CONF_OFFSET, default=0.0): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=-10.0,
                        max=10.0,
                        step=0.5,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                Optional(
                    CONF_NOMINAL_BTU,
                    default=12000.0,
                    visible={"field": CONF_TYPE, "value": "mini_split"},
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1000.0,
                        max=100000.0,
                        step=1000.0,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                Optional(
                    CONF_HYDRONIC_TYPE,
                    default="fin_tube_baseboard",
                    visible={"field": CONF_TYPE, "value": "hydronic"},
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=hydronic_type_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                Optional(
                    CONF_ZONE_ID,
                    default="z1",
                    visible={"field": CONF_TYPE, "value": "hydronic"},
                ): str,
                vol.Optional("cancel", default=False): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(
            step_id="emitter_add",
            data_schema=schema,
            errors=errors,
            description_placeholders={"space_name": space.get(CONF_NAME, s_id)},
        )

    async def async_step_emitter_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Edit selected emitter."""
        s_id = self._selected_space_id or ""
        space = next(
            (s for s in self._options.get(CONF_SPACES, []) if s.get(CONF_ID) == s_id),
            None,
        )
        if not space or self._selected_emitter_idx is None:
            return await self.async_step_emitters_menu()

        emitters = space.get(CONF_EMITTERS, [])
        if self._selected_emitter_idx >= len(emitters):
            return await self.async_step_emitters_menu()

        emitter_data = emitters[self._selected_emitter_idx]

        if user_input is not None:
            if user_input.get("cancel"):
                return await self.async_step_emitters_menu()

            if user_input.get("delete_emitter"):
                emitters.pop(self._selected_emitter_idx)
                return await self.async_step_emitters_menu()

            e_type = user_input.get(
                CONF_TYPE, emitter_data.get(CONF_TYPE, "mini_split")
            )
            if e_type == "mini_split":
                emitter_prod = user_input.get("hp_emitter_producer") or user_input.get(
                    CONF_PRODUCER, emitter_data.get(CONF_PRODUCER)
                )
            elif e_type == "furnace":
                emitter_prod = user_input.get(
                    "furnace_emitter_producer"
                ) or user_input.get(CONF_PRODUCER, emitter_data.get(CONF_PRODUCER))
            else:
                emitter_prod = user_input.get(
                    "boiler_emitter_producer"
                ) or user_input.get(CONF_PRODUCER, emitter_data.get(CONF_PRODUCER))

            emitter_data[CONF_TYPE] = e_type
            emitter_data[CONF_PRODUCER] = emitter_prod
            emitter_data[CONF_ENTITY_ID] = user_input[CONF_ENTITY_ID]
            emitter_data[CONF_OFFSET] = float(user_input.get(CONF_OFFSET, 0.0))
            if e_type == "mini_split":
                emitter_data[CONF_NOMINAL_BTU] = float(
                    user_input.get(CONF_NOMINAL_BTU, 12000.0)
                )
                emitter_data.pop(CONF_ZONE_ID, None)
                emitter_data.pop(CONF_HYDRONIC_TYPE, None)
            elif e_type == "hydronic":
                emitter_data[CONF_ZONE_ID] = user_input.get(CONF_ZONE_ID, "z1")
                emitter_data[CONF_HYDRONIC_TYPE] = user_input.get(
                    CONF_HYDRONIC_TYPE, "fin_tube_baseboard"
                )
                emitter_data.pop(CONF_NOMINAL_BTU, None)
            elif e_type == "furnace":
                emitter_data.pop(CONF_NOMINAL_BTU, None)
                emitter_data.pop(CONF_ZONE_ID, None)
                emitter_data.pop(CONF_HYDRONIC_TYPE, None)
                emitter_data.pop(CONF_HYDRONIC_TYPE, None)
            return await self.async_step_emitters_menu()

        producers = self._options.get(CONF_PRODUCERS, {})
        hp_options = [
            {"value": p_id, "label": f"{p_conf.get(CONF_NAME, p_id)} ({p_id})"}
            for p_id, p_conf in producers.items()
            if p_conf.get(CONF_TYPE) in ("heat_pump", "inverter_heat_pump")
        ]
        boiler_options = [
            {"value": p_id, "label": f"{p_conf.get(CONF_NAME, p_id)} ({p_id})"}
            for p_id, p_conf in producers.items()
            if p_conf.get(CONF_TYPE)
            in ("boiler", "modulating_boiler", "atmospheric_boiler", "steam_boiler")
        ]
        furnace_options = [
            {"value": p_id, "label": f"{p_conf.get(CONF_NAME, p_id)} ({p_id})"}
            for p_id, p_conf in producers.items()
            if p_conf.get(CONF_TYPE) == "furnace"
        ]
        all_prod_options = [
            {"value": p_id, "label": f"{p_conf.get(CONF_NAME, p_id)} ({p_id})"}
            for p_id, p_conf in producers.items()
        ]
        if not hp_options:
            hp_options = all_prod_options
        if not boiler_options:
            boiler_options = all_prod_options
        if not furnace_options:
            furnace_options = all_prod_options

        curr_prod = emitter_data.get(CONF_PRODUCER, "")
        hp_default = (
            curr_prod
            if any(p["value"] == curr_prod for p in hp_options)
            else hp_options[0]["value"]
        )
        boiler_default = (
            curr_prod
            if any(p["value"] == curr_prod for p in boiler_options)
            else boiler_options[0]["value"]
        )
        furnace_default = (
            curr_prod
            if any(p["value"] == curr_prod for p in furnace_options)
            else furnace_options[0]["value"]
        )

        emitter_type_options = [
            {"value": "mini_split", "label": "Mini-Split Head"},
            {"value": "hydronic", "label": "Hydronic Emitter"},
            {"value": "furnace", "label": "Warm-Air Furnace Register"},
        ]
        hydronic_type_options = [
            {"value": "fin_tube_baseboard", "label": "Fin-Tube Baseboard"},
            {"value": "cast_iron_radiator", "label": "Cast-Iron Radiator"},
            {"value": "in_floor_radiant", "label": "Radiant Floor"},
            {"value": "kickspace", "label": "Kickspace Fan-Coil"},
            {"value": "hydro_air", "label": "Hydro-Air (Hydronic Air Handler)"},
        ]

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_TYPE, default=emitter_data.get(CONF_TYPE, "mini_split")
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=emitter_type_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                Optional(
                    "hp_emitter_producer",
                    default=hp_default,
                    visible={"field": CONF_TYPE, "value": "mini_split"},
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=hp_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                Optional(
                    "boiler_emitter_producer",
                    default=boiler_default,
                    visible={"field": CONF_TYPE, "value": "hydronic"},
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=boiler_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                Optional(
                    "furnace_emitter_producer",
                    default=furnace_default,
                    visible={"field": CONF_TYPE, "value": "furnace"},
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=furnace_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    CONF_ENTITY_ID, default=emitter_data.get(CONF_ENTITY_ID, "")
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["climate", "switch"])
                ),
                vol.Optional(
                    CONF_OFFSET, default=emitter_data.get(CONF_OFFSET, 0.0)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=-10.0,
                        max=10.0,
                        step=0.5,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                Optional(
                    CONF_NOMINAL_BTU,
                    default=emitter_data.get(CONF_NOMINAL_BTU, 12000.0),
                    visible={"field": CONF_TYPE, "value": "mini_split"},
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1000.0,
                        max=100000.0,
                        step=1000.0,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                Optional(
                    CONF_HYDRONIC_TYPE,
                    default=emitter_data.get(CONF_HYDRONIC_TYPE, "fin_tube_baseboard"),
                    visible={"field": CONF_TYPE, "value": "hydronic"},
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=hydronic_type_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                Optional(
                    CONF_ZONE_ID,
                    default=emitter_data.get(CONF_ZONE_ID, "z1"),
                    visible={"field": CONF_TYPE, "value": "hydronic"},
                ): str,
                vol.Optional("cancel", default=False): selector.BooleanSelector(),
                vol.Optional(
                    "delete_emitter", default=False
                ): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(
            step_id="emitter_edit",
            data_schema=schema,
        )

    async def async_step_emitter_delete(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Redirect delete to emitter edit."""
        return await self.async_step_emitter_edit(user_input)
