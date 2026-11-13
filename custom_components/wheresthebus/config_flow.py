"""Config flow for WheresTheBus."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any
import uuid

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import selector

from .api import WtbAuthError, WtbClient, WtbError
from .const import (
    ALERT_MODES,
    CONF_ALERT_MILES,
    CONF_ALERT_MODE,
    CONF_AM_ENABLED,
    CONF_AM_WINDOW,
    CONF_HOME_ZONE,
    CONF_PM_ENABLED,
    DEFAULT_ALERT_MILES,
    DEFAULT_ALERT_MODE,
    DEFAULT_AM_ENABLED,
    DEFAULT_HOME_ZONE,
    DEFAULT_PM_ENABLED,
    CONF_BUFFER_MIN,
    CONF_DEVICE_ID,
    CONF_DRIVE_MIN,
    CONF_PM_WINDOW,
    CONF_WEEKDAYS_ONLY,
    DEFAULT_AM_WINDOW,
    DEFAULT_BUFFER_MIN,
    DEFAULT_DRIVE_MIN,
    DEFAULT_PM_WINDOW,
    DOMAIN,
)
from .coordinator import parse_window

DEFAULT_OPTIONS = {
    CONF_HOME_ZONE: DEFAULT_HOME_ZONE,
    CONF_DRIVE_MIN: DEFAULT_DRIVE_MIN,
    CONF_BUFFER_MIN: DEFAULT_BUFFER_MIN,
    CONF_ALERT_MODE: DEFAULT_ALERT_MODE,
    CONF_ALERT_MILES: DEFAULT_ALERT_MILES,
    CONF_AM_ENABLED: DEFAULT_AM_ENABLED,
    CONF_AM_WINDOW: DEFAULT_AM_WINDOW,
    CONF_PM_ENABLED: DEFAULT_PM_ENABLED,
    CONF_PM_WINDOW: DEFAULT_PM_WINDOW,
    CONF_WEEKDAYS_ONLY: True,
}

USER_SCHEMA = vol.Schema({vol.Required(CONF_EMAIL): str, vol.Required(CONF_PASSWORD): str})


async def _check(hass, email: str, password: str, device_id: str) -> tuple[str | None, int]:
    client = WtbClient(async_get_clientsession(hass), email, password, device_id)
    try:
        await client.login()
        kids = await client.get_children()
    except WtbAuthError:
        return "invalid_auth", 0
    except WtbError:
        return "cannot_connect", 0
    return None, len(kids)


class WtbConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            email = user_input[CONF_EMAIL].strip().lower()
            await self.async_set_unique_id(email)
            self._abort_if_unique_id_configured()
            device_id = str(uuid.uuid4())
            err, _ = await _check(self.hass, email, user_input[CONF_PASSWORD], device_id)
            if err:
                errors["base"] = err
            else:
                return self.async_create_entry(
                    title=f"WheresTheBus ({email})",
                    data={CONF_EMAIL: email, CONF_PASSWORD: user_input[CONF_PASSWORD], CONF_DEVICE_ID: device_id},
                    options=dict(DEFAULT_OPTIONS),
                )
        return self.async_show_form(step_id="user", data_schema=USER_SCHEMA, errors=errors)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            err, _ = await _check(self.hass, entry.data[CONF_EMAIL], user_input[CONF_PASSWORD], entry.data[CONF_DEVICE_ID])
            if err:
                errors["base"] = err
            else:
                return self.async_update_reload_and_abort(entry, data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]})
        return self.async_show_form(
            step_id="reauth_confirm", data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}), errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return WtbOptionsFlow()


class WtbOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            if not parse_window(user_input[CONF_AM_WINDOW]) or not parse_window(user_input[CONF_PM_WINDOW]):
                errors["base"] = "bad_window"
            else:
                return self.async_create_entry(data=user_input)
        o = {**DEFAULT_OPTIONS, **self.config_entry.options}
        minutes = selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=60, step=1, unit_of_measurement="min", mode="box")
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_HOME_ZONE, default=o[CONF_HOME_ZONE]): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="zone")
                ),
                vol.Required(CONF_ALERT_MODE, default=o[CONF_ALERT_MODE]): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=ALERT_MODES, translation_key=CONF_ALERT_MODE, mode=selector.SelectSelectorMode.LIST
                    )
                ),
                vol.Required(CONF_DRIVE_MIN, default=o[CONF_DRIVE_MIN]): minutes,
                vol.Required(CONF_BUFFER_MIN, default=o[CONF_BUFFER_MIN]): minutes,
                vol.Required(CONF_ALERT_MILES, default=o[CONF_ALERT_MILES]): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=10, step=0.1, unit_of_measurement="mi", mode="box")
                ),
                vol.Required(CONF_AM_ENABLED, default=o[CONF_AM_ENABLED]): bool,
                vol.Required(CONF_AM_WINDOW, default=o[CONF_AM_WINDOW]): str,
                vol.Required(CONF_PM_ENABLED, default=o[CONF_PM_ENABLED]): bool,
                vol.Required(CONF_PM_WINDOW, default=o[CONF_PM_WINDOW]): str,
                vol.Required(CONF_WEEKDAYS_ONLY, default=o[CONF_WEEKDAYS_ONLY]): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
