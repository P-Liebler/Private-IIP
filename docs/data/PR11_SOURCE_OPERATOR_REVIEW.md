# PR11 – Privater Quellenentscheid und tatsächliche Ereignisbelege

Vorbereitet am **29.10.2026**. **DRAFT / NOT_APPROVED**.
Dieser Bogen erteilt keine Nutzungs-, Betriebs- oder Quellenfreigabe. Die
Pflichtfelder und APIs sind bereits vorhanden; Primärprüfung und Grenzen
stehen in der [PR11-Quellenabnahme](../PR11_LIVE_SOURCE_ACCEPTANCE.md).
Tatsächliche Namen, Belege, Zeitpunkte und Receipts privat dokumentieren.

## 1. Vor ECB-Aktivierung auszufüllender Entscheid

| Feld | Konkreter erforderlicher Inhalt |
| --- | --- |
| Verantwortlicher | Tatsächlicher autorisierter Datenoperator und berechtigter privater Nutzerzweck |
| Quelle | Existierende Registry-ID und Slug `ECB` |
| Rechtebeleg | Aktuelle Primär-URL, tatsächlicher Prüfzeitpunkt, Fundstelle und privat erhaltener Beleg/Hash |
| Automatisierter Request | `https://data-api.ecb.europa.eu/service/data/EXR/D.CHF+USD.EUR.SP00.A` mit begrenztem Datumsfenster |
| Exakte Serien | Beide `EXR.D.CHF.EUR.SP00.A` und `EXR.D.USD.EUR.SP00.A` |
| Datumsscope | Tatsächlich erlaubtes ganzes Fenster; kleine spätere Requests müssen darin liegen |
| Nutzungen | `fx_rates`, `raw_archive`, `derived_analysis` jeweils tatsächlich geprüft; keine automatische ML-Freigabe |
| Aufbewahrung | Exakte Originalbytes vor Parsing und dauerhafte unveränderliche Speicherung, einschließlich zulässiger Aufbewahrung nach Nutzungsende |
| Attribution | ECB als Quelle nennen, eigenen USD/CHF-Kreuzkurs kennzeichnen; Referenzkurs von Broker-FX unterscheiden |
| Grenzen | Tatsächlich zulässige Anbieterquote und konservatives lokales Limit, Tages-/Parallelgrenzen |
| Entscheidung | Tatsächliches APPROVED/BLOCKED/UNKNOWN und begründeter Hinweis; kein Ersatzreviewer |
| Nächste Prüfung | Tatsächlicher zukünftiger UTC-Zeitpunkt; Änderung/Widerruf löst neue Entscheidung aus |
| Betriebsbeleg | Privates Ziel, Security, TLS/Egress, Originalschutz und unabhängige Recovery tatsächlich freigegeben |

Den vorhandenen `POST /api/v1/data-operations/sources/ECB/review` beziehungsweise
**Einstellungen → Datenquellen** verwenden. API-Pflichtfelder sind `status`,
`terms_url`, `scope`, `allowed_uses`, `decision_note`, `next_review_at` und
`rate_limit_per_minute`; der angemeldete Operator liefert die tatsächliche
Revieweridentität. Maximal 2.000 Scopezeichen.

Der Scope muss genau einmal diese bestehenden maschinenlesbaren Tokens
enthalten, mit **wirklich entschiedenen** Datumswerten anstelle der Platzhalter:

```text
fx_inputs=EXR.D.CHF.EUR.SP00.A,EXR.D.USD.EUR.SP00.A
fx_coverage=YYYY-MM-DD|YYYY-MM-DD
```

Der Textblock ist kein ausführbarer positiver Review. Der vorhandene
[PR10-UNKNOWN-Body](PR10_SOURCE_OPERATOR_REVIEW.md) zeigt die Feldform ohne
Freigabe. Ein neuer Review deaktiviert die Quelle. Erst nach echtem Review
separat `POST /api/v1/data-operations/sources/ECB/enable` ausführen. Review-ID,
UTC-Zeit und Aktivierungsbeleg privat sichern. Globale wiederkehrende Sammlung
bleibt zunächst aus.

## 2. Kleine echte ECB-Jobs nach separater Freigabe

Vorhandenen `POST /api/v1/data-operations/preview` und anschließend
`POST /api/v1/data-operations/jobs` mit Quelle `ECB`, Kind `ECB_FX` und echten
`start`-/`end`-Datumswerten verwenden. Ein einzelner Chunk umfasst höchstens
32 Tage; für die Erstabnahme ein kurzes abgeschlossenes Intervall wählen.
`series=EUR_CHF` ist kein Einserienscope: beide EUR-Eingangsreihen werden
abgerufen. Die vollständige Anfragespanne muss innerhalb des Reviews liegen.

| Tatsächlicher Beleg | Erstabruf | Identische Wiederholung | Späterer Veröffentlichungstag |
| --- | --- | --- | --- |
| Noch gültiger Review / Aktivierung / Betriebsfreigabe | offen | offen | offen |
| Exakte Requestparameter / Serien / Datumsscope | offen | identisch nach Abschluss | neues erlaubtes Fenster |
| Job-ID, Beginn/Ende UTC, Status/Retry/Restquote | offen | offen | offen |
| Raw-ID, HTTP-Status, Original-SHA-256, verifizierte Bytes | offen | neue Raw-/No-New-Data-Evidenz | neues tatsächliches Original |
| Beide tatsächlichen Referenztage und Canonical-/Leg-IDs | offen | keine Duplikate | neuer veröffentlichter Tag |
| Source-IDs, known_at / retrieved_at / Revisionsbezug | offen | ursprüngliche Kenntniszeit erhalten | neue tatsächliche Kenntniszeit |
| Quarantäne, Qualität und Konfliktentscheid | offen | offen | offen |
| Decimal CHF-je-USD = CHF-je-EUR / USD-je-EUR | offen | konkrete Legs vergleichen | beide Legs desselben neuen Tages |
| FX-/Bewertungsantwort: derived, carry_days, source_ids, UI-Frische | offen | Vergleich dokumentieren | neue Frische wirklich nachgewiesen |
| Prüfer, tatsächlicher Entscheid und Receiptbezüge | offen | offen | offen |

Ein leerer Erfolg oder 304 schließt die erste fachliche Abnahme nicht.
`JOBS_SUCCESS_NOT_LIVE_VALIDATED` aus dem Holdings-Helper ist kein Live-Gate.
Zwei echte Veröffentlichungstage sind für Kontinuität erforderlich; automatische
Versorgung verlangt zusätzlich einen ausdrücklich freigegebenen Zeitplan und
seine tatsächliche Ausführung. Keine Änderungen an alten Beobachtungszeiten.

## 3. OpenFIGI separat entscheiden

| Feld | Konkreter Nachweis |
| --- | --- |
| Rechte / Zweck | `mapping` mit ausdrücklicher Erlaubnis der exakten Raw-/Metadatenaufbewahrung und Identitätsnutzung; zusätzliche Analyse nur nach eigener tatsächlich benötigter Freigabe; Rechte an Eingabekennungen separat prüfen |
| Request | `https://api.openfigi.com/v3/mapping`, tatsächliche ISIN/FIGI und geprüfte Filter; kein Kursabruf |
| Quote | Passendes dokumentiertes Key-/No-Key-Limit; API-Key nur im geschützten Secret |
| Review / Aktivierung | Tatsächlicher Operator, Terms/Fundstelle, Datumsscope/Zweck, nächstes Review; separate Aktivierung |
| Identität | Konkrete interne Instrument-ID, Listing/MIC/Währung/Typ/Zeitbeleg; nicht aus Ticker oder exchCode vermuten |
| Ergebnis | Gespeicherte Originalantwort, Raw-ID/Hash, alle Kandidaten/No-Match und ausdrückliche Auswahl einer darin enthaltenen FIGI |

Der bestehende `OPENFIGI`-Job verlangt genau eine tatsächliche Instrument-UUID.
Mehrdeutigkeit bleibt offen; auch ein Einzelkandidat wird nicht automatisch
akzeptiert. FIGI-Bestätigung beweist weder Kursversorgung noch Actionscoverage.
Die technische OpenFIGI-Prüfung verlangt nur `mapping`, keine separaten
Archiv-/Analysetokens. Der freie Reviewscope muss daher den tatsächlichen
Speicher- und Nutzungsumfang ausdrücklich belegen; Pflichtfelder allein
beweisen diese Rechte nicht. Ohne passenden echten Entscheid deaktiviert lassen.

## 4. Spätere tatsächliche Aktien-/ETF-Listings

Je tatsächlichem Listing privat ergänzen: stabile interne ID, ISIN, MIC,
Handelswährung, Typ und Gültigkeit; tatsächlicher Provider-/Exportweg und
Symbol; nutzbarer Zeitraum/Frequenz und unadjustierte Preise; Abruf, exaktes
Archiv, dauerhafte Aufbewahrung, Analyse und ML getrennt; Dividenden-/Split-
Coverage; Raw-/Canonical-IDs und Frische; wirklicher Operatorentscheid und
nächstes Review. Keine universelle ISIN-Kursabdeckung wird vorausgesetzt.

Bis zu diesen Entscheidungen bleibt automatischer Abruf gesperrt. Ein
rechtmäßiger manueller Import nutzt die bestehenden Original-/Preview-/
Kanonikverträge. Fehlende Rechte oder Daten werden nicht mit erfundenen Werten
oder einem anderen ungeprüften Anbieter ersetzt.
