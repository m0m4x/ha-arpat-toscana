"""Config flow for ARPAT Toscana."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import ArpatApi, ArpatApiError
from .const import (
    ALL_DATA_TYPES,
    CONF_DATA_TYPES,
    CONF_STATION,
    CONF_STATION_DATA,
    DEFAULT_DATA_TYPES,
    DOMAIN,
)


def get_enabled_data_types(entry: ConfigEntry) -> list[str]:
    """Return validated data types from options or config-entry data."""
    configured = entry.options.get(
        CONF_DATA_TYPES,
        entry.data.get(CONF_DATA_TYPES, DEFAULT_DATA_TYPES),
    )

    if not isinstance(configured, (list, tuple, set)):
        return list(DEFAULT_DATA_TYPES)

    enabled = [item for item in configured if item in ALL_DATA_TYPES]
    return list(dict.fromkeys(enabled)) or list(DEFAULT_DATA_TYPES)


def _data_types_selector() -> SelectSelector:
    """Return the translated multi-select used by config and options flow."""
    return SelectSelector(
        SelectSelectorConfig(
            options=list(ALL_DATA_TYPES),
            multiple=True,
            mode=SelectSelectorMode.LIST,
            translation_key="data_types",
        )
    )


class ArpatToscanaConfigFlow(
    config_entries.ConfigFlow,
    domain=DOMAIN,
):
    """Handle a config flow for ARPAT Toscana."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._stations: list[dict[str, Any]] | None = None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return ArpatToscanaOptionsFlow()

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle station and dataset-type selection."""
        errors: dict[str, str] = {}

        try:
            stations = await self._async_get_stations()
        except ArpatApiError:
            stations = []
            errors["base"] = "cannot_connect"

        if user_input is not None and stations:
            station_name = str(user_input[CONF_STATION]).strip().upper()
            data_types = self._validate_data_types(
                user_input.get(CONF_DATA_TYPES)
            )

            if not data_types:
                errors[CONF_DATA_TYPES] = "no_data_types"

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

            if not errors and station_data is not None:
                await self.async_set_unique_id(station_name)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"ARPAT {station_name}",
                    data={
                        CONF_STATION: station_name,
                        CONF_STATION_DATA: station_data,
                        CONF_DATA_TYPES: data_types,
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
                    ),
                    vol.Required(
                        CONF_DATA_TYPES,
                        default=list(DEFAULT_DATA_TYPES),
                    ): _data_types_selector(),
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
        return f"{comune} ({provincia}) — {name}"

    @staticmethod
    def _validate_data_types(value: Any) -> list[str]:
        """Validate and normalize the selected dataset types."""
        if not isinstance(value, (list, tuple, set)):
            return []

        selected = [item for item in value if item in ALL_DATA_TYPES]
        return list(dict.fromkeys(selected))


class ArpatToscanaOptionsFlow(config_entries.OptionsFlowWithReload):
    """Allow changing dataset types without removing the station."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Manage ARPAT Toscana options."""
        errors: dict[str, str] = {}
        current = get_enabled_data_types(self.config_entry)

        if user_input is not None:
            data_types = ArpatToscanaConfigFlow._validate_data_types(
                user_input.get(CONF_DATA_TYPES)
            )

            if data_types:
                return self.async_create_entry(
                    data={CONF_DATA_TYPES: data_types}
                )

            errors[CONF_DATA_TYPES] = "no_data_types"

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DATA_TYPES,
                        default=current,
                    ): _data_types_selector()
                }
            ),
            errors=errors,
        )
