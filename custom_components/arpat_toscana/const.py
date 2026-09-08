"""Constants for the ARPAT Toscana integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "arpat_toscana"

CONF_STATION: Final = "station"
CONF_STATION_DATA: Final = "station_data"

NAME: Final = "ARPAT Toscana"

BASE_URL: Final = (
    "https://opendata.arpat.toscana.it/"
    "temi-ambientali/aria/qualita-aria"
)
NETWORK_PATH: Final = "rete_monitoraggio/rete_json/regionale"
NRT_PATH: Final = "dati_orari_real_time/json_orari_nrt/{station}/last"
EXCEEDANCES_PATH: Final = "bollettini/superamenti_json/-/{station}"

UPDATE_INTERVAL: Final = timedelta(minutes=30)
EXCEEDANCES_REFRESH_INTERVAL: Final = timedelta(hours=2)
REQUEST_TIMEOUT_SECONDS: Final = 20

# Campi del payload NRT che descrivono il campione o la stazione e non
# rappresentano una misura da pubblicare come sensore Home Assistant.
NRT_METADATA_FIELDS: Final = {
    "ORA",
    "PROVINCIA",
    "COMUNE",
    "NOME_STAZIONE",
    "NOME_RETE",
    "NOME_AGGLOMERATO",
    "VALIDAZIONE",
    "DATA_AGGIORNAMENTO",
    "DATA_OSSERVAZIONE",
    "STR_DATA_OSSERVAZIONE",
    "NUM_DATA",
    "COD_STAZIONE",
    "TIPO_ZONA",
    "TIPO_STAZIONE",
    "FLAG_REGIONALE",
    "COORDINATE_EGB",
    "COORDINATE_NGB",
    "SENSORI",
}

# Metadati noti dei parametri. Per campi NRT nuovi o non documentati
# l'integrazione crea comunque l'entità senza inventare unità o significati.
POLLUTANT_INFO: Final = {
    "PM10": {
        "name": "PM10",
        "unit": "µg/m³",
        "icon": "mdi:blur",
    },
    "PM2.5": {
        "name": "PM2.5",
        "unit": "µg/m³",
        "icon": "mdi:blur",
    },
    "PM1": {
        "name": "PM1",
        "unit": "µg/m³",
        "icon": "mdi:blur",
    },
    "PM4": {
        "name": "PM4",
        "unit": "µg/m³",
        "icon": "mdi:blur",
    },
    "NO2": {
        "name": "NO₂",
        "unit": "µg/m³",
        "icon": "mdi:molecule",
    },
    "O3": {
        "name": "O₃",
        "unit": "µg/m³",
        "icon": "mdi:molecule",
    },
    "SO2": {
        "name": "SO₂",
        "unit": "µg/m³",
        "icon": "mdi:molecule",
    },
    "CO": {
        "name": "CO",
        "unit": "mg/m³",
        "icon": "mdi:molecule-co",
    },
    "H2S": {
        "name": "H₂S",
        "unit": "µg/m³",
        "icon": "mdi:molecule",
    },
    "BENZENE": {
        "name": "Benzene",
        "unit": "µg/m³",
        "icon": "mdi:chemical-weapon",
    },
    "C6H6": {
        "name": "Benzene",
        "unit": "µg/m³",
        "icon": "mdi:chemical-weapon",
    },
    "BC": {
        "name": "Black Carbon",
        # Il JSON NRT non documenta esplicitamente l'unità di questo campo.
        "unit": None,
        "icon": "mdi:blur",
    },
    "BB": {
        "name": "Biomass Burning",
        "unit": "%",
        "icon": "mdi:fire",
    },
}
