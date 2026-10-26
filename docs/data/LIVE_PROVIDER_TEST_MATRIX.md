# PR6 – Live-Nachweismatrix

Stand und lokale Registryprüfung: 23.10.2026. Keine externen Finanzdatenabfragen ausgeführt. Synthetische TEST-Quellen sind aus dieser Registryauswertung ausgeschlossen.

| Quelle | Reales Gate / aktiv | Produkt-Live-Test | Voraussetzungen und konkreter Prüfumfang |
| --- | --- | --- | --- |
| ECB | UNKNOWN / nein | LIVE_TEST_BLOCKED_BY_SOURCE_APPROVAL | Dokumentierte Rechte für tägliche EXR-Reihen und Archivierung, getrennte Aktivierung; kleines EUR/CHF-/EUR/USD-Fenster, Originalhash, kanonische FX, Wiederholung, Korrekturbeobachtung und UI prüfen. API-Hilfeseite beim Dokumentationsreview HTTP 503. |
| SEC_EDGAR | UNKNOWN / nein | LIVE_TEST_BLOCKED_BY_SOURCE_APPROVAL | Kontakt/User-Agent, erlaubter US-Filer-Scope und Originalaufbewahrung; explizite Instrument/CIK-Zuordnung, Company Facts und Filing samt Verfügbarkeit, Originalreferenz und Versionshistorie. Kein Aktienkursnachweis daraus. |
| OPENFIGI | UNKNOWN / nein | LIVE_TEST_BLOCKED_BY_SOURCE_APPROVAL | Mapping-Scope, Nutzungs-/Speicherentscheidung und Quote; explizites Instrument, ISIN, MIC/Währung; Mehrfachtreffer und unlisted nicht automatisch akzeptieren. Keine Kurse. |
| SNB | UNKNOWN / nein | LIVE_TEST_BLOCKED_BY_SOURCE_APPROVAL | Cube-/Dimensions-/Serienvertrag und Attribution; kleines Monatsfenster, PublishingDate/ETag und bedingte Wiederholung; kein täglicher FX-Ersatz. |
| ALPHAVANTAGE | UNKNOWN / nein | LIVE_TEST_BLOCKED_BY_SOURCE_APPROVAL | Persönlicher Key lokal, instrumentbezogener Scope, kostenloser compact-Endpunkt und passende Langzeitrechte; OHLCV/Währung/MIC-Zuordnung, begrenzter 100-Punkte-Vertrag, erneuter Abruf und Tagesquote. |
| COMPANY_IR / NEWS_RSS | UNKNOWN / nein | LIVE_TEST_BLOCKED_BY_SOURCE_APPROVAL | Je Host/Dokument/Feed ausdrückliche Rechte und Hostvertrag, Robots-/Nutzungsregelprüfung, unveränderliche Archivierung; keine universelle Scraping-Erlaubnis. |
| YAHOO | BLOCKED / nein | LIVE_TEST_BLOCKED_BY_SOURCE_APPROVAL | Ausdrückliche passende Automatikerlaubnis fehlt; kein Bypass und kein yfinance-Abruf. |
| STOOQ | UNKNOWN / nein | LIVE_TEST_BLOCKED_BY_SOURCE_APPROVAL | Automatisierungs-, Archiv- und Analysevertrag ungeklärt. |
| MANUAL_CSV | APPROVED / ja, nur manual_upload | Kein externer HTTP-Test anwendbar | Vorhandene Original-/Preview-/Commit-Verträge lokal mit ausdrücklich synthetischen Daten getestet. Kein Beweis realer Marktversorgung. |

## Einheitliches Abnahmeprotokoll nach einer echten Entscheidung

### Einzelne Nachweisstufen

`PASS` beim Adapter bezeichnet ausschließlich den vorhandenen lokalen Vertragstest. Die folgenden Live-Spalten beziehen sich auf echte Finanzoriginale dieses PR6-Auftrags. `BLOCKED` bedeutet fehlende Rechte-/Operatorvoraussetzung, `NOT_TESTED` eine nicht durchgeführte oder hier nicht anwendbare Prüfung. Eine geprüfte Dokumentationsseite ist keine erteilte Nutzungserlaubnis.

| Quelle | Adapter | Rechteentscheidung | Operator | Echtabruf | Raw | Parsing echt | Canonical echt | Wiederholung echt | Qualität echt | UI echt | Scheduler echt |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ECB | PASS | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED |
| SEC_EDGAR | PASS | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED |
| OPENFIGI | PASS | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED |
| SNB | PASS | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED |
| ALPHAVANTAGE | PASS | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED |
| COMPANY_IR | PASS | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED |
| NEWS_RSS | PASS | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED |
| YAHOO | NOT_TESTED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED |
| STOOQ | NOT_TESTED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED |
| FRED / Twelve Data | NOT_TESTED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED |
| MANUAL_CSV | PASS | PASS (manual_upload) | PASS (bestehendes Gate) | NOT_TESTED | NOT_TESTED | NOT_TESTED | NOT_TESTED | NOT_TESTED | NOT_TESTED | NOT_TESTED | NOT_TESTED |

MANUAL_CSV ist mit synthetischen Originaldateien einschließlich Raw/Parsing/Canonical/Wiederholung/Qualität/UI lokal geprüft, aber ohne echten Brokerexport hier kein `PASS` für reale Finanzdaten. Manuelle Übernahme besitzt keinen externen Scheduler. Mapping, Monatsreferenzen, Dokumente und Nachrichten begründen keine vollständige tägliche Kursversorgung.

1. Aktuellen Registryeintrag, konkrete Nutzungsbelege, Scope, Verwendung, Ablaufdatum und Operatorentscheidung archivieren. Die API `POST /api/v1/data-operations/preview` prüft den begrenzten Auftrag, `POST /api/v1/data-operations/jobs` startet ihn erst unter den vorhandenen Gates. Es gibt keine parallele Abrufimplementierung.
2. Einen Auftrag mit kleiner Datumsgrenze und expliziten internen Instrument-IDs ausführen. Für OpenFIGI/SEC/Alpha ist genau ein geprüftes Instrument erforderlich; SEC verlangt zusätzlich CIK. Antwortbytes/SHA, HTTP-Status, Abruf-/Quellenzeit und Parservertrag aus dem Raw-Nachweis prüfen. Keine Schlüssel oder vollständigen Anfrageheader in Berichte übernehmen.
3. Jobabschluss, Mappingentscheidungen, Quarantäne, kanonische Werte und jeweilige UI überprüfen. Quelle und Währung müssen dem ausgewählten Instrument entsprechen.
4. Denselben Auftrag wiederholen und idempotente Wirkung, neue Beobachtung gegenüber echter Datenkorrektur und Checkpoint prüfen. Ein mehrfach beobachteter identischer Wert ist keine neue Preisversion.
5. 429/Retry-After, Timeout, 5xx und geänderte Rechte mit isoliertem Transport bzw. Fixture prüfen; keine absichtliche Überlastung eines echten Dienstes. Eine gesperrte Quelle darf auch beim Retry keine Anfrage erhalten.
6. Eine spätere zulässige Aktualisierung separat protokollieren. Erst dann erfolgreiche Wiederaufnahme und inkrementelle Versorgung behaupten. Recurring Collection bleibt ohne gesondertes Opt-in aus.

Alle Live-Spalten bleiben blockiert, bis diese Nachweise tatsächlich vorliegen. Ein erreichbares Dokumentationsportal erfüllt diesen Test nicht. Der Nutzer wünscht allgemeine ISIN-Unterstützung; konkrete Depotabdeckung und neue Quellenrechte werden dadurch nicht angenommen.
