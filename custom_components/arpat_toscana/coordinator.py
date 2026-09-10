"""Data coordinator for ARPAT Toscana."""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any, Iterable

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import ArpatApi, ArpatApiError
from .const import (
    DATA_TYPE_DAILY_EXCEEDANCES,
    DATA_TYPE_DAILY_INDICATORS,
    DATA_TYPE_NRT,
    DAILY_UPDATE_INTERVAL,
    NRT_UPDATE_INTERVAL,
)
from .parsers import (
    current_nrt_values,
    discover_nrt_parameters,
    normalize_daily_indicators,
    normalize_exceedances,
)

_LOGGER = logging.getLogger(__name__)


class ArpatDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate selected ARPAT datasets for one station."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: ArpatApi,
        station: str,
        station_data: dict[str, Any],
        enabled_data_types: Iterable[str],
    ) -> None:
        """Initialize the coordinator."""
        self.enabled_data_types = frozenset(enabled_data_types)
        update_interval = (
            NRT_UPDATE_INTERVAL
            if DATA_TYPE_NRT in self.enabled_data_types
            else DAILY_UPDATE_INTERVAL
        )

        super().__init__(
            hass,
            _LOGGER,
            name=f"ARPAT Toscana {station}",
            update_interval=update_interval,
        )

        self.api = api
        self.station = station
        self.station_data = station_data

        self._nrt_initialized = False
        self._nrt_parameters: set[str] = set()
        self._nrt: dict[str, Any] = {
            "available": False,
            "record": {},
            "measurements": {},
        }

        self._daily_indicator_parameters: set[str] = set()
        self._daily_indicators: dict[str, Any] = {
            "available": False,
            "record": {},
            "measurements": {},
        }
        self._last_daily_indicators_attempt: datetime | None = None

        self._exceedances: dict[str, Any] = {
            "available": False,
            "count": None,
            "date": None,
            "records": [],
        }
        self._last_exceedances_attempt: datetime | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch only the ARPAT dataset types selected by the user."""
        now = datetime.now(UTC)
        attempted = 0
        succeeded = 0

        if DATA_TYPE_NRT in self.enabled_data_types:
            attempted += 1
            try:
                await self._async_update_nrt()
                succeeded += 1
            except ArpatApiError as err:
                self._nrt["available"] = False
                _LOGGER.warning(
                    "Unable to update ARPAT NRT data for %s: %s",
                    self.station,
                    err,
                )

        if (
            DATA_TYPE_DAILY_INDICATORS in self.enabled_data_types
            and self._must_refresh(
                self._last_daily_indicators_attempt,
                now,
            )
        ):
            attempted += 1
            self._last_daily_indicators_attempt = now
            try:
                await self._async_update_daily_indicators()
                succeeded += 1
            except ArpatApiError as err:
                self._daily_indicators["available"] = False
                _LOGGER.warning(
                    "Unable to update ARPAT daily indicators for %s: %s",
                    self.station,
                    err,
                )

        if (
            DATA_TYPE_DAILY_EXCEEDANCES in self.enabled_data_types
            and self._must_refresh(
                self._last_exceedances_attempt,
                now,
            )
        ):
            attempted += 1
            self._last_exceedances_attempt = now
            try:
                payload = await self.api.async_get_daily_exceedances(
                    self.station
                )
                self._exceedances = normalize_exceedances(payload)
                succeeded += 1
            except ArpatApiError as err:
                self._exceedances["available"] = False
                _LOGGER.warning(
                    "Unable to update ARPAT daily exceedances for %s: %s",
                    self.station,
                    err,
                )

        if attempted and succeeded == 0 and not self._has_cached_data():
            raise UpdateFailed(
                f"Unable to update selected ARPAT datasets for {self.station}"
            )

        return {
            "enabled_data_types": tuple(sorted(self.enabled_data_types)),
            "nrt": self._nrt,
            "daily_indicators": self._daily_indicators,
            "exceedances": self._exceedances,
        }

    async def _async_update_nrt(self) -> None:
        """Update NRT and discover only parameters actually published NRT."""
        if not self._nrt_initialized:
            try:
                history = await self.api.async_get_nrt_history(self.station)
            except ArpatApiError as err:
                # Il /last resta sufficiente per continuare. La discovery si
                # completerà con i valori numerici che appariranno nei refresh.
                _LOGGER.warning(
                    "Unable to load ARPAT NRT history for %s: %s",
                    self.station,
                    err,
                )
            else:
                self._nrt_parameters.update(
                    discover_nrt_parameters(history)
                )

            self._nrt_initialized = True

        record = await self.api.async_get_nrt_last(self.station)

        # Se compare in futuro un nuovo parametro NRT numerico, viene aggiunto
        # dinamicamente senza dover aggiornare l'integrazione.
        self._nrt_parameters.update(discover_nrt_parameters([record]))

        self._nrt = {
            "available": True,
            "record": record,
            "measurements": current_nrt_values(
                record,
                sorted(self._nrt_parameters),
            ),
        }

    async def _async_update_daily_indicators(self) -> None:
        """Update daily indicators from the latest regional bulletin."""
        record = await self.api.async_get_daily_indicators(self.station)
        current = normalize_daily_indicators(record)

        # Una volta individuato un indicatore pertinente alla stazione,
        # manteniamo l'entità stabile anche se un bollettino successivo lo
        # riporta temporaneamente come n.d. o non numerico.
        self._daily_indicator_parameters.update(current)

        measurements = {
            parameter: current.get(parameter)
            for parameter in sorted(self._daily_indicator_parameters)
        }

        self._daily_indicators = {
            "available": True,
            "record": record,
            "measurements": measurements,
        }

    @staticmethod
    def _must_refresh(
        last_attempt: datetime | None,
        now: datetime,
    ) -> bool:
        """Return True when a daily dataset should be refreshed."""
        if last_attempt is None:
            return True

        return now - last_attempt >= DAILY_UPDATE_INTERVAL

    def _has_cached_data(self) -> bool:
        """Return True when at least one selected dataset has usable cache."""
        if (
            DATA_TYPE_NRT in self.enabled_data_types
            and self._nrt.get("record")
        ):
            return True

        if (
            DATA_TYPE_DAILY_INDICATORS in self.enabled_data_types
            and self._daily_indicators.get("record")
        ):
            return True

        if (
            DATA_TYPE_DAILY_EXCEEDANCES in self.enabled_data_types
            and (
                self._exceedances.get("date") is not None
                or self._exceedances.get("count") is not None
            )
        ):
            return True

        return False
