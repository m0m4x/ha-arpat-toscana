"""Tests for ARPAT Toscana pure payload parsers."""

from custom_components.arpat_toscana.parsers import (
    current_nrt_values,
    discover_nrt_parameters,
    normalize_daily_indicators,
    normalize_exceedances,
)


def test_nrt_ignores_null_schema_fields() -> None:
    payload = [
        {
            "ORA": "23",
            "PM10": None,
            "PM2.5": None,
            "NO2": "7",
            "O3": "41",
            "SO2": None,
            "CO": None,
            "NOME_STAZIONE": "PT-MONTALE",
        }
    ]

    assert discover_nrt_parameters(payload) == {"NO2", "O3"}


def test_current_nrt_keeps_real_parameter_unknown_when_last_is_null() -> None:
    record = {"NO2": None, "O3": "41"}

    assert current_nrt_values(record, {"NO2", "O3"}) == {
        "NO2": None,
        "O3": 41.0,
    }


def test_daily_indicator_normalization() -> None:
    record = {
        "PM10": "18",
        "PM2dot5": "9",
        "NO2": "32",
        "SO2": "-",
        "CO": "n.d.",
        "CONTATORE_SUPERAMENTI": "4",
        "NOME_STAZIONE": "PT-MONTALE",
    }

    assert normalize_daily_indicators(record) == {
        "PM10": 18.0,
        "PM2.5": 9.0,
        "NO2": 32.0,
        "CO": None,
    }


def test_zero_exceedances() -> None:
    payload = {
        "None_stazione": "PT-MONTALE",
        "data_osservazione": "07/09/2026",
        "superamenti": 0,
    }

    normalized = normalize_exceedances(payload)
    assert normalized["available"] is True
    assert normalized["count"] == 0
    assert normalized["date"] == "07/09/2026"
