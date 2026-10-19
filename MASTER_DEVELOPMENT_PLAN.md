# Private Investment Intelligence Platform
## Master Development Plan

**Projektziel:** Eine vollständig funktionierende, präzise, selbst gehostete Investment-Plattform für den privaten Gebrauch ohne verpflichtende kostenpflichtige APIs oder Cloud-Dienste.

**Zielzustand:** V3+

**Plan-Revision:** 2026-10-03 — konsolidierte V1–V3+-Roadmap, Quellenfreigaben und überprüfbare Meilensteine.

**Prinzipien:**

- Private Nutzung
- Self-hosted
- 0 CHF verpflichtende API-Kosten (Hardware, Strom und Betrieb sind davon nicht umfasst)
- Datenqualität wichtiger als Datenmenge
- Mehrere Quellen statt Single Source of Truth
- Offizielle Daten vor Scraping
- Point-in-Time-Daten
- reproduzierbare Prognosen
- transparente Modellhistorie
- lokale ML-Modelle
- lokales LLM
- keine Abhängigkeit von einem einzelnen Anbieter
- kein automatisches Trading
- Nutzer trifft die endgültige Entscheidung
- nicht rekonstruierbare Daten werden ab ihrer ersten Verfügbarkeit versioniert
- harte Validierungsregeln haben Vorrang vor Quality Scores
- Signalzeitpunkt und handelbarer Ausführungszeitpunkt werden strikt getrennt

---

# 1. Ziel der Anwendung

Die fertige Anwendung soll sechs Hauptaufgaben erfüllen.

```text
Portfolio Tracking
        +
Investment Research
        +
Forecasting
        +
Risk Analysis
        +
AI Research Assistant
        +
Investment Recommendations
```

Die App soll Fragen beantworten können wie:

- Wie entwickelt sich mein Portfolio?
- Welche Position verursacht das meiste Risiko?
- Wo bin ich übermässig konzentriert?
- Wie attraktiv ist eine bestimmte Aktie momentan?
- Welche fundamentalen Faktoren sprechen dafür oder dagegen?
- Wie schätzt das Modell die nächsten 30 oder 90 Tage ein?
- Wie sicher ist diese Einschätzung?
- Wie gut war das Modell historisch?
- Was würde passieren, wenn ich CHF 5'000 in eine Position investiere?
- Welche Positionen passen schlecht zum restlichen Portfolio?
- Welche Investments könnten mein Portfolio sinnvoll ergänzen?
- Warum gibt das System diese Empfehlung?
- Welche Daten wurden dafür verwendet?

Die Umsetzung folgt genau der Roadmap in Abschnitt 158. Die Schrittfolge in Abschnitt 204 und die Meilensteine 206–211 sind daraus abgeleitet. V1 ist der nutzbare Portfolio-Tracker; Fundamentals/Research, ML, Empfehlungen und Assistent folgen in späteren Meilensteinen.

---

# 2. Nicht-Ziele

Die erste vollständige Version benötigt nicht:

- High-Frequency Trading
- Intraday-Trading
- Optionen
- Futures
- CFDs
- Hebelprodukte
- Copy Trading
- Social Trading
- automatische Orders
- Verwaltung fremder Kundengelder
- professionelle Börsen-Realtime-Feeds
- Bloomberg
- FactSet
- LSEG
- kostenpflichtige LLM-APIs

Auch V3+ soll zunächst keine Trades selbstständig ausführen.

---

# 3. Kernprinzip

Die Plattform darf niemals so funktionieren:

```text
User
 ↓
LLM
 ↓
"Buy NVIDIA"
```

Sondern:

```text
Raw Data
   ↓
Data Validation
   ↓
Canonical Dataset
   ↓
Quantitative Models
   ↓
Risk Engine
   ↓
Recommendation Engine
   ↓
Structured Result
   ↓
LLM Explanation
   ↓
User
```

Das LLM ist hauptsächlich eine **Erklärungs- und Research-Schicht**.

Es ist nicht die eigentliche Investment-Logik.

---

# 4. Zielarchitektur

```text
                     INTERNET
                        │
              ┌─────────┴─────────┐
              │                   │
       Official Sources      Public Sources
              │                   │
       SEC / SNB / ECB       Yahoo / GDELT
       FRED / OpenFIGI       Company Websites
              │                   │
              └─────────┬─────────┘
                        │
                        ▼
                 DATA COLLECTORS
                        │
                        ▼
                 RAW DATA STORAGE
                        │
                        ▼
                  QUALITY ENGINE
                        │
              ┌─────────┴─────────┐
              │                   │
              ▼                   ▼
         CANONICAL DB         QUARANTINE
              │
     ┌────────┼────────────┐
     │        │            │
     ▼        ▼            ▼
 Portfolio  Research      ML
 Engine     Engine       Engine
     │        │            │
     └────────┼────────────┘
              ▼
          Risk Engine
              │
              ▼
      Recommendation Engine
              │
              ▼
        Local AI Assistant
              │
              ▼
             UI
```

---

# 5. Technologie-Stack

## 5.1 Frontend

Verwenden:

```text
Next.js
React
TypeScript
Tailwind CSS
shadcn/ui
TanStack Query
Zod
TradingView Lightweight Charts
```

Warum:

- moderner Web-Stack
- sehr gute TypeScript-Unterstützung
- responsive UI
- einfach mit FastAPI kombinierbar
- gute Charting-Möglichkeiten
- später PWA möglich

---

# 6. Backend

Verwenden:

```text
Python
FastAPI
Pydantic
SQLAlchemy
Alembic
```

Python ist bewusst gewählt, weil damit sowohl:

```text
API
Datenverarbeitung
Scraping
ML
Backtesting
AI
```

mit derselben Sprache umgesetzt werden können.

---

# 7. Datenbank

V1:

```text
PostgreSQL
+
pgvector
```

Keine zusätzliche Timeseries-Datenbank am Anfang.

Daily-Kursdaten werden partitioniert.

Später kann TimescaleDB ergänzt werden, wenn es tatsächlich notwendig wird.

---

# 8. Cache und Background Jobs

Verwenden:

```text
Valkey
Celery
Celery Beat
```

Valkey übernimmt:

- Cache
- Job Queue
- Distributed Locks
- Rate Limiting

Celery übernimmt:

- Datenimporte
- Portfolio-Berechnungen
- Scraper
- ML Inference
- Benachrichtigungen
- Report-Erstellung

Celery Beat übernimmt geplante Jobs.

---

# 9. Object Storage

Verwenden:

```text
MinIO
```

Dort speichern:

```text
raw provider responses
filings
annual reports
PDFs
scraped HTML
model artifacts
dataset snapshots
backtest results
exports
```

---

# 10. ML Stack

```text
Polars
Pandas
NumPy
SciPy
scikit-learn
LightGBM
XGBoost
SHAP
MLflow
PyTorch optional
```

PyTorch erst verwenden, wenn klassische Modelle tatsächlich schlechter sind.

---

# 11. Lokale AI

Primär:

```text
Ollama
```

Später optional:

```text
vLLM
```

Backend spricht nur mit einer generischen OpenAI-kompatiblen Schnittstelle.

Beispiel:

```text
LLMProvider
    │
    ├── Ollama
    ├── vLLM
    └── optional external provider
```

Kein Modellname wird tief im Code hardcodiert.

---

# 12. Embeddings

Lokal verwenden.

Anforderungen:

- multilingual
- gute Retrieval-Qualität
- lokal ausführbar

Embedding Provider abstrahieren:

```text
EmbeddingProvider

embedText()
embedDocuments()
```

Speicherung:

```text
PostgreSQL
+
pgvector
```

---

# 13. Sentiment

Für englische Finanztexte:

```text
FinBERT
```

verwenden.

Pipeline:

```text
Article
  ↓
FinBERT
  ↓
positive
neutral
negative
confidence
```

Andere Sprachen:

```text
multilingual sentiment model
        oder
lokales LLM mit JSON output
```

mit niedrigerem Confidence-Level.

---

# 14. Repository-Struktur

Projektname beispielsweise:

```text
investment-intelligence/
```

Für ein privates Einzelprojekt bleibt die Struktur bewusst einfach. API und Worker verwenden denselben Python-Domain-Code; es gibt keine doppelte `apps/api`- und `backend/app`-Struktur.

```text
investment-intelligence/

├── frontend/
│   └── web/
│       ├── app/
│       ├── components/
│       ├── lib/
│       └── types/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── auth/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── repositories/
│   │
│   ├── collectors/
│   │   ├── yahoo/
│   │   ├── stooq/
│   │   ├── sec/
│   │   ├── fred/
│   │   ├── snb/
│   │   ├── ecb/
│   │   ├── openfigi/
│   │   ├── gdelt/
│   │   └── company_ir/
│   │
│   ├── quality/
│   ├── portfolio/
│   ├── research/
│   ├── risk/
│   ├── recommendation/
│   └── assistant/
│
├── ml/
│   ├── datasets/
│   ├── features/
│   ├── training/
│   ├── evaluation/
│   ├── backtesting/
│   ├── inference/
│   └── models/
│
├── infra/
│   ├── docker/
│   ├── caddy/
│   ├── monitoring/
│   └── backup/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── data/
│   ├── ml/
│   └── e2e/
│
├── docs/
│   ├── architecture/
│   ├── data/
│   ├── models/
│   └── decisions/
│
├── docker-compose.yml
├── .env.example
├── Makefile
├── README.md
└── MASTER_DEVELOPMENT_PLAN.md
```

Prozessmodell:

```text
FastAPI ─┐
         ├── shared backend/domain services
Celery ──┘
```

Business-Logik darf nicht separat für API und Worker dupliziert werden.

---

# 15. Docker Services

Die vollständige Zielumgebung enthält:

```text
web
api
worker
scheduler
postgres
valkey
minio
ollama
mlflow
prometheus
grafana
loki
caddy
```

Optional:

```text
mailpit
```

nur für Entwicklung.

Die Dienste werden gemäss Abschnitt 158 gestaffelt aktiviert: P1 startet den Daten- und Anwendungskern, P4 ergänzt den gesicherten Produktivzugang und Grundmonitoring, P7 MLflow und P10 Ollama. Grafana/Prometheus müssen zur V1-Produktivfreigabe funktionieren; Loki ist ein späterer Ausbau. Die Zieltopologie ist keine Voraussetzung für den ersten lokalen Start.

---

# 16. Development Environments

Vier Umgebungen definieren:

```text
local
test
staging
production
```

Für private Nutzung können `staging` und `production` auf derselben Infrastruktur laufen, müssen aber:

- eigene Datenbanken
- eigene Volumes
- eigene Secrets

haben.

---

# 17. Konfiguration

Alle konfigurierbaren Dinge gehören in Settings.

Beispiel:

```text
DATABASE_URL=
VALKEY_URL=

MINIO_ENDPOINT=
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=

FRED_API_KEY=
OPENFIGI_API_KEY=
STOOQ_API_KEY=

OLLAMA_URL=

BASE_CURRENCY=CHF
DEFAULT_TIMEZONE=Europe/Zurich

MARKET_DATA_PRIMARY=yahoo
MARKET_DATA_FALLBACK=stooq

ENABLE_SCRAPERS=true
ENABLE_ML=true
ENABLE_ASSISTANT=true
```

Secrets niemals committen.

`MARKET_DATA_PRIMARY=yahoo` beschreibt eine gewünschte Reihenfolge, keine Freigabe zur automatisierten Nutzung. Ein Collector wird erst nach dem dokumentierten Source-Gate aus Abschnitt 18 aktiviert. Ohne freigegebene Yahoo-Nutzung verwendet V1 einen zulässigen Provider oder den validierten manuellen CSV-Import; `DATA_UNAVAILABLE` ist zulässig, erfundene Kurse sind es nicht.

---

# 18. Haupt-Datenquellen

## Preise

Primary:

```text
Yahoo Finance / yfinance
```

Fallback:

```text
Stooq
```

zusätzlich:

```text
manual CSV
```

Provider-Abstraktion:

```text
MarketDataProvider
    ├── YahooCollector
    ├── StooqCollector
    └── CsvCollector
```

`yfinance` oder andere Provider-Bibliotheken dürfen nur innerhalb ihres Collectors verwendet werden. Portfolio-, Research- und ML-Code sprechen ausschliesslich mit der internen Provider-/Canonical-Data-Schnittstelle. Dadurch bleibt Yahoo austauschbar.

## Source-Gate vor jeder automatisierten Nutzung

Yahoo bleibt die gewünschte Primärquelle. **Produktiver automatisierter Zugriff ist jedoch gesperrt, bis die für Nutzungsort, Nutzungsart, Abruf und Speicherung geltenden Rechte ausdrücklich geprüft und dokumentiert sind.** Die am 2026-10-03 geprüfte [US-Fassung der Yahoo-Nutzungsbedingungen](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html) untersagt automatisiertes Sammeln ohne vorherige ausdrückliche Erlaubnis. Welche regionale Fassung konkret gilt, ist Teil des Source-Gates. Die Bibliothek `yfinance` verschafft selbst keine Datenrechte. Auch Stooq und jede weitere Quelle benötigen vor Aktivierung eine eigene dokumentierte Prüfung von Nutzungsbedingungen, Abrufweg, Rate Limits und Speicherrechten.

Das Gate speichert je Quelle: geprüfte Dokumente/Links, Prüfdatum, Geltungsbereich, erlaubte Nutzungsarten, Freigabestatus, verantwortliche Entscheidung und nächstes Prüfdatum. `BLOCKED` oder `UNKNOWN` bedeutet: Collector deaktiviert; vorhandene validierte Daten mit Alter anzeigen oder manuellen CSV-Import nutzen. V1 hängt nicht von einer bestimmten Kursquelle ab. Ein Fallback ist nur zulässig, wenn auch er das Source-Gate bestanden hat. Die Quellenliste und Verfügbarkeit werden pro Instrument sichtbar gemacht.

---

# 19. US Fundamentals

Primär:

```text
SEC EDGAR
```

Verwenden:

```text
Submissions API
Company Facts API
XBRL
Filings
```

SEC gilt für US-Unternehmen als authoritative source.

SEC-Collector-Regeln:

```text
descriptive User-Agent with contact information
global rate limiter <= 10 requests/second
retry with exponential backoff + jitter
conditional requests / caching where useful
no aggressive parallel crawling
```

Das Limit gilt global über alle Worker hinweg; ein verteilter Lock/Rate-Limiter verhindert, dass mehrere Worker zusammen das Limit überschreiten.

**Quellenprüfung 2026-10-03:** Die [SEC-Daten-APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) dokumentieren Submissions und Company Facts ohne API-Key. Die [SEC-Fair-Access-Regeln](https://www.sec.gov/about/developer-resources) nennen derzeit höchstens zehn Anfragen pro Sekunde pro Nutzer über alle Maschinen hinweg. Diese Grenze ist vor Collector-Aktivierung erneut zu prüfen; bei Änderung wird die Konfiguration angepasst. SEC-Fundamentals gehören zu V1.5, nicht zur V1-Abnahme.

---

# 20. Schweizer Fundamentals

Priorität:

```text
1 Company Investor Relations
2 Annual / Half-Year Reports
3 Company announcements
4 Yahoo
5 other scraped aggregators
```

---

# 21. Europäische Fundamentals

Analog:

```text
Company filings
Company IR
Exchange publications
Yahoo
secondary sources
```

---

# 22. Makrodaten USA

```text
FRED
ALFRED
```

Besonders wichtig:

ALFRED für historische Datenstände.

**Quellenprüfung 2026-10-03:** Die [FRED/ALFRED-Dokumentation](https://fred.stlouisfed.org/docs/api/fred/overview.html) bietet Daten und historische Stände; der [API-Zugang erfordert einen Schlüssel](https://fred.stlouisfed.org/docs/api/fred/v2/api_key.html). Serienbezogene Nutzungsrechte und Vintage-Verfügbarkeit werden pro Serie dokumentiert. FRED/ALFRED erweitert nach V1 die Makro- und Point-in-Time-Daten; V1-Portfolio-FX darf nicht davon abhängen.

---

# 23. Makrodaten Schweiz

```text
SNB Data Portal
```

Beispiele:

- SNB policy rate
- CHF FX
- Schweizer Renditen
- Geldmengen
- relevante Konjunkturindikatoren

---

# 24. Makrodaten Europa

```text
ECB Data Portal
```

Verwenden für:

- EUR exchange rates
- ECB rates
- Eurozone indicators

**Quellenprüfung 2026-10-03:** Das [ECB Data Portal](https://data.ecb.europa.eu/help/api/overview) dokumentiert einen SDMX-Webservice. Historische Versionen sind je Datenabruf zu prüfen; die [API-Dokumentation](https://data.ecb.europa.eu/help/api/data) beschreibt `includeHistory` für verfügbare Reihen. Fehlende Historie wird nicht als Point-in-Time-Historie ausgegeben.

---

# 25. Instrument IDs

```text
OpenFIGI
```

Zusätzlich lokal speichern:

```text
ticker
exchange
MIC
ISIN
FIGI
currency
country
```

Ticker ist niemals die interne ID.

**Quellenprüfung 2026-10-03:** Die [OpenFIGI-API](https://www.openfigi.com/api/documentation) ist öffentlich und kostenlos; ein API-Key erhöht die dokumentierten Limits. Mapping-Treffer werden erst nach Prüfung von Börse/MIC, Währung, Instrumenttyp und Gültigkeitszeitraum als interne Identität übernommen. Mehrdeutige Treffer bleiben ungeklärt statt stillschweigend den ersten Treffer zu wählen.

---

# 26. News

Quellen:

```text
GDELT
Yahoo news/search
SEC filings
Company IR
RSS feeds
public financial websites
```

Danach:

```text
Deduplication
Entity detection
Language detection
Sentiment
Embedding
Storage
```

---

# 27. Analystenschätzungen

Initial:

```text
Yahoo/yfinance
+
available public pages
```

Da historische Analystenschätzungen kostenlos schwierig sind:

## Ab Tag 1 tägliche Snapshots speichern.

```text
estimate_snapshot

instrument_id
observed_at
eps_current_quarter
eps_next_quarter
eps_current_year
eps_next_year
revenue_current_year
revenue_next_year
price_target_low
price_target_mean
price_target_high
recommendation_mean
analyst_count
source
```

Dadurch baut die Anwendung ihre eigene Historie auf.

---

# 28. Source Registry

Tabelle:

```text
data_source

id
name
type
trust_level
priority
enabled
rate_limit
last_success
last_failure
failure_count
```

Beispiele:

```text
SEC
OFFICIAL
A
100

SNB
OFFICIAL
A
100

Yahoo
AGGREGATOR
B
80

Scraper XYZ
SCRAPER
C
60
```

Die Source Registry enthält zusätzlich den Freigabestatus des Source-Gates aus Abschnitt 18 samt Prüfdatum und Link zu den geltenden Bedingungen. `enabled=true` setzt eine gültige Freigabe voraus. `trust_level` beschreibt Datenvertrauen, nicht Nutzungsrechte.

---

# 29. Trust Levels

## Level A

```text
Official regulator
Central bank
Official company filing
Official company IR
```

Score:

```text
0.95–1.00
```

## Level B

```text
Reliable financial aggregator
```

Score:

```text
0.80–0.95
```

## Level C

```text
Scraped secondary source
```

Score:

```text
0.60–0.85
```

## Level D

```text
Forum
Social media
Unknown source
```

Nicht als Ground Truth verwenden.

---

# 30. Raw Data Principle

Alle Downloads zuerst unverändert speichern.

Beispiel:

```text
raw/
  yahoo/
    2026/
      10/
        03/
          AAPL/
            history.json
```

Dazu:

```text
source
retrieved_at
request
response_hash
http_status
content_type
```

Warum:

Später muss nachvollziehbar sein:

> Welche Daten hat das System damals tatsächlich erhalten?

Die Raw-Storage-Struktur und eine abrufbare `raw_ingestion`-Referenz müssen **vor dem ersten produktiven Collector** funktionieren. Der unveränderte Response wird mit Hash, Abrufzeit, Quelle und Request-Metadaten gespeichert; Parser und Canonical Pipeline verweisen auf genau diese Version. Gibt es keinen Original-Response, wird die Herkunft als manueller Import gekennzeichnet. Historische Daten werden nicht rückwirkend als damals beobachtete Snapshots deklariert.

---

# 31. Raw Ingestion Tabelle

```text
raw_ingestion

id
source_id
resource_type
instrument_id
requested_at
received_at
object_path
sha256
status
error
```

Eine erfolgreiche Canonical-Version referenziert `raw_ingestion.id` und ihre Parser-/Validierungsregelversion. Korrekturen erzeugen neue Versionen mit Ersetzungsbezug; Rohobjekte und frühere Canonical-Versionen bleiben erhalten. Ein fehlgeschlagener Abruf erzeugt einen nachvollziehbaren Fehlerdatensatz, aber keinen Canonical-Wert.

---

# 32. Canonical Data

Raw Data wird niemals direkt von ML oder UI verwendet.

Flow:

```text
RAW
 ↓
PARSE
 ↓
NORMALIZE
 ↓
VALIDATE
 ↓
RECONCILE
 ↓
CANONICAL
```

---

# 33. Quarantine

Fehlerhafte oder widersprüchliche Daten kommen nach:

```text
data_quarantine
```

Schema:

```text
id
source
record_type
raw_id
reason
severity
detected_at
resolved_at
resolution
```

---

# 34. Price Data Schema

```text
price_daily

instrument_id
trading_date

open
high
low
close
adjusted_close
volume

currency

primary_source
source_count
validation_status
quality_score
quality_components

created_at
updated_at
```

Primary key:

```text
instrument_id
+
trading_date
```

Dies ist der Schlüssel der **aktuellen validierten Lesesicht**. Die Historie liegt append-only in `price_daily_version` mit `instrument_id`, `trading_date`, `version_id`, `raw_ingestion_id`, `known_at`/`observed_at`, `retrieved_at`, Regelversion und Ersetzungsbezug. Jede nachträgliche Korrektur ergänzt eine Version; Point-in-Time-Abfragen lesen die damals verfügbare Version, nicht die heutige Lesesicht.

---

# 35. Price Validations

Immer prüfen:

```text
open > 0
high > 0
low > 0
close > 0

high >= low
high >= open
high >= close

low <= open
low <= close

volume >= 0
```

Zusätzlich:

```text
unexpected daily move
split mismatch
currency mismatch
missing session
duplicate record
zero price
stale price
```

---

# 36. Cross-Source Price Validation

Wenn zwei Quellen vorhanden:

```text
difference =
abs(priceA - priceB)
/
median(priceA, priceB)
```

Regeln:

```text
< 0.25 %
ACCEPT

0.25–0.50 %
ACCEPT_WITH_WARNING

0.50–2 %
REVIEW / validate corporate action

> 2 %
QUARANTINE
```

Ausnahme:

```text
split
dividend adjustment
currency mismatch
different market session
```

---

# 37. Niemals blind mitteln

Nicht:

```text
Yahoo = 100
Source B = 92

canonical = 96
```

Stattdessen:

```text
investigate discrepancy
```

Anschliessend authoritative/preferred source auswählen.

---

# 38. Corporate Actions

Tabelle:

```text
corporate_action

instrument_id
type
ex_date
record_date
payment_date

ratio
cash_amount
currency

source
validation_status
quality_score
quality_components
```

Typen:

```text
DIVIDEND
SPLIT
REVERSE_SPLIT
MERGER
SPINOFF
TICKER_CHANGE
DELISTING
```

## Price Adjustment Policy

Corporate Actions und `adjusted_close` dürfen niemals unkontrolliert gleichzeitig als Renditequelle verwendet werden.

Für Portfolio Accounting:

```text
unadjusted/raw close
+
explicit dividend cash flows
+
explicit split/corporate-action handling
```

Für ML-/Research-Total-Returns genau eine Methode wählen:

```text
A) adjusted total-return price series
```

oder:

```text
B) raw prices + explicit corporate actions
```

Nie A und B gleichzeitig, da sonst Dividenden/Splits doppelt berücksichtigt werden können. Die gewählte Policy wird versioniert und in `docs/decisions/ADR-005-price-adjustment-policy.md` dokumentiert.

**Verbindliche Rendite-Policy:** Portfolio Accounting sowie Research-/ML-Total-Returns verwenden rohe, nicht adjustierte Preise plus explizit validierte Corporate Actions; `adjusted_close` dient nur zur Plausibilisierung und wird nicht nochmals als Renditequelle addiert. Bei fehlender oder widersprüchlicher Split-/Dividendenhistorie ist die betroffene Total-Return-Kennzahl `DATA_UNAVAILABLE`, bis die Aktion geprüft wurde. Die Policy erhält eine Version und Golden Tests für Split, Dividende und deren Kombination.

---

# 39. Instrument Master

```text
instrument

id UUID

ticker
name
asset_type

exchange
mic

currency
country

isin
figi

sector
industry

listed_at
delisted_at

active

created_at
updated_at
```

---

# 40. Identifier History

Wichtig bei Ticker-Wechsel:

```text
instrument_identifier

instrument_id
type
value
valid_from
valid_to
```

Zusätzlich werden Quelle, `observed_at` und `raw_ingestion_id` gespeichert. Gültigkeitszeit und Zeitpunkt der eigenen Kenntnis sind getrennt: Ein später erkannter Ticker-Wechsel darf einen früheren Such- oder Backtest-Stand nicht stillschweigend überschreiben.

---

# 41. Point-in-Time Daten

Jeder fundamentale Wert benötigt:

```text
period_end
known_at
retrieved_at
```

Beispiel:

```text
Revenue Q2

period_end:
2026-06-30

known_at:
2026-08-01
```

Das ML darf diesen Wert erst ab:

```text
2026-08-01
```

verwenden.

## Snapshot-Policy ab erster Verfügbarkeit

Nicht rekonstruierbare Daten werden **nicht erst in einer späteren ML-Phase** archiviert. Sobald ein Collector oder Datentyp erstmals eingeführt wird, startet dessen historische Versionierung sofort.

Mindestens erfassen:

```text
observed_at
known_at
retrieved_at
source
raw_ingestion_id
quality / validation status
```

Beispiele:

```text
Prices             -> raw response + canonical version
Fundamentals       -> filing + known_at
Analyst estimates  -> daily snapshot ab erster Nutzung
Universe membership-> valid_from / valid_to ab erster Nutzung
News               -> published_at + discovered_at + raw source
Features           -> point-in-time feature snapshot
Predictions        -> immutable prediction record
```

Grundregel:

> Snapshotting beginnt an dem Tag, an dem die Quelle in die Anwendung aufgenommen wird. Die spätere Time-Machine-UI ist nur eine Darstellung dieser bereits gesammelten Historie.

Für jeden Datentyp wird zwischen **Ereigniszeit**, **öffentlicher Verfügbarkeit** und **erstem Eingang im eigenen Archiv** unterschieden. Point-in-Time-Abfragen nutzen nur Versionen, deren Verfügbarkeit für den abgefragten Zeitpunkt belegt ist. Ein später importierter aktueller Datenstand darf keine unbeobachtete historische Version ersetzen. Restatements, nachträgliche Kurskorrekturen und geänderte Identifikatoren bleiben als neue Versionen neben dem früheren Stand erhalten. Diese Regel gilt schon für V1-Preise und FX, bevor ML beginnt.

---

# 42. Fundamental Schema

```text
fundamental_fact

instrument_id

metric
value
currency
unit

period_start
period_end

fiscal_year
fiscal_quarter

filing_type

known_at
retrieved_at

source
validation_status
quality_score
quality_components
```

Jeder Fact referenziert Filing/`raw_ingestion_id` und eine Fact-Version. Restatements erzeugen neue Facts mit Ersetzungsbezug; `known_at` ist die belegte öffentliche Verfügbarkeit dieser konkreten Filing-Version. Eine aktuelle Company-Facts-Antwort allein belegt keinen früheren eigenen Snapshot.

---

# 43. Normalisierte Metrics

Mindestens:

```text
revenue
gross_profit
operating_income
net_income

eps_basic
eps_diluted

cash
total_assets
total_liabilities
total_equity
total_debt

operating_cash_flow
capex
free_cash_flow

shares_outstanding
```

---

# 44. Derived Fundamentals

Berechnen:

```text
revenue_growth_yoy
eps_growth_yoy
fcf_growth_yoy

gross_margin
operating_margin
net_margin

ROE
ROA
ROIC

debt_to_equity
net_debt

current_ratio
quick_ratio
```

---

# 45. Valuation Metrics

```text
P/E
Forward P/E
P/S
P/B

EV/EBITDA
EV/Revenue
EV/FCF

FCF Yield
Earnings Yield

PEG
```

---

# 46. News Schema

```text
news_article

id

published_at
discovered_at

source
source_url

title
summary
language

content_hash

sentiment_positive
sentiment_neutral
sentiment_negative

sentiment_model

created_at
```

---

# 47. News ↔ Instrument

```text
news_instrument

news_id
instrument_id

relevance_score
entity_confidence
```

---

# 48. Deduplication

News-Duplikate erkennen über:

```text
normalized URL
title similarity
content hash
embedding similarity
```

Nicht denselben Reuters-/AP-Text zehnmal als zehn Nachrichten bewerten.

---

# 49. Scraping Engine

Technologien:

```text
httpx
BeautifulSoup
selectolax
Playwright
```

Reihenfolge:

```text
HTTP request
   ↓
HTML parser
   ↓
Playwright only when needed
```

Browser-Scraping nur verwenden, wenn JavaScript zwingend benötigt wird.

---

# 50. Scraper Rules

Jeder Scraper besitzt:

```text
collector
parser
validator
fixtures
tests
```

Beispiel:

```text
company_ir/
  nestle.py
  fixtures/
  tests/
```

---

# 51. Scraping Robustness

Implementieren:

```text
timeouts
retry
exponential backoff
user-agent
rate limiting
caching
conditional requests
```

Nicht implementieren:

```text
CAPTCHA bypass
login bypass
paywall bypass
anti-bot circumvention
```

Wenn eine Quelle blockiert:

```text
disable connector
use fallback
```

---

# 52. Data Quality Score

`Validity` und `Quality` sind getrennte Konzepte.

Jeder canonical Record erhält mindestens:

```text
validation_status
quality_score 0..1
quality_components
```

Mögliche `validation_status`:

```text
VALID
WARNING
REJECTED
```

## Hard Validation Gates

Bestimmte Fehler dürfen niemals durch einen guten Quality Score kompensiert werden.

Beispiele:

```text
impossible OHLC                 -> REJECTED
invalid / impossible currency   -> REJECTED
future timestamp / PIT violation-> REJECTED
negative impossible quantity    -> REJECTED
schema corruption               -> REJECTED
```

Erst Records mit `VALID` oder explizit akzeptiertem `WARNING` erhalten einen Quality Score für die feinere Bewertung.

Beispiel für den Quality Score:

```text
source_trust             40 %
cross_validation         25 %
freshness                15 %
schema_quality            10 %
historical_consistency   10 %
```

Der Score beschreibt die Zuverlässigkeit eines **grundsätzlich gültigen** Records. Er ist kein Ersatz für Validierungsregeln.

---

# 53. Quality Labels

```text
0.95–1.00
EXCELLENT

0.85–0.95
HIGH

0.70–0.85
MEDIUM

0.50–0.70
LOW

<0.50
REJECT
```

---

# 54. Data Quality Dashboard

Eigene Seite:

```text
/data-quality
```

Anzeigen:

```text
last successful imports
failed imports
stale prices
source disagreements
quarantined records
missing fundamentals
news pipeline health
macro freshness
```

Die V1-Seite zeigt mindestens den letzten erfolgreichen Preis-/FX-Import, Alter des letzten validierten Wertes, Quarantäne und Quelle je betroffenem Instrument. Weitere Panels für Fundamentals, News und ML werden ergänzt, sobald diese Pipelines existieren. Ein vollständiges Data Quality Center ist ein späterer Ausbau derselben V1-Seite.

---

# 55. Portfolio Tabellen

```text
portfolio
portfolio_account
transaction
position_snapshot
cash_balance
portfolio_snapshot
benchmark
```

---

# 56. Transaction Schema

```text
transaction

id
portfolio_id
account_id

instrument_id

type

trade_date
settlement_date

quantity
price
currency

fee
tax

fx_rate_to_base

external_id
notes

created_at
updated_at
```

---

# 57. Transaction Types

```text
BUY
SELL

DIVIDEND
INTEREST

DEPOSIT
WITHDRAWAL

FEE
TAX

TRANSFER_IN
TRANSFER_OUT

SPLIT

CASH_ADJUSTMENT
```

---

# 58. Portfolio Base Currency

Default:

```text
CHF
```

Aber konfigurierbar.

Portfolio-Werte werden sowohl in:

```text
native currency
```

als auch:

```text
portfolio base currency
```

gespeichert bzw. berechnet.

---

# 59. FX Sources

Priority:

```text
1 SNB where applicable
2 ECB
3 Yahoo
```

Cross-check wenn möglich.

Für jede Umrechnung werden Kursdatum, FX-Fixing-Zeitpunkt, Richtung und Quelle gespeichert. Es werden nur zum Bewertungszeitpunkt verfügbare FX-Werte verwendet; fehlende Handelstage benötigen eine dokumentierte begrenzte Carry-Forward-Regel mit sichtbarem Alter. Fehlt ein zulässiger FX-Wert, ist der Basiswährungswert `DATA_UNAVAILABLE` und wird nicht als Null berechnet. Die V1-Abnahme umfasst CHF-, USD- und EUR-Beispiele.

---

# 60. Portfolio Calculation

Marktwert:

```text
market_value =
quantity
*
current_price
*
fx_rate
```

Unrealized P/L:

```text
market_value
-
remaining_cost_basis
```

Realized P/L wird aus Verkäufen berechnet.

---

# 61. Cost Basis

V1:

```text
weighted average cost
```

Transaktionen bleiben vollständig erhalten.

Später optional:

```text
FIFO
LIFO
specific lot
```

---

# 62. Performance

Implementieren:

```text
Absolute Return
TWR
XIRR

CAGR

realized P/L
unrealized P/L

income
fees

FX contribution
```

---

# 63. Benchmark

Default:

```text
MSCI World proxy
```

oder durch den Nutzer wählbar.

Zusätzlich:

```text
S&P 500
SPI/SMI
custom
```

---

# 64. Portfolio Import

Zuerst:

```text
Manual transaction
CSV import
```

CSV Pipeline:

```text
Upload
 ↓
Detect columns
 ↓
User mapping
 ↓
Validation
 ↓
Preview
 ↓
Duplicate detection
 ↓
Import
```

---

# 65. Broker Import später

Später:

```text
broker CSV
read-only API
```

Kein Trading.

---

# 66. UI Navigation

```text
Dashboard

Portfolio
Research
Markets
Watchlists

Forecasts
Risk
Scenarios
Recommendations

Assistant

Models
Data Quality

Settings
```

Die Navigation wächst mit den Phasen aus Abschnitt 158. V1 zeigt Dashboard, Portfolio, Instrumente, Datenqualität und Settings; spätere Module erscheinen erst mit realen, freigegebenen Daten und funktionierender API.

---

# 67. Dashboard

Anzeigen:

```text
Portfolio Value
Daily Change
Total Return
YTD

Cash

Allocation
Risk Summary

Top Movers

Upcoming Earnings
Recent News

Forecast Changes

Portfolio Alerts
```

V1 zeigt Portfolio Value, Cash, Performance, Allokation und die Datenaktualität. Risiko-, News-, Forecast- und Alert-Karten erscheinen erst nach den entsprechenden Phasen; unbekannte Werte erhalten keinen gefüllten Platzhalter.

---

# 68. Portfolio Detail

Tabs:

```text
Overview
Holdings
Performance
Allocation
Risk
Dividends
Transactions
Scenarios
Recommendations
```

V1 enthält Overview, Holdings, Performance, Allocation, Dividends und Transactions. Risk, Scenarios und Recommendations werden erst mit P8 beziehungsweise P9 freigeschaltet.

---

# 69. Instrument Detail

Route:

```text
/instrument/:id
```

Tabs:

```text
Overview
Chart
Financials
Valuation
Growth
Profitability
Momentum
News
Forecast
Model Explanation
Prediction History
```

V1 enthält Overview und Chart mit Kursquelle und Aktualität. Financials/Valuation/News folgen P5, Forecast/Model Explanation/Prediction History P7. Nicht verfügbare Ansichten werden nicht mit Mockdaten gefüllt.

---

# 70. Watchlists

Unterstützen:

```text
multiple lists
notes
tags
alerts
forecast changes
```

---

# 71. Fundamental Scores

Zuerst deterministisch.

Scores:

```text
Quality
Growth
Value
Momentum
Stability
```

Jeder Score:

```text
0..100
```

---

# 72. Kein Black-Box Score

Zu jedem Score anzeigen:

```text
Score: 82

Drivers:

ROIC               +18
FCF Margin         +14
Debt               +12
Margin stability   +10
Revenue growth      +8
...
```

---

# 73. Research Screener

Filter:

```text
country
exchange
sector
industry

market cap

P/E
P/S
EV/EBITDA

revenue growth
EPS growth

ROE
ROIC

FCF margin

debt

dividend yield

momentum

volatility

Quality Score
Growth Score
Value Score

Forecast probability
```

---

# 74. ML Universe

V1 des Modells nicht sofort auf alle weltweiten Aktien anwenden.

Start:

```text
US large/mid cap
+
Swiss large/mid cap
+
user watchlists
```

Ziel:

```text
mehrere hundert liquide Aktien
```

statt zehntausende problematisch gepflegte Instrumente.

---

# 75. ML Targets

Primäres Target:

```text
P(
stock_return >
benchmark_return
over next 30 days
)
```

Zweites Target:

```text
expected 30d excess return
```

Weiteres Target:

```text
expected 30d volatility
```

Danach:

```text
90-day versions
```

Im Modellvertrag bedeuten `30d` und `90d` **30 beziehungsweise 90 Handelssitzungen des betreffenden Instruments**, nicht Kalendertage. Instrument und Benchmark verwenden denselben bekannten Informationsstichtag und die in Abschnitt 92 definierte Ausführungsregel. Zieldefinition und Markt-Kalender werden versioniert; ohne passende Benchmark-Reihe wird kein Target erzeugt.

---

# 76. Warum kein exakter Preis?

Nicht optimieren auf:

```text
AAPL will be $248.21
```

Sondern:

```text
Probability outperforming benchmark:
67 %

Expected excess return:
+4.2 %

Expected range:
-10 % ... +17 %
```

---

# 77. Feature Snapshot

Tabelle:

```text
feature_snapshot

instrument_id
as_of

feature_set_version

features JSONB

created_at
```

Alternativ später normalisierte Feature Tables.

Wichtig ist:

```text
as_of
```

Alle Features müssen an diesem Zeitpunkt bekannt gewesen sein.

Zum Snapshot gehören Dataset-/Regelversion und Verweise auf die verwendeten Canonical-Versionen. Der Builder prüft pro Feature `known_at <= as_of` und protokolliert fehlende Eingaben; er darf keine heute korrigierte Version rückwirkend als damaligen Stand verwenden.

---

# 78. Technische Features

```text
return_1d
return_5d
return_20d
return_60d
return_120d
return_252d

momentum_20d
momentum_60d
momentum_120d

RSI

MACD

SMA20
SMA50
SMA200

distance_SMA50
distance_SMA200

ATR

volatility_20
volatility_60
volatility_252

max_drawdown

volume_change
volume_zscore

relative_strength
```

---

# 79. Fundamental Features

```text
revenue_growth
EPS_growth
FCF_growth

gross_margin
operating_margin
net_margin

ROE
ROIC

debt_to_equity
net_debt_to_EBITDA

FCF_margin
FCF_yield
```

---

# 80. Valuation Features

```text
PE
forward_PE
PS
PB
EV_EBITDA
EV_FCF
FCF_yield
earnings_yield
```

Immer zusätzlich:

```text
relative to sector
relative to own history
```

---

# 81. Analyst Features

Nur wenn Datenqualität ausreichend:

```text
EPS_revision_30d
EPS_revision_90d

target_change

recommendation_change

earnings_surprise
```

Wenn historische Daten fehlen:

```text
Feature disabled
```

Nicht rückwirkend schätzen.

---

# 82. Macro Features

Beispiele:

```text
Fed rate
SNB rate
ECB rate

2Y yield
10Y yield
yield curve

inflation

VIX

credit spreads

USD/CHF
EUR/CHF

oil
```

Nur Daten verwenden, die am `as_of` Zeitpunkt bereits verfügbar waren.

---

# 83. News Features

```text
sentiment_1d
sentiment_7d
sentiment_30d

news_volume

negative_news_ratio
positive_news_ratio

sentiment_change
```

---

# 84. Missing Data

Kein erfundener Ersatz.

Regel:

> Missing is better than wrong.

Features erhalten:

```text
value
missing flag
quality
```

---

# 85. ML Models V1

Vor jedem komplexeren Modell werden No-Skill- und einfache Faktor-Baselines berechnet. Ein ML-Modell ist nur sinnvoll, wenn es diese Baselines Out-of-Sample robust übertrifft.

Reihenfolge:

```text
0A No-skill classification baseline (50 % / class prevalence)
0B Benchmark-only baseline
0C Simple momentum baseline
0D Simple quality/value ranking baseline
0E Equal-weight universe strategy baseline

1 Logistic Regression
2 LightGBM Classifier
3 XGBoost Classifier

4 Linear Regression
5 LightGBM Regressor
6 XGBoost Regressor
```

Für Regression zusätzlich mindestens:

```text
zero excess-return baseline
historical-mean baseline
```

Alle Baselines werden mit denselben Point-in-Time-, Kosten- und Execution-Regeln wie die produktiven Modelle bewertet.

Baselines und Backtest-Infrastruktur werden vor dem Training komplexerer Modelle implementiert (Abschnitte 92 und 158). Erreicht kein Modell die vorab dokumentierten Out-of-Sample-Abnahmekriterien gegenüber den Baselines, bleibt es `SHADOW`; die UI zeigt `NO RELIABLE FORECAST` statt eine scheinpräzise Prozentzahl.

---

# 86. Model Ensemble

Erst nachdem einzelne Modelle validiert wurden:

```text
Logistic
   +
LightGBM
   +
XGBoost
   ↓
weighted ensemble
```

Gewichte aus Out-of-Sample-Performance bestimmen.

Nicht manuell nach Gefühl setzen.

---

# 87. Model Calibration

Unbedingt:

```text
Platt scaling
oder
isotonic calibration
```

Ziel:

Wenn Modell sagt:

```text
70 %
```

sollten ungefähr:

```text
70 von 100
```

vergleichbaren Fällen erfolgreich sein.

Calibration darf den finalen Test-Split niemals sehen.

```text
Train model
    ↓
Validation / calibration window
    ↓
Fit calibrator
    ↓
Final untouched test period
```

Für Production später zusätzlich:

```text
rolling calibration monitoring
calibration by market regime where sample size is sufficient
```

Platt/Isotonic-Parameter und das verwendete Calibration Window werden zusammen mit der Modellversion gespeichert. Wenn Calibration sichtbar driftet, wird Confidence reduziert oder das Modell auf `SHADOW` gesetzt.

---

# 88. Training Split

Kein Random Shuffle.

Verwenden:

```text
TRAIN
past

VALIDATION
later

TEST
latest unseen period
```

Zusätzlich:

```text
walk-forward validation
purged walk-forward validation
embargo between train and validation/test
```

Bei Targets mit überlappenden Zukunftsfenstern müssen Trainingsbeispiele entfernt werden, deren Label-Zeitraum in Validation/Test hineinragt.

Beispiel für ein 30-Tage-Target:

```text
TRAIN labels end
      ↓
PURGE overlapping label windows
      ↓
EMBARGO / safety gap
      ↓
VALIDATION begins
```

Konservative V1-Regel:

```text
embargo >= target horizon
```

Später darf das Embargo datengetrieben kleiner gewählt werden, solange automatische Tests sicherstellen, dass keine Label-Überlappung oder Informationsleckage entsteht.

---

# 89. Beispiel Walk Forward

```text
Train:
2012–2018

Validate:
2019

Train:
2012–2019

Validate:
2020

Train:
2012–2020

Validate:
2021
```

usw.

Konkrete Zeiträume hängen von verfügbarer Datenhistorie ab.

---

# 90. Data Leakage Tests

Automatische Tests müssen prüfen:

```text
known_at <= prediction_time

price_timestamp <= prediction_time

news_published_at <= prediction_time

fundamental_known_at <= prediction_time
```

Wenn verletzt:

```text
FAIL TRAINING
```

---

# 91. Survivorship Bias

Ein reales Problem bei kostenlosen Daten.

Deshalb:

```text
universe_membership
```

Tabelle anlegen:

```text
instrument_id
universe
valid_from
valid_to
source
```

Ab Start der App historische Membership selbst archivieren.

Historische Backtests mit unvollständiger Membership klar markieren:

```text
SURVIVORSHIP_BIAS_RISK
```

---

# 92. Backtest Engine

Eigener Modulbereich:

```text
ml/backtesting/
```

Input:

```text
model
universe
start
end
rebalance frequency
position limits
transaction costs
benchmark
execution policy
```

## Execution-Time Contract

Jedes Backtest-Signal benötigt explizit:

```text
signal_generated_at
information_cutoff_at
tradable_at
execution_price_type
execution_price_timestamp
```

Kernregel:

> Wenn der Schlusskurs von Tag `t` zur Feature- oder Signalberechnung verwendet wurde, darf derselbe Schlusskurs nicht als rückwirkend handelbarer Ausführungspreis verwendet werden.

V1-Default beispielsweise:

```text
Signal uses t close
        ↓
tradable_at = next valid session
        ↓
execution = t+1 open
```

Alternativ dürfen klar dokumentierte VWAP-/Next-Close-Regeln verwendet werden. Die Execution Policy wird versioniert und ist Teil jedes Backtest-Ergebnisses.

Der Ausführungsvertrag, Markt-Kalender, Kostenmodell und die Reproduzierbarkeit des Backtests werden **vor** dem Vergleich von ML-Modellen gebaut. Backtests mit fehlender damaliger Universe-Membership oder unbekanntem `known_at` werden ausgeschlossen oder sichtbar als methodisch eingeschränkt gekennzeichnet. Signal und Ausführung dürfen nie denselben Schlusskurs nutzen, wenn dieser Schlusskurs zur Signalbildung nötig war.

---

# 93. Backtest Kosten

Auch privat nicht ignorieren:

```text
commission
spread
slippage
```

Konfigurierbar.

---

# 94. Backtest Metrics

```text
CAGR

Sharpe
Sortino

Max Drawdown

Volatility

Alpha
Beta

Win Rate

Turnover

Transaction Costs
```

---

# 95. ML Metrics

Classification:

```text
ROC-AUC
PR-AUC
Precision
Recall
F1
Brier Score
Calibration Error
```

Regression:

```text
MAE
RMSE
correlation
rank correlation
```

Financial:

```text
excess return
alpha
Sharpe
drawdown
```

---

# 96. Model Registry

MLflow verwenden.

Jedes Modell speichert:

```text
model_version
dataset_version
feature_version
code_commit

training period
validation period
test period

parameters
metrics

artifact
```

---

# 97. Model Promotion

Application-level Statuses:

```text
EXPERIMENT
VALIDATION
SHADOW
PRODUCTION
RETIRED
```

Diese Statuses werden in der eigenen Model Registry/DB und zusätzlich als MLflow Tags gespeichert.

Für aktive Modellreferenzen MLflow-Aliases verwenden:

```text
@champion
@challenger
```

Nicht die Business-Logik an MLflow-interne Lifecycle-Stages koppeln. Dadurch bleibt die Promotion-Logik unabhängig von Änderungen am MLflow Registry Workflow.

Ein Modell darf nur `PRODUCTION` / `@champion` werden, wenn es den aktuellen Champion auf relevanten OOS-Metriken mindestens erreicht und alle Data-Leakage-, Calibration-, Robustness- und Execution-Tests besteht.

---

# 98. Prediction Registry

Jede echte Prognose speichern.

```text
prediction

id
instrument_id

generated_at
horizon

model_version

probability_outperform

expected_return
expected_excess_return

expected_volatility

lower_bound
upper_bound

uncertainty_method
interval_level
empirical_coverage

feature_snapshot_id

created_at
```

Produktive Predictions sind append-only. Auch der Zustand `NO RELIABLE FORECAST` wird mit Zeit, Eingabequalität und Ablehnungsgrund protokolliert; er wird nicht durch einen stillen Fallback ersetzt.

---

# 99. Prediction Outcome

Nach Ablauf:

```text
actual_return
benchmark_return
actual_excess_return

correct

evaluated_at
```

---

# 100. Prognosen niemals löschen

Wenn das Modell falsch lag:

```text
bleibt die Prognose sichtbar
```

Das ist ein Kernfeature.

---

## Forecast Uncertainty Method

`lower_bound` und `upper_bound` dürfen nicht als frei gewählte `prediction ± standard deviation`-Spanne entstehen.

V1/V2 bevorzugt:

```text
Quantile Regression
oder
Conformal Prediction
```

Speichern:

```text
uncertainty_method
interval_level
calibration_window
empirical_coverage
```

Beispiel:

```text
Expected excess return: +4.2 %
80 % prediction interval: -8.5 % ... +14.9 %
Method: conformal-v1
Observed OOS coverage: 78.6 %
```

Wenn die empirische Coverage deutlich schlechter als das Ziel ist, Confidence reduzieren und bei starker Abweichung `NO RELIABLE FORECAST` erlauben.

---

# 101. Forecast UI

Beispiel:

```text
NVIDIA

30-Day Outlook

Bullish

Outperform probability
68 %

Expected excess return
+4.7 %

Expected range
-12 % ... +19 %

Confidence
Medium-High

Model
equity30-v3.2
```

---

# 102. Forecast Explanation

Mit SHAP:

```text
Positive factors

+ EPS revision
+ Revenue growth
+ Momentum
+ Relative strength


Negative factors

- Valuation
- High volatility
- Sector concentration
```

---

# 103. Prediction History UI

```text
Generated     Forecast     Actual

03 Aug        +5.4 %       +7.1 %
10 Aug        +3.8 %       -2.0 %
17 Aug        -1.1 %       -3.2 %
```

---

# 104. Risk Engine

Portfolio-Metriken:

```text
annualized volatility
beta
maximum drawdown

VaR 95 %
CVaR 95 %

correlation

sector exposure
country exposure
currency exposure

concentration
```

---

# 105. Annualized Volatility

Daily returns:

```text
std(daily_returns)
*
sqrt(252)
```

---

# 106. Beta

```text
cov(portfolio, benchmark)
/
variance(benchmark)
```

---

# 107. Historical VaR

Zum Beispiel:

```text
95 % historical VaR
```

aus Portfolio-Tagesreturns.

Nicht als sichere Maximalverlustgrenze darstellen.

---

# 108. CVaR

Durchschnitt der Returns:

```text
worse than VaR threshold
```

---

# 109. Concentration

Mehrere Messungen:

```text
largest position
top 3 positions
top 5 positions
HHI
sector concentration
```

---

# 110. Correlation Engine

Berechnen:

```text
30d
90d
252d
```

Rolling Correlations.

Warnung erzeugen, wenn:

```text
correlation increases materially
```

---

# 111. Portfolio Health

Subscores:

```text
Diversification
Concentration
Volatility
Quality
Currency Risk
Liquidity
```

Keine undokumentierte Black Box.

Jede Teilnote muss erklärbar sein.

---

# 112. Scenario Engine

V1 Scenarios:

```text
S&P 500 -10 %
S&P 500 -20 %

NASDAQ -20 %

Technology -25 %

USD/CHF -10 %

EUR/CHF -10 %

Volatility spike
```

---

# 113. Simple Scenario Method

Für direkten Asset-Schock:

```text
position impact =
position value
*
shock
```

Für market shocks:

```text
estimated impact =
position beta
*
market shock
```

Später Factor Models ergänzen.

---

# 114. What-If Engine

User:

```text
Buy CHF 5'000 NVDA
```

Simuliere:

```text
new allocation
new concentration
new volatility
new correlation
new sector exposure
new currency exposure
```

Originalportfolio niemals verändern.

---

# 115. Recommendation Engine

Empfehlungen kommen NICHT vom LLM.

Input:

```text
Portfolio
+
Risk
+
Forecast
+
Fundamentals
+
Valuation
+
Correlation
+
User preferences
```

Vor jedem Scoring gilt ein Hard-Eligibility-Filter:

```text
data quality sufficient?
forecast reliable?
instrument active / tradable?
minimum history available?
liquidity sufficient for configured use?
corporate-action state valid?
portfolio constraints compatible?
```

Wenn ein Hard Gate fehlschlägt:

```text
INSUFFICIENT_DATA
oder
INELIGIBLE
```

Das Instrument gelangt dann nicht in das normale Recommendation-Ranking. Ein hoher ML-Score darf schlechte oder unvollständige Grunddaten nicht überstimmen.

Die Engine wird erst nach validierter Risiko- und Szenarioanalyse aktiviert. Vor ihrer Freigabe werden Eligibility-Regeln und eine Recommendation-Strategie mit denselben Point-in-Time- und Ausführungsregeln wie die Forecasts rückgetestet. Scheitert ein Gate, erzeugt die Engine nur den strukturierten Abstention-Status; das LLM darf ihn nicht überschreiben.

---

# 116. Recommendation Categories

```text
CONSIDER_INCREASE

HOLD

WATCH

REVIEW_REDUCE

AVOID_NEW_EXPOSURE

INSUFFICIENT_DATA
INELIGIBLE
```

`INSUFFICIENT_DATA` und `INELIGIBLE` sind Abstention-/Eligibility-Ergebnisse und werden nicht als positive oder negative Investmentmeinung interpretiert.

Nicht als Garantie darstellen.

---

# 117. Recommendation Score

Beispielstruktur:

```text
Expected Return Score
          +
Forecast Confidence
          +
Quality Score
          +
Valuation Score
          +
Momentum Score
          -
Risk Penalty
          -
Concentration Penalty
          -
Correlation Penalty
```

Gewichtungen müssen dokumentiert und backgetestet werden.

---

# 118. Portfolio Context

Beispiel:

Eine gute Aktie kann trotzdem:

```text
AVOID_NEW_EXPOSURE
```

bekommen, wenn:

```text
Portfolio already contains
35 % semiconductor exposure
```

Das ist ein wichtiges Alleinstellungsmerkmal.

---

# 119. Recommendation Explanation

Beispiel:

```text
NVDA

WATCH / NO ADDITIONAL EXPOSURE

Company outlook:
Positive

Portfolio impact:
Negative

Why?

+ strong earnings revisions
+ strong momentum

- portfolio already has 31 % semiconductors
- correlation with AMD: 0.86
- adding CHF 5'000 would increase volatility
```

---

# 120. Recommendation History

Speichern:

```text
recommendation

generated_at

portfolio_snapshot
model_versions
rules_version

input metrics
output
explanation
```

Damit können frühere Empfehlungen rekonstruiert werden.

---

# 121. Lokaler AI Assistant

Der Assistant erhält Tools.

Nicht einfach einen riesigen Prompt.

Beispiel:

```text
getPortfolio()
getHolding()
getInstrument()
getFinancials()
getForecast()
getRisk()
getNews()
getPredictionHistory()
runScenario()
```

Der Assistent folgt der strukturierten Recommendation Engine in der Roadmap. Er kann bereits gespeicherte Portfolio-, Research-, Forecast- und Recommendation-Ergebnisse mit Quellen erklären; ein fehlendes lokales Modell darf deren Berechnung oder Anzeige nicht blockieren.

---

# 122. Assistant Flow

```text
Question
 ↓
Intent
 ↓
Select tools
 ↓
Retrieve structured data
 ↓
Retrieve relevant documents
 ↓
LLM
 ↓
Answer + Sources
```

---

# 123. Assistant darf nicht

```text
invent prices
invent fundamentals
modify predictions
fabricate sources
execute trades
```

---

# 124. RAG

Dokumente:

```text
SEC filings
annual reports
earnings releases
company reports
news
```

Pipeline:

```text
document
 ↓
extract
 ↓
clean
 ↓
chunk
 ↓
embedding
 ↓
pgvector
```

---

# 125. Document Schema

```text
research_document

id
instrument_id

type
source

published_at
known_at

title

object_path
content_hash

created_at
```

Chunks:

```text
document_chunk

document_id
chunk_index
content
embedding
```

---

# 126. PDF Verarbeitung

Pipeline:

```text
Download
 ↓
Store original PDF
 ↓
Text/table extraction
 ↓
Validation
 ↓
RAG indexing
```

LLM darf Tabellen nicht ungeprüft als Ground Truth interpretieren.

---

# 127. Assistant Sources

Antworten sollen beispielsweise anzeigen:

```text
Sources

Apple 10-Q
SEC
2026-08-01

Apple Q3 Earnings Release
2026-08-01
```

---

# 128. Intelligent Alerts

Typen:

```text
price threshold
forecast changed
risk increased
concentration increased
earnings upcoming
major negative news
fundamental deterioration
model confidence changed
```

---

# 129. Forecast Change Alert

Trigger beispielsweise:

```text
probability change >= 15 percentage points
```

oder Kategorie:

```text
Bullish → Neutral
```

---

# 130. Portfolio Risk Alert

Beispiele:

```text
single position > 20 %

sector > 40 %

portfolio volatility +25 %

correlation materially increased
```

Grenzen konfigurierbar.

---

# 131. Daily Brief

Automatisch erzeugen:

```text
Portfolio change

Important holdings news

Earnings

Forecast changes

Risk changes

Macro events

Noisy information excluded
```

---

# 132. Time Machine

Eines der späteren Kernfeatures.

User wählt:

```text
2025-10-03
```

App zeigt:

```text
prices available then

fundamentals known then

news known then

model prediction then

portfolio state then
```

Daneben:

```text
what happened afterwards
```

Die UI wird erst in V3+ gebaut. Sie darf für Zeitpunkte vor der ersten nachweisbaren Archivierung nur die tatsächlich rekonstruierbaren Datenarten anzeigen und muss Lücken ausdrücklich markieren. Ein heute abrufbarer historischer Kurs ist kein Beleg dafür, dass derselbe Wert damals schon in genau dieser Form bekannt war.

---

# 133. Time Machine Voraussetzung

Dafür müssen ab Tag 1 gespeichert werden:

```text
raw snapshots

known_at

predictions

estimate snapshots

news

portfolio snapshots
```

Deshalb von Anfang an implementieren.

Die **Speichergrundlage** beginnt bei Einführung jedes Datentyps; die spätere Time-Machine-UI ist keine Voraussetzung für V1. Für Prognosen und Analystenschätzungen beginnt die eigene Historie erst mit der jeweiligen Collector-/Modellfreigabe. Frühere Zeiträume werden nicht rückwirkend als vollständig ausgegeben.

---

# 134. Authentication

Obwohl privat:

```text
Login
secure password
TOTP
sessions
```

Passwort mit:

```text
Argon2id
```

hashen.

Session Cookie:

```text
HttpOnly
Secure
SameSite
```

---

# 135. Network Security

Am Anfang sollte die App nicht frei im Internet stehen.

Empfohlen:

```text
LAN
+
WireGuard VPN
```

Zugriff von ausserhalb über VPN.

---

# 136. Reverse Proxy

```text
Caddy
```

Für:

```text
HTTPS
reverse proxy
security headers
```

---

# 137. Security Headers

Mindestens:

```text
HSTS
CSP
X-Content-Type-Options
Referrer-Policy
Permissions-Policy
```

---

# 138. Secrets

Nicht in Git.

Development:

```text
.env
```

Production später optional:

```text
SOPS + age
```

für verschlüsselte Secrets.

---

# 139. Audit Log

Auch privat sinnvoll.

```text
audit_event

timestamp
actor
event
resource
resource_id
metadata
```

Beispiele:

```text
transaction.created
transaction.deleted
portfolio.created
model.promoted
recommendation.generated
settings.changed
```

---

# 140. Scheduler

Alle Zeiten intern:

```text
UTC
```

UI:

```text
Europe/Zurich
```

---

# 141. Daily Jobs

Beispiel:

```text
00:15 UTC
Macro update

01:00 UTC
Fundamental updates

02:00 UTC
Analyst snapshot

03:00 UTC
News cleanup

22:30+ UTC
US market EOD import

after market data
Price validation

after validation
Feature calculation

after features
Predictions

after predictions
Alerts
```

Exakte Börsenzeiten nicht hardcoden.

Market Calendar verwenden.

---

# 142. Market Calendar

Python Library einsetzen, die Exchange Trading Calendars unterstützt.

Beachten:

```text
weekends
holidays
half-days
DST
```

---

# 143. Collector Interface

Jeder Data Collector implementiert ungefähr:

```text
fetch()
parse()
normalize()
validate()
persist_raw()
persist_canonical()
```

---

# 144. Collector Health

Für jeden Connector speichern:

```text
last_success
last_failure

records_received
records_accepted
records_rejected

latency

error
```

---

# 145. Retries

Netzwerkfehler:

```text
retry 3–5 times
```

mit:

```text
exponential backoff
+
jitter
```

Kein aggressives Endlos-Retry.

---

# 146. Caching

Nicht jeden Seitenaufruf direkt an Yahoo schicken.

```text
User
 ↓
API
 ↓
Local DB / cache
```

Collector aktualisiert Daten separat.

---

# 147. Data Freshness

UI zeigt immer:

```text
Source
Last updated
Quality
```

Beispiel:

```text
Price
Yahoo Finance

Updated
22:05

Cross-checked
Yes

Quality
High
```

---

# 148. Monitoring

Self-hosted:

```text
Prometheus
Grafana
Loki
```

Optional:

```text
OpenTelemetry
```

Für V1-Produktivbetrieb sind strukturierte Logs, Prometheus/Grafana-Grundmetriken und Alarmierung für API-/Collector-/Backup-Ausfälle erforderlich. Loki und umfangreiche ML-/LLM-Metriken werden erst mit den entsprechenden Phasen ergänzt.

---

# 149. Monitoring Metrics

App:

```text
API response time
API errors
DB latency
queue depth
```

Data:

```text
stale prices
failed imports
source disagreement
```

ML:

```text
prediction distribution
model errors
feature drift
```

AI:

```text
LLM latency
LLM failures
RAG retrieval failures
```

---

# 150. Backups

Täglich:

```text
PostgreSQL backup
MinIO metadata/data backup
config backup
```

Ziel:

```text
separate NAS/server
```

Vor produktiver V1-Nutzung existieren tägliche Backups für PostgreSQL und MinIO-Rohdaten auf einem getrennten Ziel sowie ein dokumentiertes Restore-Verfahren. Konfiguration und Schlüsselmaterial werden getrennt, geschützt und wiederherstellbar aufbewahrt. Backup-Erfolg und letztes erfolgreiches Restore-Datum sind sichtbar.

---

# 151. Backup Retention

Beispielsweise:

```text
7 daily
4 weekly
6 monthly
```

---

# 152. Restore Tests

Regelmässig:

```text
restore database
restore MinIO
start test instance
verify
```

Ein Backup gilt nicht als sicher, solange ein Restore nie getestet wurde.

V1-Produktionsfreigabe verlangt mindestens einen erfolgreichen Restore in eine isolierte Testinstanz mit Prüfung von Datenbank, Rohobjekt, Login und Portfolio-Wert. Danach werden Restore-Tests regelmässig wiederholt und protokolliert.

---

# 153. Tests

## Unit

```text
portfolio calculations
FX
returns
risk metrics
scores
recommendation rules
```

## Integration

```text
database
collectors
MinIO
Valkey
ML inference
```

## E2E

```text
login
create portfolio
add transaction
view portfolio
view forecast
run scenario
ask assistant
```

Meilenstein-Tests prüfen zusätzlich negative Fälle: fehlender/staler Preis, Quellenkonflikt, fehlender FX-Wert, Split plus Dividende, rückwirkende Korrektur und abgewiesene Quelle. ML-Tests prüfen `known_at`, Universe-Membership, Label-Überlappung, Kosten und die Trennung von Signal- und Ausführungszeit. Ausfall von Quelle oder LLM muss einen sichtbaren Zustand statt erfundener Daten erzeugen.

---

# 154. Golden Portfolio Tests

Fixe Testportfolios erstellen.

Beispiel:

```text
portfolio_golden_001.json
```

Mit vorher bekannten:

```text
market value
cost basis
return
dividends
FX impact
```

Damit verhindern wir Regressionen.

---

# 155. Data Connector Fixtures

Nie Tests live gegen Yahoo ausführen.

Speichern:

```text
tests/fixtures/yahoo/
tests/fixtures/sec/
tests/fixtures/snb/
```

Parser laufen gegen gespeicherte echte Beispielresponses.

---

# 156. Scraper Snapshot Tests

Wenn Website-Struktur geändert wird:

```text
test fails
```

statt unbemerkt falsche Daten zu speichern.

---

# 157. ML Reproducibility

Jeder Trainingslauf speichert:

```text
Git commit
dataset version
feature version
random seed
dependencies
parameters
```

Reproduzierbarkeit umfasst auch verwendete Raw-/Canonical-Versionen, Universe-Membership, Markt-Kalender, Target-, Corporate-Action- und Execution-Policy-Version sowie Quelle der FX-Reihe. Der Test rekonstruiert eine gespeicherte Prognose aus genau diesen Eingaben oder meldet explizit, welche historische Quelle fehlt.

---

# 158. Development Phases

Diese Roadmap ist die einzige normative Phasenfolge. Abschnitt 204 ist ihre Arbeitsliste, Abschnitte 206–211 beschreiben dieselben Meilensteine. Ein Meilenstein gilt nur als erreicht, wenn seine Abnahme und der angegebene Zustand bei fehlenden Daten funktionieren. Der Ziel-Stack bleibt bestehen, wird aber erst dann gestartet, wenn sein Dienst gebraucht wird.

| Phase | Voraussetzung und Lieferung | Überprüfbare Abnahme | Bei fehlenden Daten oder Diensten |
| --- | --- | --- | --- |
| **P0 Projektgrundlage** | Neues Repository, README, dieser Masterplan, ADRs für Provenienz, Kursanpassung und Backtest-Ausführung; Definition von Umgebungen, Secrets und Source-Gate. | Struktur, ADR-Vorlagen und lokale Startanleitung sind vorhanden; keine Secrets im Repository. | Noch keine produktiven Daten oder Prognosen. |
| **P1 Kern und Speichergrundlage** | Docker Compose mit PostgreSQL/pgvector, FastAPI, Next.js, Valkey, Celery Worker/Beat und MinIO; Migrationen, Session-Login/TOTP, Audit, strukturierte Logs, Health Checks, Raw-Storage und Versionierungsvertrag. | Web/API/DB/Queue/Object-Store starten; Login und Audit funktionieren; ein Rohobjekt wird unverändert gespeichert, per Hash geprüft und über `raw_ingestion` wiedergefunden. | Ausfall einer Pflichtkomponente ist ein sichtbarer Health-Fehler; kein Collector läuft. |
| **P2 Instrumente und freigegebene Quellen** | Instrument Master mit zeitgültigen Kennungen, OpenFIGI-Mapping, Source Registry, Rechte-/Rate-Limit-Gate und Provider-/CSV-Vertrag. | Ticker, ISIN und FIGI führen nur bei eindeutiger Prüfung zum selben Instrument; ungeklärte Treffer werden markiert; gesperrte Quellen starten nicht. | Manuelle Instrumentanlage und CSV-Mapping/-Vorschau bleiben möglich; der Datenimport beginnt erst mit P3. |
| **P3 Geprüfte Markt- und FX-Daten** | Erster **freigegebener** Kurs-Collector oder CSV-Import, Canonical-Versionen, Quarantäne, Cross-Checks, Corporate Actions, explizite Total-Return-Policy, SNB/ECB-FX und Data-Freshness-Status. | Golden Fixtures für US-/CH-Aktie, ETF, Split, Dividende, Korrektur, Quellenkonflikt und CHF/USD/EUR bestehen; Roh- und Canonical-Versionen sind rückverfolgbar. | Kein erfundener Ersatz; letzter validierter Wert mit Datum oder `DATA_UNAVAILABLE`. |
| **P4 Portfolio und V1-Freigabe** | Konten, Transaktionen, Cash-/Positionsrechnung, TWR/XIRR, Dashboard, Portfolio-/Instrumentseiten und V1-Datenqualitätsseite. Vor produktivem Einsatz Caddy/VPN-Zugriff, Grundmetriken/Alarmierung, getrennte Backups und erfolgreicher Restore-Test. | Login, Portfolioanlage, Transaktion, Marktwert, P/L, Performance, Allokation und Herkunft lassen sich mit Golden Portfolio Tests und UI-End-to-End-Test nachvollziehen; Backup-Restore in isolierter Instanz gelingt. **Ergebnis: V1 Private Investment Tracker.** | Fehlende Preise/FX führen zu sichtbaren unvollständigen Bewertungen; Cash und Transaktionen bleiben korrekt, kein Nullwert als Ersatz. |
| **P5 Fundamentals und Research** | SEC mit globalem Fair-Access-Limit, Company-IR/weitere erlaubte Quellen, Fundamentals mit `known_at`, Bewertung, Scores, Watchlists, News und Schätzungssnapshots jeweils ab erster Collector-Nutzung. | Filing und abgeleitete Kennzahl stimmen für Testunternehmen; Restatements und fehlende Historie sind sichtbar; Research-Suche/Screener verwenden nur validierte Werte. **Ergebnis: V1.5 Research.** | Fehlender Fakt oder nicht freigegebene Quelle wird als Lücke angezeigt; Score/Feature wird nötigenfalls ausgesetzt. |
| **P6 Point-in-Time und Backtest-Basis** | Historische Universe-Membership, Feature-/Dataset-Versionen, Markt-Kalender, Target- und Execution-Vertrag, Kostenmodell, purged Walk-Forward und einfache No-Skill-/Faktor-Baselines. | Automatische Tests verhindern Zukunftsdaten, überlappende Labels und Ausführung zum bereits genutzten Schlusskurs; Baselines sind reproduzierbar. | Historisch nicht belegte Beobachtungen werden ausgeschlossen oder als methodisch eingeschränkt ausgewiesen. |
| **P7 Modelle und V2-Forecasts** | Erst jetzt Logistic Regression/LightGBM/XGBoost und gegebenenfalls Regression; OOS-Vergleich, Kalibrierung, Unsicherheitsintervalle, MLflow/Model Registry, unveränderliche Prognosen, Model Cards und Performance-/Prediction-History-UI. | Mindestens ein Modell erfüllt vorab festgelegte OOS-, Kalibrierungs-, Coverage- und Robustheitsgates gegenüber Baselines; gespeicherte Vorhersage ist reproduzierbar. Erst dann: **V2 Investment Intelligence.** | Ohne bestandenes Modell oder verlässliche Features: `NO RELIABLE FORECAST`, dokumentiert und sichtbar; P7/V2 bleibt offen. |
| **P8 Risiko und Szenarien** | Konzentration, Volatilität, Korrelation, VaR/CVaR, FX-/Markt-Stress und What-if auf validierten Portfolio-Snapshots. | Tests zeigen nachvollziehbare Änderungen für Kurs-, FX- und Konzentrationsschocks; Originalportfolio bleibt unverändert. **Ergebnis: V2.5 Portfolio Intelligence.** | Kennzahlen mit zu wenig Historie oder fehlenden Preisen werden ausgesetzt und begründet. |
| **P9 Strukturierte Empfehlungen** | Eligibility-Gates, persönliche Grenzen, Portfolio-Kontext, regelbasierte Rangfolge, Recommendation-Historie und eigener Point-in-Time-Strategie-Backtest. | Unzulässige Kandidaten erhalten nur `INELIGIBLE`/`INSUFFICIENT_DATA`; zulässige Aktionen zeigen Wirkung, Risiken, Kosten und Regel-/Modellversion. **Ergebnis: V3 ohne LLM-Abhängigkeit.** | Fehlender Forecast oder Risk-Input verhindert die betroffene Empfehlung, nicht das Portfolio. |
| **P10 Assistent und V3+-Ausbau** | Ollama/RAG als Erklärungsschicht, Alerts, Daily Brief, robuster Optimizer und Time-Machine-UI. Loki und erweiterte Observability werden nach Bedarf ergänzt. | Zitate verweisen auf gespeicherte Daten; LLM-Ausfall lässt quantitative Ergebnisse verfügbar; Optimizer-Stresstest und historische Ansicht kennzeichnen Unsicherheit/Lücken. **Ergebnis: V3+.** | Assistent/Brief dürfen fehlen; ohne historische Snapshots zeigt Time Machine keine erfundene Vergangenheit. |

**Querschnittsregeln:** Jede Phase durchläuft Spezifikation, Schema, Backend, Tests, UI, Monitoring und Dokumentation soweit zutreffend. Jeder neue Collector erfüllt vor Aktivierung Rechteprüfung, Raw-Speicherung, Provenienz, Validierung, Versionierung und Ausfallanzeige. Phase P4 ist die erste Produktionsfreigabe; die vorherigen Phasen sind lokale/testbare Inkremente. Die Produktivfreigabe wird bei fehlendem Backup-Restore oder ungeklärten Quellenrechten verweigert, auch wenn die UI bereits funktioniert.

---

# 159. API Struktur

Base:

```text
/api/v1/
```

---

# 160. Auth

```text
POST /auth/login
POST /auth/logout

GET /auth/session

POST /auth/totp/setup
POST /auth/totp/verify
```

---

# 161. Instruments

```text
GET /instruments/search

GET /instruments/{id}

GET /instruments/{id}/prices
GET /instruments/{id}/financials
GET /instruments/{id}/metrics
GET /instruments/{id}/news
GET /instruments/{id}/forecast
GET /instruments/{id}/prediction-history
```

---

# 162. Portfolio

```text
GET /portfolios
POST /portfolios

GET /portfolios/{id}
PATCH /portfolios/{id}
DELETE /portfolios/{id}
```

---

# 163. Transactions

```text
GET /portfolios/{id}/transactions
POST /portfolios/{id}/transactions

PATCH /transactions/{id}
DELETE /transactions/{id}
```

---

# 164. Analytics

```text
GET /portfolios/{id}/performance
GET /portfolios/{id}/allocation
GET /portfolios/{id}/risk
GET /portfolios/{id}/correlation
```

---

# 165. Scenarios

```text
POST /portfolios/{id}/scenarios

GET /scenarios/{id}
```

---

# 166. Recommendations

```text
POST /portfolios/{id}/recommendations/generate

GET /portfolios/{id}/recommendations

GET /recommendations/{id}
```

---

# 167. Assistant

```text
POST /assistant/conversations

POST /assistant/conversations/{id}/messages

GET /assistant/conversations/{id}
```

---

# 168. Data Quality

```text
GET /data-quality/status

GET /data-quality/sources

GET /data-quality/issues

GET /data-quality/quarantine
```

---

# 169. Models

```text
GET /models

GET /models/{id}

GET /models/{id}/performance

GET /models/{id}/calibration
```

---

# 170. Prediction

```text
GET /predictions/{instrument_id}

GET /predictions/{instrument_id}/history
```

---

# 171. First Database Tables

Migrationen werden entlang der Phasen aus Abschnitt 158 angelegt; nicht sämtliche V3+-Tabellen müssen vor V1 existieren.

| Phase | Tabellen/Verträge |
| --- | --- |
| P1 | `users`, `sessions`, `audit_events`, `data_sources`, `raw_ingestions`, `jobs`; Raw-Objektverweis und Versionierungsmetadaten. |
| P2 | `instruments`, `instrument_identifiers`; zeitgültige Kennungen und eindeutige Zuordnung. |
| P3 | `price_daily` als aktuelle Lesesicht, `price_daily_version` append-only, versionierte `corporate_actions`/`fx_rates`, `data_quarantine`; Referenzen zu Raw-Ingestion und Regelversion. |
| P4 | `portfolios`, `portfolio_accounts`, `transactions`, `position_snapshots`, `portfolio_snapshots`, Cash-/Benchmark-Daten. |
| P5 | `fundamental_facts`, `derived_metrics`, `news_articles`, `news_instruments`, `estimate_snapshots`, Watchlists. |
| P6–P7 | `universe_membership`, `feature_snapshots`, Dataset-/Backtest-Metadaten, `models`, `predictions` und Outcomes. |
| P8–P10 | Versionierte Risiko-/Szenarioergebnisse, `recommendations`, Alerts und Assistant-/Time-Machine-Metadaten nur bei Bedarf. |

Migrationsschritte müssen vor der jeweils zugehörigen Collector- oder Feature-Aktivierung laufen. Historische Versionen und Raw-Objekte werden nicht durch `UPDATE` überschrieben.

---

# 172. First Screens

Für V1 werden nur diese Seiten benötigt:

```text
/login
/dashboard
/portfolio
/portfolio/:id
/instrument/:id
/settings
/data-quality
```

Die Seiten zeigen Source/Freshness und `DATA_UNAVAILABLE` sichtbar an. Research-, Forecast-, Risiko-, Empfehlungs- und Assistant-Ansichten folgen erst mit ihren Phasen aus Abschnitt 158; leere oder gefälschte Platzhalter sind keine V1-Anforderung.

---

# 173. Erste Instrumente zum Testen

Ein kleines heterogenes Set verwenden.

Beispielsweise:

```text
AAPL
MSFT
NVDA

NESN.SW
NOVN.SW
ROG.SW

SPY
VT
```

Damit testest du:

```text
US stocks
Swiss stocks
ETFs
USD
CHF
```

---

# 174. Erste Portfolio Fixture

Beispiel:

```text
Portfolio base currency:
CHF

AAPL
10 shares

MSFT
5 shares

NESN.SW
20 shares

Cash:
CHF 5'000
```

Mit historischen Transaktionen.

---

# 175. Quality First Rule

Kein Feature wird veröffentlicht, wenn die zugrunde liegenden Daten fragwürdig sind.

Reihenfolge:

```text
Correct
↓
Reproducible
↓
Explainable
↓
Fast
↓
Pretty
```

Nicht umgekehrt.

---

# 176. Keine heimlichen Fallbacks

Wenn Yahoo nicht funktioniert:

Nicht:

```text
return 0
```

oder:

```text
return fake price
```

Sondern:

```text
DATA_UNAVAILABLE
```

und letzten validierten Wert anzeigen:

```text
Last validated:
2026-10-02
```

---

# 177. Keine Mockdaten in Production

Fixtures nur:

```text
development
test
```

Production:

```text
real data
or
explicitly unavailable
```

---

# 178. UI Confidence

Bei Daten anzeigen:

```text
Verified
Cross-checked
Single source
Stale
Estimated
```

---

# 179. Forecast Confidence

Forecast Confidence darf nicht einfach identisch mit:

```text
probability_outperform
```

sein.

Confidence berücksichtigt beispielsweise:

```text
model calibration
feature completeness
data quality
model agreement
market regime uncertainty
```

---

# 180. Forecast Abstention

Das Modell muss sagen dürfen:

```text
NO RELIABLE FORECAST
```

Wenn:

```text
missing data
poor calibration
IPO too new
extreme market regime
models strongly disagree
```

Das ist besser als eine schlechte Prognose.

---

# 181. Recommendation Abstention

Ebenso:

```text
INSUFFICIENT DATA
```

ist eine gültige Recommendation.

---

# 182. Model Agreement

Beispiel:

```text
Logistic:
61 %

LightGBM:
72 %

XGBoost:
69 %
```

Ensemble:

```text
68 %
```

Agreement anzeigen.

Wenn:

```text
45 %
81 %
52 %
```

Confidence reduzieren.

---

# 183. Model Regimes

Später unterscheiden:

```text
bull market
bear market
high volatility
low volatility
recession
rate shock
```

Performance je Regime speichern.

---

# 184. Recommendation Backtest

Nicht nur Forecast-Modell testen.

Auch Recommendation Strategy separat backtesten.

Beispiel:

```text
Top recommendation basket

vs

benchmark
```

---

# 185. Personal Preferences

Private Settings:

```text
risk tolerance
investment horizon
preferred assets
excluded assets

max position
max sector exposure

minimum cash
```

---

# 186. Default Constraints

Beispiele, aber vom Nutzer änderbar:

```text
max position:
15 %

max sector:
35 %

minimum cash:
5 %
```

Nicht als allgemeingültige Investmentregeln darstellen.

---

# 187. Portfolio Optimizer

Input:

```text
current portfolio

forecast returns
covariance

constraints
```

Die rohe Sample-Covariance wird nicht blind verwendet. Die **erste Optimizer-Version in P10** verwendet standardmässig eine robuste/shrinked Covariance-Schätzung, beispielsweise:

```text
Ledoit-Wolf shrinkage
```

oder eine vergleichbare dokumentierte Shrinkage-Methode.

Constraints der ersten Optimizer-Version mindestens:

```text
no shorting
no leverage
max position
max sector exposure
minimum cash
target / maximum turnover
minimum meaningful position size
```

Transaktionskosten werden auch im Optimizer berücksichtigt, damit kleine theoretische Rebalancing-Vorteile nicht zu unnötigem Turnover führen.

Output mehrere mögliche Portfolios.

Methoden:

```text
minimum variance
risk parity
max Sharpe

constrained expected-return optimization
```

Nicht blind das mathematische Optimum empfehlen.

---

# 188. Optimizer Stability

Vor Anzeige Stress Tests:

```text
expected returns ± uncertainty
correlation perturbation
volatility perturbation
```

Wenn Portfolio stark auf minimale Inputänderungen reagiert:

```text
LOW ROBUSTNESS
```

anzeigen.

---

# 189. Daily Data Workflow

Nach Börsenschluss, nur für bereits freigegebene Quellen und nur für die in der aktuellen Phase vorhandenen Module:

```text
1 Fetch prices and corporate actions
2 Store each raw response and raw_ingestion immediately
3 Parse and normalize; retain the source version
4 Validate OHLC, currency, calendar and corporate actions
5 Fetch only an approved fallback where needed; store its raw response
6 Cross-check and quarantine unresolved conflicts
7 Append canonical price/action versions with provenance
8 Resolve FX for the valuation date; append its version
9 Recompute portfolio and immutable snapshot
10 From P6: calculate point-in-time features
11 From P7: forecast or store abstention
12 From P10: evaluate alerts and daily brief
```

Jeder Snapshot entsteht beim jeweiligen Schritt, nicht gesammelt erst am Schluss. Scheitert ein Schritt, werden abhängige Berechnungen ausgesetzt und mit dem letzten validierten Stand/`DATA_UNAVAILABLE` angezeigt. Der Markt-Kalender steuert die Ausführung; Uhrzeiten werden nicht als feste Börsenschlusswerte angenommen.

---

# 190. Fundamental Workflow

```text
1 Detect new filing

2 Download original

3 Save raw

4 Parse

5 Normalize XBRL

6 Validate units/currency

7 Store facts

8 Recompute derived metrics

9 Recompute score

10 Recompute features

11 Trigger forecast refresh
```

Vor dem Speichern eines Facts werden `known_at`, Filing-Version und `raw_ingestion_id` gesetzt. Ein späteres Filing oder Restatement erzeugt eine neue Version. Der Forecast-Refresh läuft nur, wenn P7 aktiv ist und seine Eingaben die Quality-Gates bestehen.

---

# 191. News Workflow

```text
1 Discover

2 Download metadata/content

3 Deduplicate

4 Identify companies

5 Sentiment

6 Embedding

7 Store

8 Update news features

9 Evaluate important-news alert
```

Originalinhalt und Abrufmetadaten werden unmittelbar nach dem Download als Raw-Objekt gespeichert. Sentiment, Embeddings und Alerts sind optionale spätere Schritte; fehlt ein Modell, bleibt die Nachricht mit Herkunft und Entdeckungszeit verfügbar.

---

# 192. Prediction Workflow

```text
1 Load canonical data

2 Verify freshness

3 Build point-in-time features

4 Validate features

5 Run models

6 Calibrate probabilities

7 Ensemble

8 Calculate uncertainty

9 Calculate SHAP

10 Store prediction

11 Compare to previous

12 Trigger alerts
```

Vor Schritt 5 gelten Modellfreigabe, Feature-Qualität und Point-in-Time-Vertrag. Scheitert ein Gate oder die Kalibrierung, wird `NO RELIABLE FORECAST` mit Grund gespeichert; Schritte 5–9 werden dann nicht durch Ersatzwerte simuliert. Alerts laufen erst in P10.

---

# 193. Recommendation Workflow

```text
1 Load latest portfolio snapshot

2 Load forecast

3 Load risk

4 Load fundamentals

5 Load user constraints

6 Run hard eligibility / data-quality gates

7 Build eligible candidate universe

8 Calculate candidate actions

9 Simulate portfolio impact

10 Rank candidate scenarios

11 Store structured recommendation

12 Optionally generate LLM explanation from P10
```

Ranking findet nur innerhalb des zulässigen Candidate Universe statt. Ohne verlässliche Forecast- und Risiko-/Szenarioeingaben entsteht `INSUFFICIENT_DATA`; die strukturierten Ergebnisse aus P9 bleiben bei LLM-Ausfall erhalten.

---

# 194. Dependency Rule

Kein LLM-Ausfall darf verhindern, dass:

```text
portfolio
forecast
risk
recommendation
```

funktionieren.

Nur die natürliche Text-Erklärung darf fehlen.

---

# 195. Offline Capability

Wenn externe Quellen vorübergehend nicht funktionieren:

App verwendet:

```text
local validated history
```

und zeigt:

```text
Data not updated since ...
```

---

# 196. Final Docker Topology

```text
Caddy
  │
  ├── Next.js
  │
  └── FastAPI
        │
        ├── PostgreSQL
        ├── Valkey
        ├── MinIO
        └── Ollama

Celery Worker
   │
   ├── Collectors
   ├── ML
   ├── News
   └── Reports

Celery Beat
   │
   └── Scheduler

Monitoring
   ├── Prometheus
   ├── Grafana
   └── Loki
```

---

# 197. Deployment auf Homelab

Für den Start genügt eine Ubuntu-Server-VM.

Darauf:

```text
Docker
Docker Compose
Git
Caddy
```

Projekt unter beispielsweise:

```text
/opt/investment-intelligence/
```

Volumes:

```text
/srv/investment/postgres
/srv/investment/minio
/srv/investment/valkey
/srv/investment/mlflow
/srv/investment/ollama
```

---

# 198. GPU

GPU ist nicht Voraussetzung für:

```text
Portfolio
Research
ML inference
LightGBM
XGBoost
Risk
Forecasting
```

GPU wird hauptsächlich für:

```text
local LLM
large embeddings
deep learning experiments
```

benötigt.

Wenn keine GPU vorhanden:

kleineres lokales Modell verwenden oder Assistant vorerst deaktivieren.

Der quantitative Kern funktioniert weiter.

---

# 199. Resource Separation später

Wenn nötig:

```text
VM 1
Web/API

VM 2
Postgres/MinIO

VM 3
ML/LLM GPU
```

Aber nicht am Anfang unnötig komplizieren.

---

# 200. Entwicklungsprinzip

Jede Phase läuft:

```text
Specification
 ↓
Schema
 ↓
Backend
 ↓
Tests
 ↓
Frontend
 ↓
Monitoring
 ↓
Documentation
```

---

# 201. Definition of Done

Eine Funktion ist erst fertig, wenn:

```text
implemented
tested
validated
typed
errors handled
logging added
monitoring added
documentation updated
```

Zur Definition of Done eines **Meilensteins** gehören zusätzlich: seine in Abschnitt 158 genannte Abnahme, Tests des Missing-Data-Zustands und bei produktiver V1-Nutzung ein protokollierter Restore. Eine nicht freigegebene Datenquelle darf trotz technisch grünem Collector nicht als fertig gelten.

---

# 202. Commit Strategie

Kleine Commits.

Beispiele:

```text
feat(data): add Yahoo daily price collector

feat(data): add raw ingestion storage

feat(portfolio): calculate weighted cost basis

test(portfolio): add dividend golden tests

feat(ml): add 30d target generator
```

---

# 203. Architekturentscheidungen dokumentieren

Verzeichnis:

```text
docs/decisions/
```

Beispiel:

```text
ADR-001-postgresql.md
ADR-002-yahoo-primary-price-source.md
ADR-003-point-in-time-data.md
ADR-004-no-llm-forecasting.md
ADR-005-price-adjustment-policy.md
ADR-006-backtest-execution-policy.md
ADR-007-snapshot-from-first-availability.md
ADR-008-model-calibration-and-uncertainty.md
ADR-009-source-rights-and-activation-gate.md
```

ADR-002 hält Yahoo als **gewünschte** Primärquelle und das Freigabe-Gate aus Abschnitt 18 fest. Ohne dokumentierte Freigabe bleibt der Yahoo-Collector deaktiviert.

---

# 204. Implementierungsreihenfolge

Die folgende Arbeitsliste konkretisiert **ausschliesslich** Abschnitt 158; ihre P0–P10-Grenzen sind identisch. Innerhalb jeder Phase gilt die angegebene Reihenfolge. Ein Phasenabschluss setzt die dortigen Abnahmekriterien voraus.

1. **P0:** Repository und Dokumentation; ADRs für Provenienz, Corporate Actions und Backtest-Ausführung; lokale/test/staging/production-Konfiguration und Source-Gate definieren.
2. **P1:** PostgreSQL/pgvector und Migrationen; FastAPI/Next.js; Valkey/Celery; MinIO-Raw-Storage; Login/TOTP, Sessions, Audit, Health und strukturierte Logs.
3. **P2:** Instrument Master/Identifier-Historie; Source Registry mit Rechteprüfung; erst danach OpenFIGI-Mapping; CSV-/Provider-Vertrag.
4. **P3:** Erst nach Raw- und Source-Gate einen freigegebenen Preis-Collector oder CSV aktivieren; Canonical-/Quarantäne-Pipeline; Cross-Checks; Corporate Actions und Rendite-Policy; SNB/ECB-FX und Freshness.
5. **P4:** Portfolio- und Transaktionsledger; Cash/Positionen; Kostenbasis und Performance; V1-UI samt Datenqualität; Caddy/VPN, Grundmonitoring, Backup und erfolgreicher Restore. **V1-Abnahme.**
6. **P5:** SEC/Company-IR mit `known_at`; Fundamentals, Valuation, Scores und Research-UI; Watchlists; News-/Schätzungssnapshots ab erster Nutzung. **V1.5-Abnahme.**
7. **P6:** Historische Universe-Membership; Feature-/Target-Versionen; Markt-Kalender, Ausführungs- und Kostenvertrag; purged Walk-Forward; einfache Baselines und Leakage-Tests.
8. **P7:** Komplexere ML-Modelle gegen die Baselines; zeitbewusste Kalibrierung und Intervalle; MLflow/Promotion; immutable Predictions, Outcomes, Model Cards und Forecast-UI. **V2-Abnahme nur bei bestandenem Modellgate; sonst sichtbare Abstention und offene Phase.**
9. **P8:** Risiko-, Korrelations-, Stress- und What-if-Engine mit Tests. **V2.5-Abnahme.**
10. **P9:** Eligibility-/Constraint- und Scoring-Engine; Recommendation-Backtest; immutable Recommendation-History und UI. **V3-Abnahme.**
11. **P10:** Lokales LLM/RAG als optionale Erklärung; Alerts, Daily Brief, Optimizer und Time-Machine-UI; Observability-Ausbau. **V3+-Abnahme.**

Collector-Snapshotting ist in P2/P3 und jeder späteren Datentyp-Phase Pflicht; es wird nicht auf P6 oder P10 verschoben. Ein fehlgeschlagenes Gate erzeugt den dokumentierten Missing-Data-Zustand statt einen stillen Fallback.

---

# 205. Was du als Erstes NICHT bauen sollst

Nicht anfangen mit:

```text
AI chat
prediction model
recommendations
mobile app
```

bevor diese Dinge funktionieren:

```text
Instrument IDs
Prices
Corporate Actions
FX
Fundamentals
Portfolio Accounting
Point-in-Time Data
```

---

# 206. Erster funktionierender Meilenstein

**V1 = Abschluss P4 aus Abschnitt 158.** Die folgenden Funktionen sind mit echten validierten oder explizit importierten Daten nutzbar:

```text
Login und sichere Session
Portfolio anlegen
Transaktion erfassen/importieren
Instrument eindeutig auflösen
Kurs/Corporate Action/FX mit Herkunft und Aktualität anzeigen
Marktwert, Cash, realisiertes und unrealisiertes P/L berechnen
Performance-Chart und Allokation anzeigen
Instrumentenseite und V1-Datenqualitätsseite öffnen
```

**Abnahme:** Golden Tests für Kauf, Verkauf, Dividende, Split und FX; End-to-End-Test von Login bis Portfolioanzeige; Quellenkonflikt/fehlender Kurs/FX zeigen `DATA_UNAVAILABLE` oder den datierten letzten validierten Wert; keine Production-Fixtures. Vor Homelab-Produktivnutzung sind Zugriffsschutz, Grundmonitoring, getrennte Backups und ein erfolgreicher isolierter Restore nachgewiesen. Yahoo ist dafür keine Pflichtquelle.

---

# 207. Zweiter Meilenstein

**V1.5 = Abschluss P5.** Fundamentals, Valuation, nachvollziehbare Scores, News, Screener und Watchlists werden auf V1 aufgebaut. SEC-/IR-Facts müssen ihre Quelle und `known_at` zeigen; korrigierte Meldungen bleiben versioniert. Analystenschätzungen und News besitzen Snapshots ab der ersten jeweiligen Nutzung.

**Abnahme:** Mindestens ein US- und ein CH/EU-Testinstrument mit nachprüfbaren Fakten; fehlende Quellen führen zu sichtbaren Lücken oder ausgesetztem Score, nicht zu ergänzten Schätzwerten. V1-Portfoliofunktionen bleiben unabhängig von Research-Collectoren verfügbar.

---

# 208. Dritter Meilenstein

**V2 = P6 und P7.** Zuerst entstehen Point-in-Time-Datensatz, Universe-/Feature-Versionen, Baselines und eine Backtest-Engine mit Zeit-/Kosten-/Execution-Vertrag. Erst danach folgen komplexere Modelle, Kalibrierung, Unsicherheitsintervalle, Model Registry und transparente Forecast-/Prediction-History-UI.

**Abnahme:** Leak-, Label-Overlap- und Same-Close-Execution-Tests sind grün; mindestens ein Modell besteht vorab dokumentierte OOS-, Calibration- und Coverage-Gates gegenüber Baselines. Wenn nicht, wird `NO RELIABLE FORECAST` mit Grund und Zeitpunkt gespeichert; V2 gilt noch nicht als erreicht. V1/V1.5 funktionieren weiter.

---

# 209. V3+ Endzustand

Nach V2 folgen **V2.5 = P8** (Risiko, Stress, What-if), **V3 = P9** (strukturierte Empfehlungen mit Eligibility, Portfolio-Kontext und eigenem Backtest) und **V3+ = P10** (lokaler Assistent, Alerts, Daily Brief, Optimizer und Time Machine). Diese Reihenfolge ist für Empfehlungen bindend: erst verlässliche Forecasts **und** Risiko-/Szenarioeingaben, dann Recommendation Engine, danach LLM-Erklärung.

Der Zielumfang umfasst weiterhin Portfolio, Research, Forecasting, Risiko, Szenarien, Empfehlungen, Assistent, Automation und Transparenz. Jedes Modul zeigt seine Datenlücken; Assistant-Ausfall beeinträchtigt die quantitativen Module nicht. Die Time Machine zeigt nur historisch belegte Zustände.

**Abnahme V3:** Zulässige und ausgeschlossene Kandidaten, Portfolio-Auswirkung, Kosten und Regelversion sind nachvollziehbar; Recommendation-Backtests bestehen ihre Point-in-Time- und Execution-Tests. **Abnahme V3+:** Quellenzitate, LLM-Ausfall, Optimizer-Stabilität und historische Datenlücken sind getestet.

---

# 210. Wichtigste Projektregeln

## Rule 1

```text
Never invent financial data.
```

## Rule 2

```text
Missing data > wrong data.
```

## Rule 3

```text
Raw data is immutable.
```

## Rule 4

```text
Production predictions are immutable.
```

## Rule 5

```text
Every important value has provenance.
```

## Rule 6

```text
Never train on future information.
```

## Rule 7

```text
Never hide bad predictions.
```

## Rule 8

```text
LLM explains.
Quant models decide.
```

## Rule 9

```text
Data quality before model complexity.
```

## Rule 10

```text
Simple model beating complex model wins.
```

## Rule 11

```text
Snapshot non-reconstructable data from first availability.
```

## Rule 12

```text
Never execute a backtest signal at a price that was not yet tradable when the signal became known.
```

## Rule 13

```text
Hard validation gates override quality scores.
```

---

# 211. Startpunkt

Die Umsetzung startet mit **P0 → P1 → P2 → P3 → P4** gemäss Abschnitt 158 und der identischen Arbeitsliste in Abschnitt 204:

```text
P0 Repository + ADRs + Quellen-/Versionierungsregeln
P1 Compose-Kern + Auth/Audit + Valkey/Celery + MinIO/Raw-Storage
P2 Instrument Master + OpenFIGI + Source-Gate + CSV-Vertrag
P3 freigegebene Kurse oder CSV + Validierung + Corporate Actions + FX
P4 Portfolio Accounting + V1-UI/Datenqualität + Backup/Restore
```

**Erster Release:** V1 nach den Tests aus Abschnitt 206. Für die lokale Umsetzung können P1–P3 einzeln demonstriert werden; produktive Nutzung beginnt erst nach P4-Freigabe. Fundamentals/Research sind P5, PIT/Backtest-Basis P6, ML/Forecast P7, Risiko/Szenarien P8, Empfehlungen P9 und Assistant/V3+-Erweiterungen P10. Es gibt keinen zweiten abweichenden Startplan.

---

# 212. Das eigentliche Qualitätsziel

Das Ziel ist nicht:

```text
"möglichst viele AI Features"
```

Das Ziel ist:

```text
hochwertige Daten
+
reproduzierbare Berechnungen
+
ehrliche Wahrscheinlichkeiten
+
gute Portfolioanalyse
+
nachvollziehbare Modelle
+
verlässliche Empfehlungen
```

Wenn eine Funktion diese Standards nicht erfüllt, wird sie nicht künstlich mit unzuverlässigen Daten fertiggestellt.

Die fertige Anwendung soll lieber sagen:

```text
Insufficient reliable data
```

als eine überzeugend aussehende, aber falsche Antwort zu produzieren.

---

## PR1-Umsetzungsnachtrag – Real Financial Data Readiness (2026-10-16)

Dieser Nachtrag konkretisiert den Datenbetrieb der bestehenden P0–P10-Roadmap; die 212 Hauptabschnitte und ihre Abhängigkeiten bleiben bestehen. Voraussetzung ist die technische P10-Abnahme. Quellenrechte, tatsächliche historische Datenqualität, P7-/P9-Validierung und Zielinstallation werden getrennt bewertet.

PR1 ergänzt gemeinsame begrenzte HTTP-/Raw-Verarbeitung, append-only Rechtebelege, private persistente Backfills, Sync-/Coverage-Zustände, den verifizierten monatlichen SNB-Vertrag, optionale kompakte Aktienkurse sowie menschlich geprüfte IR-Belege. Raw-Originale gehen jedem Parser voraus. Ein freier Zugang oder persönlicher Key ersetzt keine Rechteentscheidung. Yahoo bleibt priorisiert unter Freigabevorbehalt und gesperrt; eine zulässige manuelle Quelle bleibt der nutzbare Ersatzweg.

Vor jedem externen Request einschließlich Retry gelten aktuelles approved/enabled/in-scope Gate, öffentliche Host-/DNS-Bindung und Quoten. Wiederkehrende Collection bleibt standardmäßig deaktiviert. SNB-Monatsreferenzen ersetzen keine tägliche FX. Fehlende Historie, Actions, Membership, Open-Preise oder damalige Verfügbarkeit bleiben fehlend. Neu beobachtete Daten werden nicht rückdatiert; neue Evidenz schreibt keine alten Archive um.

Abnahme verlangt Offline-Vertragstests, P0–P10-Regression, Browserabläufe, vorhandene und frische Alembic-Migration sowie isolierten Restore einschließlich neuer Datenbetriebshistorien. Produktive Live-Smokes benötigen eine wirkliche Operatorfreigabe; bei deren Fehlen ist SOURCE_NOT_APPROVED mit dokumentierter Alternative zulässig. Technisch funktionale Collector begründen keine echten Prognosen oder Empfehlungen.

Konkrete Verträge: [Data Operations](docs/architecture/data-operations.md), [Quellenrechte](docs/data/SOURCE_RIGHTS_MATRIX.md), [historische Policy](docs/data/HISTORICAL_DATA_POLICY.md), [PR1-Abnahme](docs/PR1_ACCEPTANCE_REPORT.md). Danach endet dieser Auftrag. PR2 – Real Historical Validation & ML/Recommendation Acceptance erfordert einen eigenen Auftrag und tatsächliche Daten; keine automatische Modell-/Strategie-Promotion oder Produktionsfreigabe.

## PR2-Umsetzungsnachtrag – Historical & Forward Validation (2026-10-19)

Der separat beauftragte PR2-Schritt folgt auf PR1 und erhält die 212 Hauptabschnitte. PR2A prüft Quellenrechte, Originalherkunft, Coverage, PIT, historische Membership/Delistings und quantitative Dataset-Eignung. Ein begrenzter CHF-Pilot verwendet vorhandene PR1-Jobs und 3–5 bestehende Instrumente plus Benchmark. Fehlende Quellenfreigabe oder Originaldaten lassen die technische Infrastruktur fertigstellbar, sperren aber die reale Abnahme.

PR2B registriert Experimentverträge vor unberührtem finalem OOS, verwendet P6-Datasets/Backtests und P7-Training/Registry mit unveränderten Mindestgates. Beide 30-/90-Session-Horizonte, einfache Modelle, Baselines, Kalibrierung, Intervalle, Kosten und belegbare Regime werden getrennt bewertet. Kein quantitatives Gate wird für kleine Datenbestände abgesenkt. Reconstructed- oder synthetischer Erfolg ist kein Produktionsnachweis.

Forward Shadow beginnt ausschließlich mit tatsächlicher Erzeugung, archiviert Prognosen unveränderlich und wartet auf sessiongereifte Outcomes. Retrospektive PIT-Experimente und echte archivierte Forward-Prognosen bleiben unterscheidbar. Automatik benötigt globale und individuelle ausdrückliche Aktivierung; keine autonome Quellenaktivierung. P9 nutzt weiterhin vorhandene historische Replay-, Forecast-, Risiko- und Review-Gates. Keine Modell-/Strategiepromotion und keine Broker-Ausführung durch diesen Auftrag.

Abnahme umfasst bestehende Regression, neue Rechte-/Herkunfts-/OOS-/Forward-/Strategietests, Browseransichten, Alembic ohne Drift und isolierten Restore einschließlich PR2-Evidenz und bisheriger Archive. Numerische Dependency-Locks sowie alte P6-/P7-Hashes bleiben erhalten. Tatsächlicher Fachstatus: PR2A BLOCKED_BY_SOURCE_APPROVAL; PR2B BLOCKED_BY_REAL_DATA; V2 FORECASTS NOT VALIDATED; V3 RECOMMENDATIONS GATED. Die endgültige Homelab-Produktionsabnahme folgt separat.

Nachweise: [PR2A](docs/PR2A_REAL_DATA_ACCEPTANCE_REPORT.md), [PR2B](docs/PR2B_MODEL_VALIDATION_REPORT.md), [Gesamtbericht](docs/PR2_ACCEPTANCE_REPORT.md), [Experimentvertrag](docs/validation/ML_EXPERIMENT_PROTOCOL.md), [Forward-Vertrag](docs/validation/FORWARD_SHADOW_PROTOCOL.md).
