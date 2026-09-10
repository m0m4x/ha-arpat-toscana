"""Pure parsing helpers for ARPAT Toscana payloads."""

from __future__ import annotations

from typing import Any, Iterable

from .const import (
    DAILY_METADATA_FIELDS,
    DAILY_NOT_APPLICABLE_VALUES,
    DAILY_NOT_AVAILABLE_VALUES,
    NRT_METADATA_FIELDS,
    PARAMETER_ALIASES,
)


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


def canonical_parameter(value: str) -> str:
    """Return a stable parameter name across the ARPAT datasets."""
    name = str(value).strip().upper()
    return PARAMETER_ALIASES.get(name, name)


def get_case_insensitive(data: dict[str, Any], *keys: str) -> Any:
    """Return a dict value using case-insensitive key matching."""
    normalized = {str(key).lower(): value for key, value in data.items()}

    for key in keys:
        if key.lower() in normalized:
            return normalized[key.lower()]

    return None


def discover_nrt_parameters(
    records: Iterable[dict[str, Any]],
) -> set[str]:
    """Discover parameters that actually published numeric NRT data."""
    parameters: set[str] = set()

    for record in records:
        for key, value in record.items():
            raw_name = str(key).strip().upper()

            if not raw_name or raw_name in NRT_METADATA_FIELDS:
                continue

            if parse_numeric(value) is not None:
                parameters.add(canonical_parameter(raw_name))

    return parameters


def current_nrt_values(
    record: dict[str, Any],
    parameters: Iterable[str],
) -> dict[str, float | None]:
    """Return current NRT values for the already discovered parameters."""
    raw_values = {
        canonical_parameter(str(key)): value
        for key, value in record.items()
        if str(key).strip().upper() not in NRT_METADATA_FIELDS
    }

    return {
        parameter: parse_numeric(raw_values.get(parameter))
        for parameter in parameters
    }


def normalize_daily_indicators(
    record: dict[str, Any],
) -> dict[str, float | None]:
    """Normalize indicators published in a regional daily bulletin row."""
    indicators: dict[str, float | None] = {}

    for key, value in record.items():
        raw_name = str(key).strip().upper()

        if not raw_name or raw_name in DAILY_METADATA_FIELDS:
            continue

        parameter = canonical_parameter(raw_name)
        text = "" if value is None else str(value).strip()
        lowered = text.lower()

        if text in DAILY_NOT_APPLICABLE_VALUES:
            continue

        numeric = parse_numeric(value)
        if numeric is not None:
            indicators[parameter] = numeric
            continue

        # ARPAT usa "n.d." per indicare un indicatore pertinente alla
        # stazione ma non disponibile nel bollettino considerato.
        if value is None or lowered in DAILY_NOT_AVAILABLE_VALUES:
            indicators[parameter] = None

    return indicators


def normalize_exceedances(
    payload: dict[str, Any] | list[dict[str, Any]],
) -> dict[str, Any]:
    """Normalize ARPAT daily exceedance payload variants."""
    if isinstance(payload, dict):
        count_raw = get_case_insensitive(payload, "superamenti")

        if count_raw is not None:
            count = parse_numeric(count_raw)
            date = get_case_insensitive(
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

        if (
            get_case_insensitive(payload, "NOME_PARAMETRO") is not None
            or get_case_insensitive(payload, "SIGLA_PARAMETRO") is not None
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
        date = get_case_insensitive(item, "DATA_OSSERVAZIONE")
        if observation_date is None:
            observation_date = date

        raw_value = get_case_insensitive(item, "VALORE")
        numeric_value = parse_numeric(raw_value)

        records.append(
            {
                "parametro": get_case_insensitive(item, "NOME_PARAMETRO"),
                "sigla": get_case_insensitive(item, "SIGLA_PARAMETRO"),
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
