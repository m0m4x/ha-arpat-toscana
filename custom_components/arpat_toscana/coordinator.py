"""Data coordinator for ARPAT Toscana."""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import ArpatApi, ArpatApiError
from .const import (
    EXCEEDANCES_REFRESH_INTERVAL,
    NRT_METADATA_FIELDS,
    POLLUTANT_INFO,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


def parse_numeric(value: Any) -> float | None:
    """Convert an ARPAT numeric value to float when possible."""
    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text or text in {"-", "--", "null", "None"}:
        return None

    try:
        return float(text.replace(",", "."))
    except ValueError:
        return None


def _get_case_insensitive(
    data: dict[str, Any],
    *keys: str,
) -> Any:
    """Return a dict value using case-insensitive key matching."""
    normalized = {str(key).lower(): value for key, value in data.items()}
    for key in keys:
        if key.lower() in normalized:
            return normalized[key.lower()]
    return None


class ArpatDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate ARPAT NRT and daily exceedance data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: ArpatApi,
        station: str,
        station_data: dict[str, Any],
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"ARPAT Toscana {station}",
            update_interval=UPDATE_INTERVAL,
        )
        self.api = api
        self.station = station
        self.station_data = station_data
        self._last_exceedances_attempt: datetime | None = None
        self._exceedances: dict[str, Any] = {
            "available": False,
            "count": None,
            "date": None,
            "records": [],
        }

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the latest ARPAT data."""
        try:
            nrt = await self.api.async_get_nrt_last(self.station)
        except ArpatApiError as err:
            raise UpdateFailed(
                f"Unable to update ARPAT NRT data for {self.station}"
            ) from err

        now = datetime.now(UTC)
        if self._must_refresh_exceedances(now):
            self._last_exceedances_attempt = now
            try:
                payload = await self.api.async_get_daily_exceedances(
                    self.station
                )
                self._exceedances = self._normalize_exceedances(payload)
            except ArpatApiError as err:
                # I dati NRT restano utili anche se il bollettino giornaliero
                # è temporaneamente indisponibile.
                _LOGGER.warning(
                    "Unable to update ARPAT daily exceedances for %s: %s",
                    self.station,
                    err,
                )

        pollutants = self._discover_pollutants(nrt)

        return {
            "nrt": nrt,
            "pollutants": tuple(sorted(pollutants)),
            "exceedances": self._exceedances,
        }

    def _must_refresh_exceedances(self, now: datetime) -> bool:
        """Return True when daily exceedances should be refreshed."""
        if self._last_exceedances_attempt is None:
            return True
        return (
            now - self._last_exceedances_attempt
            >= EXCEEDANCES_REFRESH_INTERVAL
        )

    def _discover_pollutants(self, nrt: dict[str, Any]) -> set[str]:
        """Discover station measurements from network metadata and NRT."""
        pollutants: set[str] = set()

        declared = self.station_data.get("SENSORI", [])
        if isinstance(declared, list):
            for item in declared:
                name = str(item).strip().upper()
                if name:
                    pollutants.add(name)

        for key, value in nrt.items():
            name = str(key).strip().upper()

            if not name or name in NRT_METADATA_FIELDS:
                continue

            # Campi conosciuti vengono pubblicati anche se il campione corrente
            # è null; campi futuri/sconosciuti vengono aggiunti se numerici.
            if name in POLLUTANT_INFO or parse_numeric(value) is not None:
                pollutants.add(name)

        return pollutants

    @staticmethod
    def _normalize_exceedances(
        payload: dict[str, Any] | list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Normalize the two ARPAT exceedance response shapes."""
        if isinstance(payload, dict):
            count_raw = _get_case_insensitive(payload, "superamenti")

            # Risposta documentata quando non ci sono superamenti.
            if count_raw is not None:
                count = parse_numeric(count_raw)
                date = _get_case_insensitive(
                    payload,
                    "data_osservazione",
                    "DATA_OSSERVAZIONE",
                )

                return {
                    "available": True,
                    "count": int(count) if count is not None else 0,
                    "date": date,
                    "records": [],
                }

            # Difesa da un eventuale singolo record restituito come oggetto.
            if (
                _get_case_insensitive(payload, "NOME_PARAMETRO") is not None
                or _get_case_insensitive(payload, "SIGLA_PARAMETRO") is not None
            ):
                payload = [payload]
            else:
                return {
                    "available": False,
                    "count": None,
                    "date": None,
                    "records": [],
                }

        if not payload:
            return {
                "available": False,
                "count": None,
                "date": None,
                "records": [],
            }

        records: list[dict[str, Any]] = []
        observation_date: Any = None

        for item in payload:
            date = _get_case_insensitive(item, "DATA_OSSERVAZIONE")
            if observation_date is None:
                observation_date = date

            raw_value = _get_case_insensitive(item, "VALORE")
            numeric_value = parse_numeric(raw_value)

            records.append(
                {
                    "parametro": _get_case_insensitive(
                        item,
                        "NOME_PARAMETRO",
                    ),
                    "sigla": _get_case_insensitive(
                        item,
                        "SIGLA_PARAMETRO",
                    ),
                    "valore": (
                        numeric_value
                        if numeric_value is not None
                        else raw_value
                    ),
                    "data_osservazione": date,
                }
            )

        return {
            "available": True,
            "count": len(records),
            "date": observation_date,
            "records": records,
        }
