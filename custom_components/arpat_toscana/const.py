"""Constants for the ARPAT Toscana integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "arpat_toscana"
NAME: Final = "ARPAT Toscana"

CONF_STATION: Final = "station"
CONF_STATION_DATA: Final = "station_data"
CONF_DATA_TYPES: Final = "data_types"

DATA_TYPE_NRT: Final = "nrt"
DATA_TYPE_DAILY_INDICATORS: Final = "daily_indicators"
DATA_TYPE_DAILY_EXCEEDANCES: Final = "daily_exceedances"

ALL_DATA_TYPES: Final = (
    DATA_TYPE_NRT,
    DATA_TYPE_DAILY_INDICATORS,
    DATA_TYPE_DAILY_EXCEEDANCES,
)

# Nuove configurazioni: tutte le tipologie sono proposte e selezionabili.
DEFAULT_DATA_TYPES: Final = ALL_DATA_TYPES

# Migrazione dalla 0.1.x: conserva esattamente le due sorgenti già presenti.
LEGACY_DEFAULT_DATA_TYPES: Final = (
    DATA_TYPE_NRT,
    DATA_TYPE_DAILY_EXCEEDANCES,
)

BASE_URL: Final = (
    "https://opendata.arpat.toscana.it/"
    "temi-ambientali/aria/qualita-aria"
)
NETWORK_PATH: Final = "rete_monitoraggio/rete_json/regionale"
NRT_HISTORY_PATH: Final = "dati_orari_real_time/json_orari_nrt/{station}"
NRT_LAST_PATH: Final = "dati_orari_real_time/json_orari_nrt/{station}/last"
DAILY_BULLETIN_PATH: Final = "bollettini/bollettino_json/regionale"
EXCEEDANCES_PATH: Final = "bollettini/superamenti_json/-/{station}"

NRT_UPDATE_INTERVAL: Final = timedelta(minutes=30)
DAILY_UPDATE_INTERVAL: Final = timedelta(hours=2)
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

# Campi descrittivi del bollettino regionale. CONTATORE_SUPERAMENTI viene
# conservato come attributo del dato giornaliero, ma non viene trasformato in
# sensore fino a quando non ne definiamo esplicitamente la semantica.
DAILY_METADATA_FIELDS: Final = {
    "DATA_OSSERVAZIONE",
    "NOME_AGGLOMERATO",
    "NUMERO_RIGHE_AGGLOMERATO",
    "CONTATORE_SUPERAMENTI",
    "PROVINCIA",
    "COMUNE",
    "NOME_STAZIONE",
    "TIPO_ZONA",
    "TIPO_STAZIONE",
    "TIPO",
    "OPERATORE_NOME",
}

DAILY_NOT_APPLICABLE_VALUES: Final = {"-", "--"}
DAILY_NOT_AVAILABLE_VALUES: Final = {"n.d.", "n.d", "nd", "n/d"}

# Normalizzazione delle sigle che ARPAT rappresenta in modo diverso nei vari
# dataset.
PARAMETER_ALIASES: Final = {
    "PM2DOT5": "PM2.5",
    "C6H6": "BENZENE",
}

# Metadati noti dei parametri. Per campi nuovi o non documentati l'integrazione
# crea comunque l'entità numerica senza inventare unità o significato.
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
    "BC": {
        "name": "Black Carbon",
        # Il tracciato Open Data NRT non documenta esplicitamente l'unità.
        "unit": None,
        "icon": "mdi:blur",
    },
    "BB": {
        "name": "Biomass Burning",
        "unit": "%",
        "icon": "mdi:fire",
    },
}
