"""Config flow for HVAC Fusion integration."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_OUTDOOR_TEMPERATURE_ENTITY,
    CONF_ELECTRIC_COST_PER_KWH,
    CONF_GAS_COST_PER_THERM,
    CONF_PROPANE_COST_PER_GAL,
    CONF_CONTROL_ENABLED,
    CONF_TARIFFS,
    CONF_PRODUCERS,
    CONF_SPACES,
)

_LOGGER = logging.getLogger(__name__)


class HvacFusionConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HVAC Fusion."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial hub configuration step."""
        errors: Dict[str, str] = {}

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
