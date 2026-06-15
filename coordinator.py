from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AirXApiError, AirXAuthError, IVTAirXApi
from .const import (
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SENTINEL_VALUES,
    PATH_OUTDOOR_TEMP,
    PATH_GW_FIRMWARE,
    PATH_GW_HARDWARE,
    PATH_GW_SERIAL,
    PATH_GW_MAC,
    PATH_SUPPLY_TEMP,
    PATH_RETURN_TEMP,
    PATH_MODULATION,
    PATH_COMPRESSOR_STATUS,
    PATH_CH_STATUS,
    PATH_DHW_TEMP,
    PATH_SYSTEM_BRAND,
    PATH_SYSTEM_TYPE,
)

_LOGGER = logging.getLogger(__name__)

# Phase 1: minimal path set for smoke-testing the data pipeline.
# Phase 2 will expand this list to full coverage.
POLL_PATHS: tuple[str, ...] = (
    PATH_OUTDOOR_TEMP,
    PATH_SUPPLY_TEMP,
    PATH_RETURN_TEMP,
    PATH_DHW_TEMP,
    PATH_MODULATION,
    PATH_COMPRESSOR_STATUS,
    PATH_CH_STATUS,
    # Gateway / device info (used for device_info on entities)
    PATH_GW_FIRMWARE,
    PATH_GW_HARDWARE,
    PATH_GW_SERIAL,
    PATH_GW_MAC,
    PATH_SYSTEM_BRAND,
    PATH_SYSTEM_TYPE,
)


class IVTAirXCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll the PoinTT API and distribute data to all sensor entities."""

    def __init__(self, hass: HomeAssistant, api: IVTAirXApi) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.api.get_resources(list(POLL_PATHS))
        except AirXAuthError as err:
            raise UpdateFailed(f"Authentication error — re-authenticate the integration: {err}") from err
        except AirXApiError as err:
            raise UpdateFailed(f"PoinTT API error: {err}") from err

    def get_value(self, path: str) -> Any:
        """Extract the 'value' field for a path, returning None for sentinels or missing data."""
        if not self.data:
            return None
        entry = self.data.get(path)
        if not isinstance(entry, dict):
            return None
        val = entry.get("value")
        if val in SENTINEL_VALUES:
            return None
        return val
