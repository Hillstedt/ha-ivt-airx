from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable, Awaitable
from typing import Any

import aiohttp

from .const import (
    OAUTH_CLIENT_ID,
    OAUTH_REDIRECT_URI,
    OAUTH_TOKEN_URL,
    POINTT_BASE_URL,
    POINTT_USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)


class AirXApiError(Exception):
    """Unexpected API response."""


class AirXAuthError(AirXApiError):
    """Access token rejected or refresh failed."""


class IVTAirXApi:
    """Read-only async client for the Bosch PoinTT API.

    Holds the current access/refresh tokens and refreshes them automatically
    before they expire.  After each refresh the on_token_refresh callback is
    awaited so the caller can persist the new tokens (e.g. into a HA config
    entry) without this class knowing about HA internals.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        gateway_id: str,
        access_token: str,
        refresh_token: str | None = None,
        expires_at: int = 0,
        on_token_refresh: Callable[[str, str, int], Awaitable[None]] | None = None,
    ) -> None:
        self._session = session
        self._gateway_id = gateway_id
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._expires_at = expires_at  # unix timestamp
        self._on_token_refresh = on_token_refresh

    # ── Properties ───────────────────────────────────────────

    @property
    def access_token(self) -> str:
        return self._access_token

    @property
    def refresh_token(self) -> str | None:
        return self._refresh_token

    @property
    def expires_at(self) -> int:
        return self._expires_at

    @property
    def gateway_id(self) -> str:
        return self._gateway_id

    # ── Token management ─────────────────────────────────────

    def _token_is_fresh(self) -> bool:
        """True if the access token is valid for at least 5 more minutes."""
        if not self._expires_at:
            return False
        return time.time() < self._expires_at - 300

    async def _ensure_token(self) -> None:
        if self._token_is_fresh():
            return
        if not self._refresh_token:
            raise AirXAuthError("Access token expired and no refresh token is available")
        await self._do_refresh()

    async def _do_refresh(self) -> None:
        data = {
            "grant_type": "refresh_token",
            "client_id": OAUTH_CLIENT_ID,
            "refresh_token": self._refresh_token,
        }
        # Token endpoint requires form-encoded body, not JSON.
        # _default_headers() sets Content-Type: application/json (correct for
        # PoinTT resource calls) so we use explicit headers here instead.
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": POINTT_USER_AGENT,
        }
        async with self._session.post(OAUTH_TOKEN_URL, data=data, headers=headers) as resp:
            body = await resp.text()
            if resp.status in (400, 401, 403):
                raise AirXAuthError(f"Token refresh rejected ({resp.status}): {body}")
            if resp.status >= 400:
                raise AirXApiError(f"Token refresh failed ({resp.status}): {body}")
            token_data = await resp.json(content_type=None)

        if "access_token" not in token_data:
            raise AirXAuthError("Token refresh response contained no access_token")

        self._access_token = token_data["access_token"]
        if "refresh_token" in token_data:
            self._refresh_token = token_data["refresh_token"]
        expires_in = int(token_data.get("expires_in", 3600))
        self._expires_at = int(time.time()) + expires_in

        _LOGGER.debug("Access token refreshed (expires_in=%ds)", expires_in)

        if self._on_token_refresh:
            await self._on_token_refresh(
                self._access_token, self._refresh_token, self._expires_at
            )

    # ── HTTP helpers ─────────────────────────────────────────

    def _default_headers(self, *, auth: bool = True) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Accept-Charset": "UTF-8",
            "Content-Type": "application/json",
            "User-Agent": POINTT_USER_AGENT,
        }
        if auth:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    def _resource_url(self, path: str) -> str:
        return f"{POINTT_BASE_URL}/gateways/{self._gateway_id}/resource/{path.lstrip('/')}"

    async def _get(self, url: str) -> Any:
        """Raw GET; caller is responsible for ensuring token freshness first."""
        async with self._session.get(url, headers=self._default_headers()) as resp:
            if resp.status in (401, 403):
                raise AirXAuthError(f"API auth failure: {resp.status}")
            if resp.status == 404:
                return None
            if resp.status >= 400:
                body = await resp.text()
                raise AirXApiError(f"GET {url} failed ({resp.status}): {body}")
            body = await resp.text()
            if not body:
                return None
            try:
                return json.loads(body)
            except Exception as err:
                raise AirXApiError(f"Invalid JSON from {url}: {body[:200]}") from err

    # ── Public read-only interface ────────────────────────────

    @staticmethod
    async def exchange_code(
        session: aiohttp.ClientSession,
        code: str,
        code_verifier: str,
    ) -> dict[str, Any]:
        """Exchange an authorization code for tokens.

        Returns dict with access_token, refresh_token, expires_at (unix ts).
        Raises AirXAuthError on failure.
        """
        data = {
            "grant_type": "authorization_code",
            "client_id": OAUTH_CLIENT_ID,
            "code": code,
            "code_verifier": code_verifier,
            "redirect_uri": OAUTH_REDIRECT_URI,
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": POINTT_USER_AGENT,
        }
        async with session.post(OAUTH_TOKEN_URL, data=data, headers=headers) as resp:
            body = await resp.text()
            if resp.status in (400, 401, 403):
                raise AirXAuthError(f"Code exchange rejected ({resp.status}): {body}")
            if resp.status >= 400:
                raise AirXApiError(f"Code exchange failed ({resp.status}): {body}")
            token_data = await resp.json(content_type=None)

        if "access_token" not in token_data:
            raise AirXAuthError("Code exchange response contained no access_token")

        expires_in = int(token_data.get("expires_in", 3600))
        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "expires_at": int(time.time()) + expires_in,
        }

    @staticmethod
    async def discover_gateway_id(
        session: aiohttp.ClientSession, access_token: str
    ) -> str:
        """Return the first gateway's deviceId from the /gateways/ list.

        Raises AirXApiError if none found, AirXAuthError on 401/403.
        """
        url = f"{POINTT_BASE_URL}/gateways/"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "User-Agent": POINTT_USER_AGENT,
        }
        async with session.get(url, headers=headers) as resp:
            if resp.status in (401, 403):
                raise AirXAuthError(f"Gateway list auth failure: {resp.status}")
            if resp.status >= 400:
                body = await resp.text()
                raise AirXApiError(f"Gateway list failed ({resp.status}): {body}")
            data = await resp.json(content_type=None)

        gateways = data if isinstance(data, list) else [data]
        if not gateways:
            raise AirXApiError("No gateways found on this account")

        gw = gateways[0]
        gw_id = gw.get("deviceId") or gw.get("id") or gw.get("gatewayId")
        if not gw_id:
            raise AirXApiError(f"Could not find deviceId in gateway response: {gw}")
        return str(gw_id)

    async def get_resource(self, path: str) -> dict[str, Any] | None:
        """GET a single resource path.  Returns None on 404 or unavailable."""
        await self._ensure_token()
        url = self._resource_url(path)
        return await self._get(url)

    async def get_resources(self, paths: list[str]) -> dict[str, dict[str, Any] | None]:
        """GET multiple resource paths sequentially.

        Returns {path: response_or_None}.  Individual 404s are recorded as None
        without raising so the coordinator can mark those entities unavailable.
        """
        results: dict[str, dict[str, Any] | None] = {}
        await self._ensure_token()
        for path in paths:
            try:
                results[path] = await self._get(self._resource_url(path))
            except AirXAuthError:
                raise
            except AirXApiError as err:
                _LOGGER.debug("Skipping %s: %s", path, err)
                results[path] = None
        return results

    async def test_connection(self) -> bool:
        """Return True if we can reach the API with valid credentials."""
        try:
            await self._ensure_token()
            data = await self._get(f"{POINTT_BASE_URL}/gateways/{self._gateway_id}")
            return data is not None
        except (AirXApiError, aiohttp.ClientError):
            return False
