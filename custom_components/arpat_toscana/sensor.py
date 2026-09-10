"""Sensor platform for ARPAT Toscana."""

from __future__ import annotations

import re
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DATA_TYPE_DAILY_EXCEEDANCES,
    DATA_TYPE_DAILY_INDICATORS,
    DATA_TYPE_NRT,
    DOMAIN,
    POLLUTANT_INFO,
)
from .coordinator import ArpatDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ARPAT Toscana sensors."""
    coordinator: ArpatDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    created: set[str] = set()

    _cleanup_legacy_and_disabled_entities(hass, entry, coordinator)

    def async_add_new_entities() -> None:
        """Add entities discovered after initial setup."""
        entities: list[SensorEntity] = []

        if DATA_TYPE_NRT in coordinator.enabled_data_types:
            measurements = coordinator.data.get("nrt", {}).get(
                "measurements", {}
            )
            for parameter in sorted(measurements):
                unique_id = _nrt_unique_id(coordinator.station, parameter)
                if unique_id in created:
                    continue
                created.add(unique_id)
                entities.append(ArpatNrtSensor(coordinator, parameter))

        if DATA_TYPE_DAILY_INDICATORS in coordinator.enabled_data_types:
            measurements = coordinator.data.get("daily_indicators", {}).get(
                "measurements", {}
            )
            for parameter in sorted(measurements):
                unique_id = _daily_unique_id(
                    coordinator.station,
                    parameter,
                )
                if unique_id in created:
                    continue
                created.add(unique_id)
                entities.append(
                    ArpatDailyIndicatorSensor(coordinator, parameter)
                )

        if DATA_TYPE_DAILY_EXCEEDANCES in coordinator.enabled_data_types:
            unique_id = _exceedances_unique_id(coordinator.station)
            if unique_id not in created:
                created.add(unique_id)
                entities.append(ArpatDailyExceedancesSensor(coordinator))

        if entities:
            async_add_entities(entities)

    async_add_new_entities()
    entry.async_on_unload(
        coordinator.async_add_listener(async_add_new_entities)
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
        return DeviceInfo(
            identifiers={(DOMAIN, self._station)},
            name=f"ARPAT {self._station}",
            manufacturer="ARPAT",
            model="Rete Regionale di Monitoraggio della Qualità dell'Aria",
            configuration_url=(
                "https://www.arpat.toscana.it/dati-in-tempo-reale/"
            ),
        )

    def _station_attributes(self) -> dict[str, Any]:
        """Return common station metadata."""
        return {
            "stazione": self._station,
            "codice_stazione": self._station_data.get("COD_STAZIONE"),
            "comune": self._station_data.get("COMUNE"),
            "provincia": self._station_data.get("PROVINCIA"),
            "zona": self._station_data.get("NOME_AGGLOMERATO"),
            "tipo_zona": self._station_data.get("TIPO_ZONA"),
            "tipo_stazione": self._station_data.get("TIPO_STAZIONE"),
            "fonte": "ARPAT Toscana Open Data",
        }


class ArpatNrtSensor(ArpatBaseSensor):
    """An ARPAT Near Real Time measurement."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: ArpatDataUpdateCoordinator,
        parameter: str,
    ) -> None:
        """Initialize an NRT sensor."""
        super().__init__(coordinator)

        self._parameter = parameter
        info = POLLUTANT_INFO.get(parameter, {})

        self._attr_unique_id = _nrt_unique_id(self._station, parameter)
        self._attr_name = f"{info.get('name') or parameter} NRT"
        self._attr_native_unit_of_measurement = info.get("unit")
        self._attr_icon = str(info.get("icon") or "mdi:gauge")

    @property
    def available(self) -> bool:
        """Return whether the NRT dataset is currently reachable."""
        nrt = self.coordinator.data.get("nrt", {})
        return self.coordinator.last_update_success and bool(
            nrt.get("available")
        )

    @property
    def native_value(self) -> float | None:
        """Return the latest NRT value."""
        return self.coordinator.data.get("nrt", {}).get(
            "measurements", {}
        ).get(self._parameter)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return NRT source and observation metadata."""
        record = self.coordinator.data.get("nrt", {}).get("record", {})
        attributes = self._station_attributes()
        attributes.update(
            {
                "tipologia_dato": "Dati orari Near Real Time (NRT)",
                "parametro_arpat": self._parameter,
                "validazione": record.get("VALIDAZIONE"),
                "data_osservazione": (
                    record.get("STR_DATA_OSSERVAZIONE")
                    or record.get("DATA_OSSERVAZIONE")
                ),
                "ora": record.get("ORA"),
                "data_aggiornamento": record.get("DATA_AGGIORNAMENTO"),
                "ora_solare": True,
            }
        )
        return attributes


class ArpatDailyIndicatorSensor(ArpatBaseSensor):
    """An indicator from the latest ARPAT regional daily bulletin."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: ArpatDataUpdateCoordinator,
        parameter: str,
    ) -> None:
        """Initialize a daily indicator sensor."""
        super().__init__(coordinator)

        self._parameter = parameter
        info = POLLUTANT_INFO.get(parameter, {})

        self._attr_unique_id = _daily_unique_id(self._station, parameter)
        self._attr_name = (
            f"{info.get('name') or parameter} indicatore giornaliero"
        )
        self._attr_native_unit_of_measurement = info.get("unit")
        self._attr_icon = str(info.get("icon") or "mdi:chart-line")

    @property
    def available(self) -> bool:
        """Return whether the daily bulletin is currently reachable."""
        daily = self.coordinator.data.get("daily_indicators", {})
        return self.coordinator.last_update_success and bool(
            daily.get("available")
        )

    @property
    def native_value(self) -> float | None:
        """Return the latest published daily indicator."""
        return self.coordinator.data.get("daily_indicators", {}).get(
            "measurements", {}
        ).get(self._parameter)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return daily bulletin metadata."""
        record = self.coordinator.data.get("daily_indicators", {}).get(
            "record", {}
        )
        attributes = self._station_attributes()
        attributes.update(
            {
                "tipologia_dato": "Indicatori giornalieri",
                "parametro_arpat": self._parameter,
                "data_osservazione": record.get("DATA_OSSERVAZIONE"),
                "validazione": "primo livello",
                "operatore": record.get("OPERATORE_NOME"),
            }
        )

        counter = record.get("CONTATORE_SUPERAMENTI")
        if counter not in (None, "", "-", "--"):
            attributes["contatore_superamenti"] = counter

        return attributes


class ArpatDailyExceedancesSensor(ArpatBaseSensor):
    """Number of exceedances in the latest ARPAT daily publication."""

    _attr_name = "Superamenti limiti giornalieri"
    _attr_icon = "mdi:alert-circle-outline"

    def __init__(
        self,
        coordinator: ArpatDataUpdateCoordinator,
    ) -> None:
        """Initialize the daily exceedances sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = _exceedances_unique_id(self._station)

    @property
    def available(self) -> bool:
        """Return whether the latest exceedance data is available."""
        exceedances = self.coordinator.data.get("exceedances", {})
        return self.coordinator.last_update_success and bool(
            exceedances.get("available")
        )

    @property
    def native_value(self) -> int | None:
        """Return the number of exceedances in the latest publication."""
        value = self.coordinator.data.get("exceedances", {}).get("count")
        return int(value) if value is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return details of the daily exceedances."""
        exceedances = self.coordinator.data.get("exceedances", {})
        attributes = self._station_attributes()
        attributes.update(
            {
                "tipologia_dato": "Superamenti limiti giornalieri",
                "data_bollettino": exceedances.get("date"),
                "dettaglio_superamenti": exceedances.get("records", []),
            }
        )
        return attributes


def _nrt_unique_id(station: str, parameter: str) -> str:
    """Return a unique id for an NRT parameter."""
    return f"{station}_nrt_{_slugify(parameter)}"


def _daily_unique_id(station: str, parameter: str) -> str:
    """Return a unique id for a daily indicator."""
    return f"{station}_daily_{_slugify(parameter)}"


def _exceedances_unique_id(station: str) -> str:
    """Return the unique id for daily exceedances."""
    return f"{station}_superamenti_giornalieri"


def _slugify(value: str) -> str:
    """Create a stable unique-id fragment."""
    value = value.lower().replace(".", "_")
    return re.sub(r"[^a-z0-9_]+", "_", value).strip("_")


def _cleanup_legacy_and_disabled_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: ArpatDataUpdateCoordinator,
) -> None:
    """Remove 0.1.x entities and entities for disabled dataset types."""
    registry = er.async_get(hass)
    prefix = f"{coordinator.station}_"
    nrt_prefix = f"{coordinator.station}_nrt_"
    daily_prefix = f"{coordinator.station}_daily_"
    exceedances_id = _exceedances_unique_id(coordinator.station)

    for registry_entry in er.async_entries_for_config_entry(
        registry,
        entry.entry_id,
    ):
        if registry_entry.domain != "sensor" or registry_entry.platform != DOMAIN:
            continue

        unique_id = registry_entry.unique_id
        remove = False

        if not unique_id.startswith(prefix):
            continue

        # Unique-id 0.1.x: STAZIONE_parametro, senza categoria dataset.
        is_legacy = (
            not unique_id.startswith(nrt_prefix)
            and not unique_id.startswith(daily_prefix)
            and unique_id != exceedances_id
        )

        if is_legacy:
            remove = True
        elif (
            unique_id.startswith(nrt_prefix)
            and DATA_TYPE_NRT not in coordinator.enabled_data_types
        ):
            remove = True
        elif (
            unique_id.startswith(daily_prefix)
            and DATA_TYPE_DAILY_INDICATORS
            not in coordinator.enabled_data_types
        ):
            remove = True
        elif (
            unique_id == exceedances_id
            and DATA_TYPE_DAILY_EXCEEDANCES
            not in coordinator.enabled_data_types
        ):
            remove = True

        if remove:
            registry.async_remove(registry_entry.entity_id)
