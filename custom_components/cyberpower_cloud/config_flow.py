"""Config flow for CyberPower Cloud integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AuthError, CyberPowerCloudAPI
from .const import CONF_EMAIL, CONF_PASSWORD, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class CyberPowerCloudConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CyberPower Cloud."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return CyberPowerOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            api = CyberPowerCloudAPI(
                session, user_input[CONF_EMAIL], user_input[CONF_PASSWORD]
            )

            try:
                await api.login()
            except AuthError as err:
                _LOGGER.warning("Config flow login failed: %s", err)
                errors["base"] = "invalid_auth"
            except (aiohttp.ClientError, TimeoutError) as err:
                _LOGGER.warning("Config flow connection error: %s", err)
                errors["base"] = "cannot_connect"
            else:
                devices = api.devices
                if not devices:
                    errors["base"] = "no_devices"
                else:
                    await self.async_set_unique_id(user_input[CONF_EMAIL].lower())
                    self._abort_if_unique_id_configured()

                    device_names = ", ".join(
                        d.get("DeviceName", d.get("Model", "UPS")) for d in devices
                    )
                    return self.async_create_entry(
                        title=f"CyberPower ({device_names})",
                        data=user_input,
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauth when credentials are invalid."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauth confirmation with new credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
            email = entry.data[CONF_EMAIL]

            session = async_get_clientsession(self.hass)
            api = CyberPowerCloudAPI(session, email, user_input[CONF_PASSWORD])

            try:
                await api.login()
            except AuthError:
                errors["base"] = "invalid_auth"
            except (aiohttp.ClientError, TimeoutError):
                errors["base"] = "cannot_connect"
            else:
                self.hass.config_entries.async_update_entry(
                    entry, data={**entry.data, CONF_PASSWORD: user_input[CONF_PASSWORD]}
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            api = CyberPowerCloudAPI(
                session, user_input[CONF_EMAIL], user_input[CONF_PASSWORD]
            )

            try:
                await api.login()
            except AuthError:
                errors["base"] = "invalid_auth"
            except (aiohttp.ClientError, TimeoutError):
                errors["base"] = "cannot_connect"
            else:
                if not api.devices:
                    errors["base"] = "no_devices"
                else:
                    entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
                    self.hass.config_entries.async_update_entry(entry, data=user_input)
                    await self.hass.config_entries.async_reload(entry.entry_id)
                    return self.async_abort(reason="reconfigure_successful")

        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL, default=entry.data.get(CONF_EMAIL, "")): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )


class CyberPowerOptionsFlow(OptionsFlow):
    """Handle options for CyberPower Cloud."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self._config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current_interval): vol.All(
                        int, vol.Range(min=60, max=3600)
                    ),
                }
            ),
        )
