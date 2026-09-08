"""Sensor platform for ARPAT Toscana."""

from __future__ import annotations

import re
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, POLLUTANT_INFO
from .coordinator import ArpatDataUpdateCoordinator, parse_numeric


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ARPAT Toscana sensors."""
    coordinator: ArpatDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    created: set[str] = set()

    def async_add_new_pollutants() -> None:
        """Add entities for pollutants discovered after setup."""
        current = set(coordinator.data.get("pollutants", ()))
        new_keys = sorted(current - created)

        if not new_keys:
            return

        async_add_entities(
            [
                ArpatNrtSensor(coordinator, pollutant)
                for pollutant in new_keys
            ]
        )
        created.update(new_keys)

    # Sensore persistente per il dataset dei superamenti giornalieri.
    async_add_entities([ArpatDailyExceedancesSensor(coordinator)])

    # Sensori NRT iniziali e discovery di eventuali nuovi campi futuri.
    async_add_new_pollutants()
    entry.async_on_unload(
        coordinator.async_add_listener(async_add_new_pollutants)
    )


class ArpatBaseSensor(
    CoordinatorEntity[ArpatDataUpdateCoordinator],
    SensorEntity,
):
    """Base ARPAT sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ArpatDataUpdateCoordinator,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._station = coordinator.station
        self._station_data = coordinator.station_data

    @property
    def device_info(self) -> DeviceInfo:
        """Return the ARPAT station as a Home Assistant device."""
        station_slug = self._station.lower()
        return DeviceInfo(
            identifiers={(DOMAIN, self._station)},
            name=f"ARPAT {self._station}",
            manufacturer="ARPAT",
            model="Rete regionale qualità dell'aria",
            configuration_url=(
                f"https://www.arpat.toscana.it/stazione/{station_slug}/"
            ),
        )

    def _common_attributes(self) -> dict[str, Any]:
        """Return common station metadata."""
        nrt = self.coordinator.data.get("nrt", {})
        return {
            "stazione": self._station,
            "codice_stazione": self._station_data.get("COD_STAZIONE"),
            "comune": self._station_data.get("COMUNE")
            or nrt.get("COMUNE"),
            "provincia": self._station_data.get("PROVINCIA")
            or nrt.get("PROVINCIA"),
            "zona": self._station_data.get("NOME_AGGLOMERATO"),
            "tipo_zona": self._station_data.get("TIPO_ZONA"),
            "tipo_stazione": self._station_data.get("TIPO_STAZIONE"),
            "validazione": nrt.get("VALIDAZIONE"),
            "data_osservazione": (
                nrt.get("STR_DATA_OSSERVAZIONE")
                or nrt.get("DATA_OSSERVAZIONE")
            ),
            "ora": nrt.get("ORA"),
            "data_aggiornamento": nrt.get("DATA_AGGIORNAMENTO"),
            "ora_solare": True,
            "fonte": "ARPAT Toscana Open Data",
        }


class ArpatNrtSensor(ArpatBaseSensor):
    """A dynamically discovered ARPAT NRT measurement."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: ArpatDataUpdateCoordinator,
        pollutant: str,
    ) -> None:
        """Initialize an NRT sensor."""
        super().__init__(coordinator)

        self._pollutant = pollutant
        info = POLLUTANT_INFO.get(pollutant, {})

        self._attr_unique_id = (
            f"{self._station}_{_slugify(pollutant)}"
        )
        self._attr_name = str(info.get("name") or pollutant)
        self._attr_native_unit_of_measurement = info.get("unit")
        self._attr_icon = str(info.get("icon") or "mdi:gauge")

    @property
    def native_value(self) -> float | None:
        """Return the current ARPAT NRT value."""
        nrt = self.coordinator.data.get("nrt", {})

        value = nrt.get(self._pollutant)
        if value is None:
            # Difesa da variazioni di maiuscole/minuscole dell'API.
            for key, candidate in nrt.items():
                if str(key).strip().upper() == self._pollutant:
                    value = candidate
                    break

        return parse_numeric(value)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return source and observation metadata."""
        attributes = self._common_attributes()
        attributes["parametro_arpat"] = self._pollutant
        return attributes


class ArpatDailyExceedancesSensor(ArpatBaseSensor):
    """Number of daily exceedances in the latest ARPAT bulletin."""

    _attr_name = "Superamenti giornalieri"
    _attr_icon = "mdi:alert-circle-outline"

    def __init__(
        self,
        coordinator: ArpatDataUpdateCoordinator,
    ) -> None:
        """Initialize the daily exceedances sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._station}_superamenti_giornalieri"

    @property
    def available(self) -> bool:
        """Return whether the latest bulletin data is available."""
        exceedances = self.coordinator.data.get("exceedances", {})
        return (
            self.coordinator.last_update_success
            and bool(exceedances.get("available"))
        )

    @property
    def native_value(self) -> int | None:
        """Return the number of exceedances in the latest bulletin."""
        value = self.coordinator.data.get("exceedances", {}).get("count")
        return int(value) if value is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return details of daily exceedances."""
        exceedances = self.coordinator.data.get("exceedances", {})
        attributes = self._common_attributes()
        attributes.update(
            {
                "data_bollettino": exceedances.get("date"),
                "dettaglio_superamenti": exceedances.get("records", []),
            }
        )
        return attributes


def _slugify(value: str) -> str:
    """Create a stable unique-id fragment."""
    value = value.lower().replace(".", "_")
    return re.sub(r"[^a-z0-9_]+", "_", value).strip("_")
