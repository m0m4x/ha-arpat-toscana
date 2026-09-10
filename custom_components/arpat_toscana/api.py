"""Async client for ARPAT Toscana Open Data."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import (
    BASE_URL,
    DAILY_BULLETIN_PATH,
    EXCEEDANCES_PATH,
    NETWORK_PATH,
    NRT_HISTORY_PATH,
    NRT_LAST_PATH,
    REQUEST_TIMEOUT_SECONDS,
)


class ArpatApiError(Exception):
    """Base exception for ARPAT API errors."""


class ArpatApi:
    """Client for the public ARPAT Toscana Open Data endpoints."""

    def __init__(self, session: ClientSession) -> None:
        """Initialize the API client."""
        self._session = session

    async def async_get_stations(self) -> list[dict[str, Any]]:
        """Return stations from the regional monitoring network."""
        payload = await self._async_get_json(NETWORK_PATH)

        if not isinstance(payload, list):
            raise ArpatApiError("Unexpected station network response")

        stations = [
            item
            for item in payload
            if isinstance(item, dict) and item.get("NOME_STAZIONE")
        ]

        if not stations:
            raise ArpatApiError("No stations returned by ARPAT")

        unique: dict[str, dict[str, Any]] = {}
        for station in stations:
            name = str(station["NOME_STAZIONE"]).strip().upper()
            unique[name] = station

        return sorted(
            unique.values(),
            key=lambda item: (
                str(item.get("PROVINCIA", "")),
                str(item.get("COMUNE", "")),
                str(item.get("NOME_STAZIONE", "")),
            ),
        )

    async def async_get_nrt_history(
        self,
        station: str,
    ) -> list[dict[str, Any]]:
        """Return all currently available NRT records for a station."""
        station_url = quote(station, safe="-")
        payload = await self._async_get_json(
            NRT_HISTORY_PATH.format(station=station_url)
        )

        if not isinstance(payload, list):
            raise ArpatApiError(
                f"Unexpected NRT history response for station {station}"
            )

        return [item for item in payload if isinstance(item, dict)]

    async def async_get_nrt_last(self, station: str) -> dict[str, Any]:
        """Return the latest NRT sample for a station."""
        station_url = quote(station, safe="-")
        payload = await self._async_get_json(
            NRT_LAST_PATH.format(station=station_url)
        )

        if isinstance(payload, list):
            records = [item for item in payload if isinstance(item, dict)]
            if not records:
                raise ArpatApiError(
                    f"No NRT data returned for station {station}"
                )
            return records[-1]

        if isinstance(payload, dict):
            return payload

        raise ArpatApiError(
            f"Unexpected NRT response for station {station}"
        )

    async def async_get_latest_regional_bulletin(
        self,
    ) -> list[dict[str, Any]]:
        """Return the latest regional air-quality bulletin."""
        payload = await self._async_get_json(DAILY_BULLETIN_PATH)

        if not isinstance(payload, list):
            raise ArpatApiError("Unexpected regional bulletin response")

        return [item for item in payload if isinstance(item, dict)]

    async def async_get_daily_indicators(
        self,
        station: str,
    ) -> dict[str, Any]:
        """Return the station row from the latest regional bulletin."""
        bulletin = await self.async_get_latest_regional_bulletin()
        wanted = station.strip().upper()

        for item in bulletin:
            station_name = str(item.get("NOME_STAZIONE", "")).strip().upper()
            if station_name == wanted:
                return item

        raise ArpatApiError(
            f"Station {station} not found in latest regional bulletin"
        )

    async def async_get_daily_exceedances(
        self,
        station: str,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Return daily exceedances from the latest bulletin."""
        station_url = quote(station, safe="-")
        payload = await self._async_get_json(
            EXCEEDANCES_PATH.format(station=station_url)
        )

        if isinstance(payload, dict):
            return payload

        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]

        raise ArpatApiError(
            f"Unexpected exceedances response for station {station}"
        )

    async def _async_get_json(self, path: str) -> Any:
        """GET a JSON endpoint and return the decoded payload."""
        url = f"{BASE_URL}/{path.lstrip('/')}"

        try:
            async with self._session.get(
                url,
                timeout=ClientTimeout(total=REQUEST_TIMEOUT_SECONDS),
                headers={"Accept": "application/json"},
            ) as response:
                response.raise_for_status()
                return await response.json(content_type=None)
        except (ClientError, TimeoutError, ValueError) as err:
            raise ArpatApiError(f"ARPAT request failed: {url}") from err
