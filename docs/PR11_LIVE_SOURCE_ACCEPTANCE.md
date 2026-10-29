# PR11D – Erste reale Quellenabnahme

Prüfdatum **29.10.2026**. **LIVE_SOURCE_BLOCKED_BY_APPROVAL**.
ECB und OpenFIGI sind nach der letzten belegten
[PR10-Registryprüfung](security/pr10-20261029/source-registry-post-regression.json)
`UNKNOWN` und deaktiviert. Das ist ein datierter PR10-Beleg, keine vorgetäuschte
neue PR11-Registrylesung. Seitdem wurde im Auftrag keine echte Quellen- oder
Betriebsfreigabe mitgeteilt. Dieser Arbeitsschritt hat keine Quelle verändert
und keinen externen Finanzendpunkt aufgerufen.

## 1. Primärdokumentation erneut geprüft

Die [ECB-Copyrightseite](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html)
gestattet direkte Informationsnutzung mit zutreffender Wiedergabe,
Quellenangabe und Kennzeichnung eigener Änderungen; Autorenwerke haben
Ausnahmen. Der Operator muss den konkreten EXR-Abruf, unveränderte Speicherung,
Aufbewahrung und interne Ableitung im Registryentscheid erfassen. Diese
Dokumentationsprüfung selbst ist keine erfasste Freigabe.

Die [ECB-Referenzkursseite](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html)
nennt EUR als Basis und normalerweise Veröffentlichung um 16:00 CET an
Arbeitstagen außer TARGET-Schließtagen. Die Informationskurse sind nicht als
Transaktionskurse gedacht. Geplante Veröffentlichung beweist weder Abruf noch
tatsächliche lokale Kenntniszeit. Angezeigte Werte wurden nicht übernommen.

[API-Überblick](https://data.ecb.europa.eu/help/api/overview) lieferte beim
PR11-Recherchezugriff HTTP 503;
[API-Daten](https://data.ecb.europa.eu/help/api/data) lieferten einen
Fetch-Timeout. Deshalb wird keine neue bestätigte numerische ECB-Quote oder
zusätzliche API-Zusage behauptet. Der Operator prüft diese konkreten Regeln
vor dem ersten tatsächlichen Request erneut. Ein lokales Limit von einer
Anfrage pro Minute ist eine konservative Konfiguration, kein Anbieterzitat.

Für OpenFIGI wurden [API-Dokumentation](https://www.openfigi.com/api/documentation),
[Terms](https://www.openfigi.com/docs/terms-of-service) und
[FAQ](https://www.openfigi.com/about/faq) erneut gelesen. Mapping erlaubt
25 Requests/min und 10 Jobs/Request ohne Key, 250 und 100 mit Key;
Search/Filter hat eigene Limits. Bei 429 ist `retry-after` zu beachten.
FIGI-Identifier sind frei nutzbar; die FAQ beschreibt offene zugehörige
Metadaten. Eingabekennungen, konkrete Antwortarchivierung und Zweck bleiben
explizit zu reviewen. Die API garantiert keine vollständige Listinghistorie
und liefert keine Kurse. Die Terms tragen weiter das Änderungsdatum 27.11.2018.

## 2. Vorhandenen Codepfad geprüft

Die neue tatsächliche [read-only Registryprüfung nach der Regression](security/pr11-20261029/source-registry-readonly.json)
bestätigt weiterhin ECB/OpenFIGI UNKNOWN und deaktiviert, ohne gültige
Reviewentscheidung. Testmodus, Collection, Forward-Scheduling und temporäre
Operatorrollen sind aus; der Prüflauf hat keine Finanzprovideranfrage und
keine Registryänderung ausgeführt. Der Livezustand bleibt
`LIVE_SOURCE_BLOCKED_BY_APPROVAL`.

Read-only geprüft: [`EcbFxCollector`](../backend/app/providers/ecb_fx.py),
[`BackfillJobService`](../backend/app/services/backfill_jobs.py),
[`fetch_response`](../backend/app/providers/http.py),
[`SourceService`](../backend/app/services/sources.py),
[`provider_canonical`](../backend/app/services/provider_canonical.py),
[`MarketQueryService.fx`](../backend/app/services/market_queries.py) und
[`holdings_refresh.py`](../ops/holdings_refresh.py). Es wird kein neuer
Collector oder paralleler Freigabepfad eingeführt.

| Vertrag | Tatsächliches Verhalten / Grenze |
| --- | --- |
| Reihen | Request `/service/data/EXR/D.CHF+USD.EUR.SP00.A` enthält immer CHF je EUR **und** USD je EUR; `series=EUR_CHF` beschränkt ihn nicht auf einen Input |
| Rechte | `APPROVED`, getrennt `enabled`, gültiger Review, `fx_rates`, `raw_archive`, `derived_analysis`; genau ein `fx_inputs=EXR.D.CHF.EUR.SP00.A,EXR.D.USD.EUR.SP00.A` und ein vollständig deckendes `fx_coverage=YYYY-MM-DD\|YYYY-MM-DD` |
| Prüfstellen | Gesamter Backfill-Preview vor Queue; Collector vor Sync/Client; aktualisierter Review und Scope bei jedem HTTP-Versuch; geänderter Review beendet den alten Versuch |
| Aktivierung | Ein neuer append-only Review deaktiviert die Quelle; `enable` ist ein eigener authentifizierter Operatoraufruf |
| Request | Offizieller HTTPS-Host, begrenzter öffentlicher DNS-Pfad, keine Redirects/Proxyübernahme; höchstens 32 Tage je Chunk, keine Zukunft |
| Original | Exakte begrenzte Antwortbytes und SHA-256 vor Parsing, anschließend verifiziertes Rücklesen; Schemafehler löschen Originale nicht |
| Kanonik | Nur tägliche EUR/SP00/A-Reihen, positive endliche Decimalwerte, eindeutige Tag/Währungs-Paare im Requestfenster; Konflikte bleiben reviewpflichtig |
| Wiederholung | Request-/Parserbindung und Synczustand; gleiche Bytes oder 304 erzeugen keine neuen kanonischen Beobachtungszeiten; neue Raw-Evidenz bleibt nachvollziehbar |
| Lücken | Leere oder nur teilweise Antworten können technisch erfolgreich sein; `SUCCESS` ist kein Coveragebeweis; 304 ohne verifizierten Cache wird verworfen |
| Zeit | Aktuell bezogener Stand mit `includeHistory=false`; historische lokale Verfügbarkeit wird nicht rückdatiert |

Der [PR10-Scopefix](data/pr10-ecb-scope-regression.json) und seine
321er-Produktionsimageregression bleiben datierte technische Nachweise.
Tatsächliche PR11-Regressionsläufe stehen separat im
[Gesamtbericht](PR11_ACCEPTANCE_REPORT.md).

## 3. Konkrete Betreiberentscheidung vor Livezugriff

Den vorbereiteten [PR11-Operatorbogen](data/PR11_SOURCE_OPERATOR_REVIEW.md)
privat vervollständigen. Bestehende Schritte verwenden: **Einstellungen →
Datenquellen** für Review und separate Aktivierung, **Datenbetrieb** für
Preview und einen einzelnen bestehenden Job.

| Entscheidung | Handlung | Wer autorisiert? | Geschützte Eingaben | Erfolg | Bis dahin gesperrt |
| --- | --- | --- | --- | --- | --- |
| ECB-Nutzung | Beide Serien, Zeitraum, Abruf/Archiv/Analyse, Attribution, Quote und nächstes Review konkret entscheiden | Tatsächlicher autorisierter Datenoperator | Rechtebeleg/Hash, Nutzerzweck, reale Datumswerte, Reviewer; keine Zugangsdaten im Scope | Append-only Review mit tatsächlicher UTC-Zeit und gültigen Pflichtfeldern | Jeder ECB-Finanzrequest |
| ECB-Betrieb | Privates Ziel, Security, TLS/Egress, Original-/Backupschutz abnehmen; separat aktivieren | Zielbetreiber und Datenoperator | Ziel-/Securitybelege, geschützte Prozesskonfiguration | Aktivierungsbeleg und weiterhin gültiger, exakt passender Review | Erstabruf und geplanter Betrieb |
| Fachliche Liveabnahme | Erstabruf, identische Wiederholung und späteren Veröffentlichungstag tatsächlich vergleichen | Verantwortlicher Datenoperator / fachlicher Prüfer | Private Job-/Raw-/Canonical-/Bewertungsreceipts | Die nachstehende vollständige Evidenz ist vorhanden | `LIVE_SOURCE_VERIFIED` |
| Wiederkehrende Versorgung | Vorhandenen Scheduler ausdrücklich freigeben, Quote und Fehlermonitoring prüfen | Betriebs- und Datenoperator | Tatsächlicher Zeitplan, globale/individuelle Opt-ins, Alarmbelege | Zeitgesteuerter echter späterer Abruf und aktuelle geprüfte Daten | `AUTOMATIC_REFRESH_VERIFIED` |

Weder Dokumentation noch diese Tabelle erteilen eine Zustimmung. Rechtmäßige
manuelle Imports bleiben ein zulässiger Core-V1-Datenweg.

## 4. Echte ECB-Ereignisse und Kreuzrechnung

1. Kurzes abgeschlossenes Veröffentlichungsintervall innerhalb des **gesamten**
   freigegebenen Fensters vorschauen und genau einen Job starten. Tatsächliche
   Quote und gültige Rechte vorher lesen; kein Downloadclient als Umgehung.
2. Job-ID, Beginn/Ende UTC, Antwortstatus, Parser, Raw-ID, Originalbytes und
   SHA-256 privat sichern. Beide realen Serien und tatsächlichen Referenztage
   gegen kanonische Leg-IDs prüfen; Konflikte/Quarantäne zuerst auflösen.
3. Für EUR/CHF, EUR/USD und USD/CHF den vorhandenen FX-Leseweg mit explizitem
   Bewertungsdatum prüfen. Die Decimal-Ableitung lautet:

   ```text
   CHF je USD = (CHF je EUR) / (USD je EUR)
   ```

   Beide gespeicherten Legs müssen **denselben tatsächlichen Referenztag**,
   den freigegebenen ECB-Source-Eintrag und verifizierte Originale haben.
   `source_ids`, `legs`, `derived`, `rate_date`, `carry_days`, `known_at` und
   `retrieved_at` vergleichen. Der allgemeine Querypfad kann direkte manuelle
   Kurse, andere akzeptierte Quellen oder verschieden alte Legs auswählen;
   `AVAILABLE` allein belegt keinen aktuellen ECB-Kreuzkurs.
4. Identisches Fenster nach Abschluss erneut abrufen. Neue Raw-/No-New-Data-
   Evidenz und unveränderte Canonicalzahl/ursprüngliche Kenntniszeiten prüfen.
   Ein noch laufender Job kann dieselbe Job-ID liefern; das ist kein zweiter
   Request. 304 beweist keine spätere Veröffentlichung.
5. An einem **tatsächlich späteren Veröffentlichungstag** neue echte
   Referenzdaten, Raw-/Canonical-IDs, Abrufzeit und UI-Freshness abnehmen.
   Sofortige Wiederholung und neue lokale Testwerte erfüllen diesen Schritt
   nicht. Der Holdings-Planer fragt bis gestern an und beweist keinen heutigen
   Veröffentlichungstag.
6. Erst mit getrenntem Zeitplanentscheid den vorhandenen wiederkehrenden
   Betrieb nutzen. Erster Echtabruf und manuell späterer Echtabruf allein
   beweisen keine automatische Ausführung. Timeout/429/Schemafehler/Widerruf
   ausschließlich mit Offline-Fixtures testen.

## 5. OpenFIGI und Aktien-/ETF-Abdeckung

OpenFIGI separat für konkretes Mapping einschließlich Originalarchiv und
Identitätsnutzung reviewen und aktivieren. Zusätzliche Analyse ist eigens zu
entscheiden, wenn sie tatsächlich vorgesehen ist. Ein vorhandener `OPENFIGI`-Job verwendet genau
ein geprüftes Instrument und dessen ISIN/FIGI, MIC und Währung. MIC und
`exchCode` sind alternative Filter; der normale Instrument-Mappingpfad und
der Datenbetriebsjob senden nicht zwangsläufig dieselben Filter.

**Begrenzung der maschinellen Rechteprüfung:**
[`OpenFigiProvider.map_identifier` und `MappingService.accept`](../backend/app/providers/openfigi.py)
verlangen den gültigen aktivierten Source-Review mit `mapping`. Sie verlangen
keine separaten `raw_archive`-/`derived_analysis`-Tokens und prüfen den freien
Scope-/Entscheidtext nicht semantisch. Der
[`SourceService.review`](../backend/app/services/sources.py) kann den konkreten
fachlichen Mappingumfang einschließlich exakter Speicherung, Aufbewahrung
und Identitätsnutzung im Scope und im append-only Entscheid festhalten. Er
belegt allein durch vorhandene Pflichtfelder nicht die tatsächlichen Rechte.
Ein echtes Mappingapproval muss diese unvermeidliche Originalarchivierung
ausdrücklich umfassen; fehlt dieser Nachweis oder schließt der Scope sie aus,
bleibt die Quelle deaktiviert. `mapping` allein ist kein Nachweis separat
geprüfter Speicher- oder zusätzlicher Analyserechte. Es wird keine technische
Gleichheit mit dem strengeren ECB-Vertrag behauptet. Ein genehmigungsumgehender
Echtablauf wurde nicht ausgeführt oder als neuer reproduzierter Defekt
behauptet; daraus entsteht keine ungeprüfte Backendänderung.

Raw-Original und alle Kandidaten prüfen; fehlende MIC-/Währungs-/Zeitangaben
mit eigenem berechtigten Listingbeleg klären. Auch `UNIQUE_CANDIDATE` erfordert
ausdrückliche Auswahl gegen die gespeicherte Antwort. `exchCode` ist kein
automatisch bewiesener ISO-MIC. Mehrdeutige Treffer bleiben ungeklärt.

Allgemeine ISIN-Unterstützung ist gewünscht; konkrete Holdings werden nicht
vorausgesetzt oder erneut angefragt. Für jeden später tatsächlich benötigten
Kurs sind Listing/MIC, Handelswährung, Typ, Provider-/Exportsymbol, Intervall,
Abruf-/Archiv-/Analyserechte und Actionscoverage getrennt nachzuweisen.
Yahoo bleibt Priorität unter Freigabevorbehalt; Erreichbarkeit oder eine
Bibliothek ersetzen keinen Rechteentscheid. Keine universelle kostenlose
Aktien-/ETF-Abdeckung wird behauptet.

**`LIVE_SOURCE_VERIFIED=false`, `AUTOMATIC_REFRESH_VERIFIED=false`.** Die
ausstehenden echten Entscheidungen und Ereignisse werden durch keine weitere
synthetische Datensammlung ersetzt.
