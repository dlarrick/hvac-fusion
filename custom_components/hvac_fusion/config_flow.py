"""Config flow for HVAC Fusion integration."""

from __future__ import annotations

import logging
import os
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_ENTITY_ID, CONF_ID, CONF_NAME
from homeassistant.core import callback
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
    CONF_HEAT_PUMP_SAFETY_BAND_F,
    CONF_NOMINAL_BTU,
    CONF_OFFSET,
    CONF_OUTDOOR_TEMPERATURE_ENTITY,
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


def get_available_producer_profiles() -> list[dict[str, str]]:
    """Return available producer profile choices."""
    profiles = [
        {
            "value": "mitsubishi/mxz_3c30nahz2.json",
            "label": "Mitsubishi MXZ-3C30NAHZ2 (30k Hyper-Heat)",
        },
        {
            "value": "mitsubishi/mxz_2d20nlhz.json",
            "label": "Mitsubishi MXZ-2D20NLHZ (20k Hyper-Heat)",
        },
        {
            "value": "haier/3u24ms2vhb.json",
            "label": "Haier 3U24MS2VHB (24k 3-Port)",
        },
        {
            "value": "bradford_white/bwmfthw140p.json",
            "label": "Bradford White BWMFTHW140P (Brute FT Propane)",
        },
        {
            "value": "burnham/alta_150.json",
            "label": "Burnham Alta 150 (Natural Gas)",
        },
    ]
    try:
        import hvac_crossover

        pkg_dir = os.path.dirname(hvac_crossover.__file__)
        pkg_profiles_dir = os.path.join(pkg_dir, "profiles", "producers")
        if os.path.isdir(pkg_profiles_dir):
            for root, _, files in os.walk(pkg_profiles_dir):
                for f in files:
                    if f.endswith(".json"):
                        rel_path = os.path.relpath(
                            os.path.join(root, f), pkg_profiles_dir
                        )
                        if not any(p["value"] == rel_path for p in profiles):
                            profiles.append({"value": rel_path, "label": rel_path})
    except Exception:
        pass
    profiles.append({"value": "none", "label": "None / Custom Modulating Boiler"})
    return profiles


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
        """Handle the initial hub configuration step."""
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
                CONF_TARIFFS: {
                    CONF_ELECTRIC_COST_PER_KWH: user_input[CONF_ELECTRIC_COST_PER_KWH],
                    CONF_GAS_COST_PER_THERM: user_input.get(
                        CONF_GAS_COST_PER_THERM, 0.0
                    ),
                    CONF_PROPANE_COST_PER_GAL: user_input.get(
                        CONF_PROPANE_COST_PER_GAL, 0.0
                    ),
                },
                CONF_PRODUCERS: {},
                CONF_SPACES: [],
            }

            return self.async_create_entry(title=title, data=entry_data)

        schema = vol.Schema(
            {
                vol.Optional(CONF_NAME, default="HVAC Fusion"): str,
                vol.Required(CONF_OUTDOOR_TEMPERATURE_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(
                    CONF_ELECTRIC_COST_PER_KWH, default=0.25
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=2.0,
                        step=0.01,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_GAS_COST_PER_THERM, default=0.0
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=10.0,
                        step=0.01,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_PROPANE_COST_PER_GAL, default=0.0
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=15.0,
                        step=0.01,
                        mode=selector.NumberSelectorMode.BOX,
                    )
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

    @property
    def _options(self) -> dict[str, Any]:
        """Return or lazily initialize working options copy."""
        if self._working_options is None:
            opts = dict(self.config_entry.options)
            if not opts:
                opts = dict(self.config_entry.data)
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
        """Configure global sensors and tariffs."""
        if user_input is not None:
            self._options[CONF_OUTDOOR_TEMPERATURE_ENTITY] = user_input[
                CONF_OUTDOOR_TEMPERATURE_ENTITY
            ]
            if CONF_SOLAR_EXPORT_ENTITY in user_input:
                self._options[CONF_SOLAR_EXPORT_ENTITY] = user_input[
                    CONF_SOLAR_EXPORT_ENTITY
                ]
            self._options[CONF_HEAT_PUMP_SAFETY_BAND_F] = float(
                user_input.get(
                    CONF_HEAT_PUMP_SAFETY_BAND_F, DEFAULT_HEAT_PUMP_SAFETY_BAND_F
                )
            )

            tariffs = self._options.setdefault(CONF_TARIFFS, {})
            tariffs[CONF_ELECTRIC_COST_PER_KWH] = float(
                user_input[CONF_ELECTRIC_COST_PER_KWH]
            )
            tariffs[CONF_GAS_COST_PER_THERM] = float(
                user_input.get(CONF_GAS_COST_PER_THERM, 0.0)
            )
            tariffs[CONF_PROPANE_COST_PER_GAL] = float(
                user_input.get(CONF_PROPANE_COST_PER_GAL, 0.0)
            )

            for key in (
                CONF_ELECTRIC_RATE_SENSOR,
                CONF_GAS_RATE_SENSOR,
                CONF_PROPANE_RATE_SENSOR,
            ):
                if user_input.get(key):
                    tariffs[key] = user_input[key]
                else:
                    tariffs.pop(key, None)

            return await self.async_step_init()

        tariffs = self._options.get(CONF_TARIFFS, {})
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
                vol.Required(
                    CONF_ELECTRIC_COST_PER_KWH,
                    default=tariffs.get(CONF_ELECTRIC_COST_PER_KWH, 0.25),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=2.0,
                        step=0.01,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_ELECTRIC_RATE_SENSOR,
                    description={
                        "suggested_value": tariffs.get(CONF_ELECTRIC_RATE_SENSOR)
                    },
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(
                    CONF_GAS_COST_PER_THERM,
                    default=tariffs.get(CONF_GAS_COST_PER_THERM, 0.0),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=10.0,
                        step=0.01,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_GAS_RATE_SENSOR,
                    description={"suggested_value": tariffs.get(CONF_GAS_RATE_SENSOR)},
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(
                    CONF_PROPANE_COST_PER_GAL,
                    default=tariffs.get(CONF_PROPANE_COST_PER_GAL, 0.0),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=15.0,
                        step=0.01,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_PROPANE_RATE_SENSOR,
                    description={
                        "suggested_value": tariffs.get(CONF_PROPANE_RATE_SENSOR)
                    },
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
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
        return self.async_show_form(step_id="global_settings", data_schema=schema)

    async def async_step_policies_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure operational policies."""
        if user_input is not None:
            self._options[CONF_CONTROL_ENABLED] = user_input.get(
                CONF_CONTROL_ENABLED, False
            )
            self._options[CONF_CYCLING_BAND] = float(
                user_input.get(CONF_CYCLING_BAND, DEFAULT_CYCLING_BAND)
            )
            self._options[CONF_EVALUATION_INTERVAL_MINUTES] = int(
                user_input.get(
                    CONF_EVALUATION_INTERVAL_MINUTES,
                    DEFAULT_EVALUATION_INTERVAL_MINUTES,
                )
            )
            return await self.async_step_init()

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_CONTROL_ENABLED,
                    default=self._options.get(CONF_CONTROL_ENABLED, False),
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_CYCLING_BAND,
                    default=self._options.get(CONF_CYCLING_BAND, DEFAULT_CYCLING_BAND),
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
        return self.async_show_form(step_id="policies_menu", data_schema=schema)

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
            return await self.async_step_producer_manage()

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
        """Choose action for selected producer."""
        if user_input is not None:
            act = user_input["action"]
            if act == "edit":
                return await self.async_step_producer_edit()
            if act == "delete":
                return await self.async_step_producer_delete()
            return await self.async_step_producers_menu()

        p_id = self._selected_producer_id or ""
        p_name = (
            self._options.get(CONF_PRODUCERS, {}).get(p_id, {}).get(CONF_NAME, p_id)
        )

        schema = vol.Schema(
            {
                vol.Required("action", default="edit"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "edit", "label": f"Edit {p_name}"},
                            {"value": "delete", "label": f"Delete {p_name}"},
                            {"value": "back", "label": "Back to Producers List"},
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                    )
                )
            }
        )
        return self.async_show_form(
            step_id="producer_manage",
            data_schema=schema,
            description_placeholders={"producer_name": p_name},
        )

    async def async_step_producer_add(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Add a new producer."""
        errors: dict[str, str] = {}
        if user_input is not None:
            p_id = user_input[CONF_ID].strip().lower().replace(" ", "_")
            if p_id in self._options.get(CONF_PRODUCERS, {}):
                errors["base"] = "producer_id_exists"
            else:
                profile = user_input.get(CONF_PROFILE)
                if profile == "none":
                    profile = None
                self._options[CONF_PRODUCERS][p_id] = {
                    CONF_NAME: user_input.get(CONF_NAME, p_id),
                    CONF_TYPE: user_input[CONF_TYPE],
                    CONF_PROFILE: profile,
                    CONF_FUEL_TYPE: user_input.get(CONF_FUEL_TYPE, "natural_gas"),
                }
                return await self.async_step_producers_menu()

        profile_choices = get_available_producer_profiles()
        schema = vol.Schema(
            {
                vol.Required(CONF_ID): str,
                vol.Required(CONF_NAME): str,
                vol.Required(
                    CONF_TYPE, default="inverter_heat_pump"
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {
                                "value": "inverter_heat_pump",
                                "label": "Inverter Heat Pump",
                            },
                            {
                                "value": "modulating_boiler",
                                "label": "Modulating Boiler",
                            },
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_PROFILE, default=profile_choices[0]["value"]
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=profile_choices,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_FUEL_TYPE, default="natural_gas"
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "natural_gas", "label": "Natural Gas"},
                            {"value": "propane", "label": "Propane"},
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
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
            profile = user_input.get(CONF_PROFILE)
            if profile == "none":
                profile = None
            p_conf[CONF_NAME] = user_input.get(CONF_NAME, p_id)
            p_conf[CONF_TYPE] = user_input[CONF_TYPE]
            p_conf[CONF_PROFILE] = profile
            p_conf[CONF_FUEL_TYPE] = user_input.get(CONF_FUEL_TYPE, "natural_gas")
            return await self.async_step_producers_menu()

        profile_choices = get_available_producer_profiles()
        current_profile = p_conf.get(CONF_PROFILE) or "none"

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=p_conf.get(CONF_NAME, p_id)): str,
                vol.Required(
                    CONF_TYPE, default=p_conf.get(CONF_TYPE, "inverter_heat_pump")
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {
                                "value": "inverter_heat_pump",
                                "label": "Inverter Heat Pump",
                            },
                            {
                                "value": "modulating_boiler",
                                "label": "Modulating Boiler",
                            },
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_PROFILE, default=current_profile
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=profile_choices,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_FUEL_TYPE, default=p_conf.get(CONF_FUEL_TYPE, "natural_gas")
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "natural_gas", "label": "Natural Gas"},
                            {"value": "propane", "label": "Propane"},
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
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
        """Delete a producer."""
        p_id = self._selected_producer_id or ""
        p_name = (
            self._options.get(CONF_PRODUCERS, {}).get(p_id, {}).get(CONF_NAME, p_id)
        )

        if user_input is not None:
            if user_input.get("confirm", False):
                self._options.get(CONF_PRODUCERS, {}).pop(p_id, None)
            return await self.async_step_producers_menu()

        schema = vol.Schema(
            {vol.Required("confirm", default=True): selector.BooleanSelector()}
        )
        return self.async_show_form(
            step_id="producer_delete",
            data_schema=schema,
            description_placeholders={"producer_name": p_name},
        )

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
        if user_input is not None:
            s_id = user_input[CONF_ID].strip().lower().replace(" ", "_")
            existing_ids = [s.get(CONF_ID) for s in self._options.get(CONF_SPACES, [])]
            if s_id in existing_ids:
                errors["base"] = "space_id_exists"
            else:
                space_entry = {
                    CONF_ID: s_id,
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_TEMP_SENSOR: user_input[CONF_TEMP_SENSOR],
                    CONF_FLOOR_AREA: float(user_input.get(CONF_FLOOR_AREA, 300.0)),
                    CONF_CEILING_HEIGHT: float(
                        user_input.get(CONF_CEILING_HEIGHT, 8.0)
                    ),
                    CONF_PRIORITY: int(user_input.get(CONF_PRIORITY, 5)),
                    CONF_SHARED_BOILER_ROLE: user_input.get(
                        CONF_SHARED_BOILER_ROLE, "independent"
                    ),
                    CONF_EMITTERS: [],
                }
                if user_input.get(CONF_WINDOW_SENSOR):
                    space_entry[CONF_WINDOW_SENSOR] = user_input[CONF_WINDOW_SENSOR]

                self._options.setdefault(CONF_SPACES, []).append(space_entry)
                self._selected_space_id = s_id
                return await self.async_step_space_manage()

        schema = vol.Schema(
            {
                vol.Required(CONF_ID): str,
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_TEMP_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_WINDOW_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor")
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
                vol.Optional(
                    CONF_SHARED_BOILER_ROLE, default="independent"
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "independent", "label": "Independent"},
                            {"value": "master", "label": "Master"},
                            {"value": "slave", "label": "Slave"},
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )
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

        if user_input is not None:
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
                CONF_SHARED_BOILER_ROLE, "independent"
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
                    CONF_WINDOW_SENSOR,
                    description={"suggested_value": space.get(CONF_WINDOW_SENSOR)},
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor")
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
                    CONF_SHARED_BOILER_ROLE,
                    default=space.get(CONF_SHARED_BOILER_ROLE, "independent"),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "independent", "label": "Independent"},
                            {"value": "master", "label": "Master"},
                            {"value": "slave", "label": "Slave"},
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
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
            return await self.async_step_emitter_manage()

        emitters = space.setdefault(CONF_EMITTERS, [])
        options = [{"value": "add", "label": "+ Add an emitter"}]
        for idx, e in enumerate(emitters):
            e_type = e.get(CONF_TYPE, "emitter")
            e_prod = e.get(CONF_PRODUCER, "")
            e_entity = e.get(CONF_ENTITY_ID, "")
            options.append(
                {
                    "value": str(idx),
                    "label": f"[{idx+1}] {e_type} ({e_prod} -> {e_entity})",
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
        """Choose action for selected emitter."""
        if user_input is not None:
            act = user_input["action"]
            if act == "edit":
                return await self.async_step_emitter_edit()
            if act == "delete":
                return await self.async_step_emitter_delete()
            return await self.async_step_emitters_menu()

        schema = vol.Schema(
            {
                vol.Required("action", default="edit"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "edit", "label": "Edit Emitter"},
                            {"value": "delete", "label": "Delete Emitter"},
                            {"value": "back", "label": "Back to Emitters List"},
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                    )
                )
            }
        )
        return self.async_show_form(
            step_id="emitter_manage",
            data_schema=schema,
        )

    async def async_step_emitter_add(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Add an emitter to space."""
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

        if user_input is not None:
            emitter_data = {
                CONF_TYPE: user_input[CONF_TYPE],
                CONF_PRODUCER: user_input[CONF_PRODUCER],
                CONF_ENTITY_ID: user_input[CONF_ENTITY_ID],
                CONF_OFFSET: float(user_input.get(CONF_OFFSET, 0.0)),
            }
            if user_input[CONF_TYPE] == "mini_split":
                emitter_data[CONF_NOMINAL_BTU] = float(
                    user_input.get(CONF_NOMINAL_BTU, 12000.0)
                )
            elif user_input[CONF_TYPE] == "hydronic":
                emitter_data[CONF_ZONE_ID] = user_input.get(CONF_ZONE_ID, "z1")

            space.setdefault(CONF_EMITTERS, []).append(emitter_data)
            return await self.async_step_emitters_menu()

        prod_options = [
            {"value": p_id, "label": f"{p_conf.get(CONF_NAME, p_id)} ({p_id})"}
            for p_id, p_conf in producers.items()
        ]
        default_prod = prod_options[0]["value"] if prod_options else ""

        schema = vol.Schema(
            {
                vol.Required(CONF_TYPE, default="mini_split"): selector.SelectSelector(
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
                ),
                vol.Required(
                    CONF_PRODUCER, default=default_prod
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=prod_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_ENTITY_ID): selector.EntitySelector(
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
                vol.Optional(
                    CONF_NOMINAL_BTU, default=12000.0
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1000.0,
                        max=60000.0,
                        step=1000.0,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(CONF_ZONE_ID, default="z1"): str,
            }
        )
        return self.async_show_form(
            step_id="emitter_add",
            data_schema=schema,
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
            emitter_data[CONF_TYPE] = user_input[CONF_TYPE]
            emitter_data[CONF_PRODUCER] = user_input[CONF_PRODUCER]
            emitter_data[CONF_ENTITY_ID] = user_input[CONF_ENTITY_ID]
            emitter_data[CONF_OFFSET] = float(user_input.get(CONF_OFFSET, 0.0))
            if user_input[CONF_TYPE] == "mini_split":
                emitter_data[CONF_NOMINAL_BTU] = float(
                    user_input.get(CONF_NOMINAL_BTU, 12000.0)
                )
                emitter_data.pop(CONF_ZONE_ID, None)
            elif user_input[CONF_TYPE] == "hydronic":
                emitter_data[CONF_ZONE_ID] = user_input.get(CONF_ZONE_ID, "z1")
                emitter_data.pop(CONF_NOMINAL_BTU, None)
            return await self.async_step_emitters_menu()

        producers = self._options.get(CONF_PRODUCERS, {})
        prod_options = [
            {"value": p_id, "label": f"{p_conf.get(CONF_NAME, p_id)} ({p_id})"}
            for p_id, p_conf in producers.items()
        ]

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_TYPE, default=emitter_data.get(CONF_TYPE, "mini_split")
                ): selector.SelectSelector(
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
                ),
                vol.Required(
                    CONF_PRODUCER, default=emitter_data.get(CONF_PRODUCER, "")
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=prod_options,
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
                vol.Optional(
                    CONF_NOMINAL_BTU,
                    default=emitter_data.get(CONF_NOMINAL_BTU, 12000.0),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1000.0,
                        max=60000.0,
                        step=1000.0,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_ZONE_ID, default=emitter_data.get(CONF_ZONE_ID, "z1")
                ): str,
            }
        )
        return self.async_show_form(
            step_id="emitter_edit",
            data_schema=schema,
        )

    async def async_step_emitter_delete(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Delete an emitter."""
        s_id = self._selected_space_id or ""
        space = next(
            (s for s in self._options.get(CONF_SPACES, []) if s.get(CONF_ID) == s_id),
            None,
        )

        if user_input is not None:
            if (
                user_input.get("confirm", False)
                and space
                and self._selected_emitter_idx is not None
            ):
                emitters = space.get(CONF_EMITTERS, [])
                if self._selected_emitter_idx < len(emitters):
                    emitters.pop(self._selected_emitter_idx)
            return await self.async_step_emitters_menu()

        schema = vol.Schema(
            {vol.Required("confirm", default=True): selector.BooleanSelector()}
        )
        return self.async_show_form(
            step_id="emitter_delete",
            data_schema=schema,
        )
