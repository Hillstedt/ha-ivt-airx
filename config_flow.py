from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AirXApiError, AirXAuthError, IVTAirXApi
from .auth import build_authorization_url, create_code_verifier, create_state, extract_code_from_redirect
from .const import CONF_ACCESS_TOKEN, CONF_EXPIRES_AT, CONF_GATEWAY_ID, CONF_REFRESH_TOKEN, DOMAIN

_LOGGER = logging.getLogger(__name__)


class IVTAirXConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Single-step OAuth2 config flow.

    1. Display the SingleKey ID login URL.
    2. User logs in, browser redirects to a custom URI scheme.
    3. User copies that redirect URL (or just the code) and pastes it here.
    4. We exchange the code for tokens and discover the gateway ID.
    """

    VERSION = 1

    def _ensure_oauth_context(self) -> None:
        if not hasattr(self, "_code_verifier"):
            self._code_verifier: str = create_code_verifier()
            self._state: str = create_state()
            self._auth_url: str = build_authorization_url(self._code_verifier, self._state)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        self._ensure_oauth_context()
        errors: dict[str, str] = {}

        if user_input is not None:
            redirect_url = user_input.get("redirect_url", "").strip()
            gateway_id_hint = user_input.get(CONF_GATEWAY_ID, "").strip()

            try:
                code = extract_code_from_redirect(redirect_url, self._state)
            except ValueError as err:
                _LOGGER.debug("Code extraction failed: %s", err)
                errors["redirect_url"] = "invalid_code"
                return self._show_form(errors)

            session = async_get_clientsession(self.hass)

            try:
                token_data = await IVTAirXApi.exchange_code(session, code, self._code_verifier)
            except AirXAuthError:
                errors["redirect_url"] = "invalid_auth"
                return self._show_form(errors)
            except AirXApiError:
                errors["base"] = "cannot_connect"
                return self._show_form(errors)

            if not token_data.get(CONF_REFRESH_TOKEN):
                errors["redirect_url"] = "no_refresh_token"
                return self._show_form(errors)

            # Discover gateway ID (auto or user-supplied)
            try:
                if gateway_id_hint:
                    gateway_id = gateway_id_hint
                else:
                    gateway_id = await IVTAirXApi.discover_gateway_id(
                        session, token_data[CONF_ACCESS_TOKEN]
                    )
            except AirXAuthError:
                errors["base"] = "invalid_auth"
                return self._show_form(errors)
            except AirXApiError:
                errors["base"] = "no_gateway"
                return self._show_form(errors)

            await self.async_set_unique_id(gateway_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"IVT AirX ({gateway_id})",
                data={
                    CONF_ACCESS_TOKEN: token_data[CONF_ACCESS_TOKEN],
                    CONF_REFRESH_TOKEN: token_data[CONF_REFRESH_TOKEN],
                    CONF_EXPIRES_AT: token_data["expires_at"],
                    CONF_GATEWAY_ID: gateway_id,
                },
            )

        return self._show_form(errors)

    def _show_form(self, errors: dict[str, str]) -> config_entries.ConfigFlowResult:
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("redirect_url"): str,
                    vol.Optional(CONF_GATEWAY_ID, default=""): str,
                }
            ),
            errors=errors,
            description_placeholders={"authorization_url": self._auth_url},
        )
