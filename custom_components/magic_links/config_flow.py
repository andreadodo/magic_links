"""Configurazione da interfaccia grafica."""
from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .const import (
    CONF_CONFIRM_PAGE,
    CONF_DEFAULT_EXPIRY,
    CONF_EXTERNAL_URL,
    CONF_FAIL_WINDOW,
    CONF_MAX_FAILS,
    CONF_SIDEBAR,
    CONF_SIDEBAR_TITLE,
    DEFAULTS,
    DOMAIN,
)

SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_EXTERNAL_URL): TextSelector(),
        vol.Required(CONF_DEFAULT_EXPIRY, default=DEFAULTS[CONF_DEFAULT_EXPIRY]): SelectSelector(
            SelectSelectorConfig(
                options=["24h", "48h", "never"],
                mode=SelectSelectorMode.DROPDOWN,
                translation_key="default_expiry",
            )
        ),
        vol.Required(CONF_CONFIRM_PAGE, default=DEFAULTS[CONF_CONFIRM_PAGE]): BooleanSelector(),
        vol.Required(CONF_MAX_FAILS, default=DEFAULTS[CONF_MAX_FAILS]): NumberSelector(
            NumberSelectorConfig(min=3, max=100, step=1, mode=NumberSelectorMode.BOX)
        ),
        vol.Required(CONF_FAIL_WINDOW, default=DEFAULTS[CONF_FAIL_WINDOW]): NumberSelector(
            NumberSelectorConfig(min=1, max=120, step=1, mode=NumberSelectorMode.BOX, unit_of_measurement="min")
        ),
        vol.Required(CONF_SIDEBAR, default=DEFAULTS[CONF_SIDEBAR]): BooleanSelector(),
        vol.Required(CONF_SIDEBAR_TITLE, default=DEFAULTS[CONF_SIDEBAR_TITLE]): TextSelector(),
    }
)


def _clean(data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    """Normalizza i valori e valida l'URL."""
    out = dict(data)
    errors: dict[str, str] = {}
    url = (out.get(CONF_EXTERNAL_URL) or "").strip().rstrip("/")
    if url and not re.match(r"^https?://[^\s/]+", url):
        errors[CONF_EXTERNAL_URL] = "invalid_url"
    if url:
        out[CONF_EXTERNAL_URL] = url
    else:
        out.pop(CONF_EXTERNAL_URL, None)
    for key in (CONF_MAX_FAILS, CONF_FAIL_WINDOW):
        if key in out:
            out[key] = int(out[key])
    out[CONF_SIDEBAR_TITLE] = (out.get(CONF_SIDEBAR_TITLE) or DEFAULTS[CONF_SIDEBAR_TITLE]).strip()
    return out, errors


class MagicLinksConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        errors: dict[str, str] = {}
        if user_input is not None:
            options, errors = _clean(user_input)
            if not errors:
                return self.async_create_entry(title="Magic Links", data={}, options=options)
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(SCHEMA, user_input or {}),
            errors=errors,
        )

    async def async_step_import(self, import_data):
        """Importa la vecchia configurazione YAML."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        options, _ = _clean({**DEFAULTS, **(import_data or {})})
        return self.async_create_entry(title="Magic Links", data={}, options=options)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return MagicLinksOptionsFlow()


class MagicLinksOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input=None):
        errors: dict[str, str] = {}
        if user_input is not None:
            options, errors = _clean(user_input)
            if not errors:
                return self.async_create_entry(data=options)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(SCHEMA, user_input or self.config_entry.options),
            errors=errors,
        )
