# ARPAT Toscana per Home Assistant

[![GitHub release](https://img.shields.io/github/v/release/m0m4x/ha-arpat-toscana?display_name=tag)](https://github.com/m0m4x/ha-arpat-toscana/releases)
[![HACS validation](https://github.com/m0m4x/ha-arpat-toscana/actions/workflows/validate.yml/badge.svg)](https://github.com/m0m4x/ha-arpat-toscana/actions/workflows/validate.yml)
[![hassfest](https://github.com/m0m4x/ha-arpat-toscana/actions/workflows/hassfest.yml/badge.svg)](https://github.com/m0m4x/ha-arpat-toscana/actions/workflows/hassfest.yml)

Custom integration per Home Assistant per acquisire i dati della **qualità dell'aria** pubblicati da **ARPAT - Agenzia regionale per la protezione ambientale della Toscana** tramite gli Open Data ufficiali.

La prima versione si concentra su:

- **Dati orari Near Real Time (NRT)** della stazione scelta;
- **Superamenti dei limiti giornalieri** riportati nell'ultimo bollettino disponibile.

> **Progetto indipendente e non ufficiale.** Non è sviluppato, approvato o supportato da ARPAT.

## Installazione con HACS

Premi il pulsante seguente per aprire direttamente questo repository in HACS:

[![Apri ARPAT Toscana in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=m0m4x&repository=ha-arpat-toscana&category=integration)

Dopo aver installato l'integrazione da HACS e riavviato Home Assistant:

[![Aggiungi ARPAT Toscana a Home Assistant](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=arpat_toscana)

## Configurazione

Da **Impostazioni → Dispositivi e servizi → Aggiungi integrazione**, cerca **ARPAT Toscana**.

L'integrazione scarica l'elenco aggiornato delle stazioni della rete regionale direttamente dall'Open Data ARPAT e mostra una selezione del tipo:

```text
Firenze (Firenze) — FI-LAVAGNINI · BENZENE, CO, NO2, PM10, PM2.5
Capannori (Lucca) — LU-CAPANNORI · SO2, NO2, PM10, PM2.5
...
```

Non è necessario conoscere o inserire manualmente il codice numerico della centralina.

È possibile configurare più stazioni; ogni stazione viene rappresentata come un dispositivo Home Assistant separato.

## Sensori NRT dinamici

Per la stazione selezionata l'integrazione crea automaticamente un'entità per ciascun parametro disponibile.

L'autodiscovery usa l'unione di:

1. `SENSORI` dichiarati dal dataset della rete;
2. campi numerici effettivamente pubblicati nel payload NRT.

Questo è importante perché ARPAT può pubblicare nel NRT misure aggiuntive che non risultano nell'array `SENSORI` della struttura di rete.

Esempi di parametri gestiti:

| Parametro | Unità |
| --- | --- |
| PM10 | µg/m³ |
| PM2.5 | µg/m³ |
| NO₂ | µg/m³ |
| O₃ | µg/m³ |
| SO₂ | µg/m³ |
| CO | mg/m³ |
| H₂S | µg/m³ |
| Benzene | µg/m³ |
| BB - Biomass Burning | % |
| BC - Black Carbon | valore ARPAT, senza unità forzata |

Per campi NRT futuri o non documentati viene comunque creata l'entità, ma senza inventarne unità o significato.

Ogni sensore NRT espone inoltre attributi come:

- stazione;
- codice stazione;
- comune e provincia;
- zona;
- tipo di zona e tipo di stazione;
- validazione;
- data di osservazione;
- ora;
- data di aggiornamento;
- fonte.

ARPAT specifica che i valori dei dati in tempo reale sono riferiti all'**ora solare**. L'integrazione conserva quindi i riferimenti temporali originali come metadati e non applica conversioni arbitrarie.

## Superamenti giornalieri

L'endpoint dei superamenti può restituire due forme diverse:

- un oggetto con `superamenti: 0`, quando non risultano superamenti;
- una lista di record, uno per ciascun superamento pubblicato.

Per mantenere un'entità stabile nel tempo, l'integrazione crea:

```text
sensor.<stazione>_superamenti_giornalieri
```

con:

- **stato**: numero di superamenti nell'ultimo bollettino disponibile;
- `data_bollettino`: data di osservazione;
- `dettaglio_superamenti`: elenco di parametro, sigla e valore per i superamenti presenti.

Il sensore non viene creato e rimosso in base agli eventi: rimane sempre lo stesso, così lo storico del Recorder è coerente anche nei giorni con valore `0`.

## Frequenza di aggiornamento

- NRT: interrogazione ogni **30 minuti**;
- Superamenti giornalieri: aggiornamento al massimo ogni **2 ore**.

ARPAT dichiara che i dati NRT vengono aggiornati automaticamente su base oraria. Il polling a 30 minuti permette di acquisire rapidamente un nuovo campione senza interrogare inutilmente il servizio con frequenze elevate.

Una sola acquisizione coordinata alimenta tutte le entità della stessa stazione tramite `DataUpdateCoordinator`.

## Endpoint utilizzati

Base Open Data:

```text
https://opendata.arpat.toscana.it/temi-ambientali/aria/qualita-aria
```

Struttura rete regionale:

```text
/rete_monitoraggio/rete_json/regionale
```

Ultimo dato NRT:

```text
/dati_orari_real_time/json_orari_nrt/[NOME_STAZIONE]/last
```

Superamenti nell'ultimo bollettino per stazione:

```text
/bollettini/superamenti_json/-/[NOME_STAZIONE]
```

Documentazione ARPAT:

https://www.arpat.toscana.it/open-data/open-data-sulla-qualita-dellaria/

## Validazione dei dati

I dati NRT non devono essere confusi con le serie storiche definitive.

ARPAT distingue i dati validi a livello strumentale dai dati che hanno superato il primo livello di validazione operatore. Il payload NRT contiene il campo `VALIDAZIONE`, che viene mantenuto negli attributi delle entità.

I dati storici consolidati, che hanno completato l'intero ciclo di validazione, possono differire dai valori NRT o dai dati del bollettino quotidiano.

## Installazione manuale

Copia:

```text
custom_components/arpat_toscana
```

in:

```text
/config/custom_components/arpat_toscana
```

Riavvia Home Assistant e aggiungi l'integrazione dalla UI.

## Limiti della versione 0.1.0

- viene utilizzata per la selezione delle stazioni la **rete regionale**;
- sono importati esclusivamente NRT e superamenti giornalieri;
- non vengono ancora importati bollettini completi, indicatori giornalieri/annuali o storico validato;
- il campo NRT `BC` viene esposto senza unità forzata perché il tracciato JSON Open Data NRT non ne documenta esplicitamente l'unità;
- la disponibilità dei dati dipende dai servizi pubblici ARPAT.

## Licenze e attribuzione

Codice dell'integrazione: **MIT**.

I dati ARPAT sono rilasciati con **Italian Open Data License v2.0 (IODL 2.0)**. ARPAT richiede, tra le altre condizioni, l'indicazione della fonte e che il riuso non suggerisca carattere di ufficialità o approvazione da parte dell'ente.

Fonte dati: **ARPAT - Agenzia regionale per la protezione ambientale della Toscana**.

## Disclaimer

Questa integrazione è esclusivamente un client non ufficiale che consente di visualizzare in Home Assistant informazioni pubblicamente rese disponibili da ARPAT. I dati, la loro validazione e il loro significato ufficiale restano quelli definiti e pubblicati da ARPAT.
