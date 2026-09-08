"""Config flow for ARPAT Toscana."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import ArpatApi, ArpatApiError
from .const import CONF_STATION, CONF_STATION_DATA, DOMAIN


class ArpatToscanaConfigFlow(
    config_entries.ConfigFlow,
    domain=DOMAIN,
):
    """Handle a config flow for ARPAT Toscana."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._stations: list[dict[str, Any]] | None = None

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        try:
            stations = await self._async_get_stations()
        except ArpatApiError:
            stations = []
            errors["base"] = "cannot_connect"

        if user_input is not None and stations:
            station_name = str(user_input[CONF_STATION]).strip().upper()
            station_data = next(
                (
                    station
                    for station in stations
                    if str(station.get("NOME_STAZIONE", ""))
                    .strip()
                    .upper()
                    == station_name
                ),
                None,
            )

            if station_data is None:
                errors[CONF_STATION] = "invalid_station"
            else:
                api = ArpatApi(async_get_clientsession(self.hass))
                try:
                    await api.async_get_nrt_last(station_name)
                except ArpatApiError:
                    errors["base"] = "no_data"
                else:
                    await self.async_set_unique_id(station_name)
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=f"ARPAT {station_name}",
                        data={
                            CONF_STATION: station_name,
                            CONF_STATION_DATA: station_data,
                        },
                    )

        options = [
            {
                "value": str(station["NOME_STAZIONE"]),
                "label": self._station_label(station),
            }
            for station in stations
        ]

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_STATION): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
            errors=errors,
        )

    async def _async_get_stations(self) -> list[dict[str, Any]]:
        """Load and cache the regional station list."""
        if self._stations is None:
            api = ArpatApi(async_get_clientsession(self.hass))
            self._stations = await api.async_get_stations()
        return self._stations

    @staticmethod
    def _station_label(station: dict[str, Any]) -> str:
        """Build the label shown in the station selector."""
        name = str(station.get("NOME_STAZIONE", ""))
        comune = str(station.get("COMUNE", "")).title()
        provincia = str(station.get("PROVINCIA", "")).title()
        sensors = station.get("SENSORI", [])

        sensor_text = ""
        if isinstance(sensors, list) and sensors:
            sensor_text = f" · {', '.join(dict.fromkeys(map(str, sensors)))}"

        return f"{comune} ({provincia}) — {name}{sensor_text}"
