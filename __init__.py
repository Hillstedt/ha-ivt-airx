from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import IVTAirXApi
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_EXPIRES_AT,
    CONF_GATEWAY_ID,
    CONF_REFRESH_TOKEN,
    DOMAIN,
    MANUFACTURER,
    PATH_GW_FIRMWARE,
    PATH_GW_HARDWARE,
    PATH_GW_MAC,
    PATH_GW_SERIAL,
    PATH_SYSTEM_TYPE,
)
from .coordinator import IVTAirXCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    session = async_get_clientsession(hass)

    async def _on_token_refresh(
        access_token: str, refresh_token: str | None, expires_at: int
    ) -> None:
        """Persist refreshed tokens back into the config entry so they survive restarts."""
        new_data = dict(entry.data)
        new_data[CONF_ACCESS_TOKEN] = access_token
        if refresh_token:
            new_data[CONF_REFRESH_TOKEN] = refresh_token
        new_data[CONF_EXPIRES_AT] = expires_at
        hass.config_entries.async_update_entry(entry, data=new_data)
        _LOGGER.debug("Persisted refreshed tokens to config entry")

    api = IVTAirXApi(
        session=session,
        gateway_id=entry.data[CONF_GATEWAY_ID],
        access_token=entry.data[CONF_ACCESS_TOKEN],
        refresh_token=entry.data.get(CONF_REFRESH_TOKEN),
        expires_at=entry.data.get(CONF_EXPIRES_AT, 0),
        on_token_refresh=_on_token_refresh,
    )

    coordinator = IVTAirXCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    # Register device now that we have real data from the first poll
    fw = coordinator.get_value(PATH_GW_FIRMWARE)
    hw = coordinator.get_value(PATH_GW_HARDWARE)
    serial = coordinator.get_value(PATH_GW_SERIAL)
    mac = coordinator.get_value(PATH_GW_MAC)
    sys_type = coordinator.get_value(PATH_SYSTEM_TYPE)
    model = f"AirX 407 ({sys_type})" if sys_type else "AirX 407"

    dev_reg = dr.async_get(hass)
    dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.data[CONF_GATEWAY_ID])},
        name="IVT AirX Heat Pump",
        manufacturer=MANUFACTURER,
        model=model,
        sw_version=fw,
        hw_version=hw,
        serial_number=serial or entry.data[CONF_GATEWAY_ID],
        connections={(dr.CONNECTION_NETWORK_MAC, mac)} if mac else set(),
    )

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
