# PR9C – Reale Datenversorgung und Holdings-Aktualisierung

Prüfdatum **28.10.2026**. Status: **BLOCKED_BY_SOURCE_APPROVAL / LIVE_NOT_EXECUTED**. Die Dokumentationsprüfung erteilt keine Nutzungsrechte. Es wurden keine Finanz-API-Abfragen ausgelöst, keine Quelle aktiviert und keine Livewerte als Portfolioevidenz erfasst. Öffentlich sichtbare Beispiele auf Dokumentationsseiten sind keine importierten Beobachtungen. Die [PR8-Nachweise](PR8C_DATA_PROVIDER_REPORT.md) bleiben unverändert.

## Ergebnis und Grenzen

- ECB ist der zuerst abnehmbare vorhandene FX-Pfad. Der dokumentierte Nutzungsrahmen ist grundsätzlich brauchbar; der echte, versionierte Operatorentscheid und der freigegebene Netzwerkpfad fehlen weiterhin.
- OpenFIGI kann nach Freigabe ISIN-Kandidaten liefern. Es liefert keine Preise und garantiert in der Mappingantwort weder MIC, Handelswährung noch einen historischen Listingstatus.
- Allgemeine kostenlose, rechtlich geprüfte Kursversorgung für beliebige Schweizer/US-/europäische Aktien und ETFs ist **nicht nachgewiesen**. Allgemeine ISIN-Erfassung bleibt möglich; Preis-, Börsen-, Währungs- und Actioncoverage sind je Listing gesondert zu belegen.
- Der bisher fest auf Alpha Vantage gerichtete Refresh wurde korrigiert: Nur exakt abgedeckte und aktuell freigegebene Listings erhalten einen Job. Fehlende Rechte oder Abdeckung erzeugen eine ausdrückliche Enthaltung mit manuellem Importweg.
- Keine neue Datenpipeline, kein neues Schema, kein neuer Provider und kein automatischer Zeitplan. Backend-Source-Gates, bestehende Collector und Checkpoints bleiben maßgeblich.

## ECB: konkreter Daten- und Rechtevertrag

Die [Referenzkursbeschreibung](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html) nennt gewöhnlich etwa 16:00 CET an Arbeitstagen, ausgenommen TARGET-Schließtage. Der [Framework-Stand 23.06.2026](https://www.ecb.europa.eu/stats/pdf/exchange/Frameworkfortheeuroforeignexchangereferencerates.en.pdf) trennt die Ermittlung gegen 14:10 CET von der Veröffentlichung. Die [Feiertagsliste](https://www.ecb.europa.eu/ecb/contacts/working-hours/html/index.en.html) markiert TARGET-Schließtage; ein allgemeiner ECB-Bürofeiertag ist nicht automatisch ein TARGET-Schließtag. Ein geplanter Abruf muss verspätete Veröffentlichung, Sommerzeit und Nichtveröffentlichung berücksichtigen. Aus einem erwarteten Zeitpunkt wird kein tatsächlich beobachtetes `known_at` abgeleitet.

Die [Copyrightbedingungen](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html) erlauben die freie Nutzung direkt bezogener Information unter Quellenangabe, korrekter Wiedergabe und Kennzeichnung eigener Änderungen; Autorenwerke haben besondere Rechte. Daraus folgt ein geeigneter **Prüfkandidat** für privates Originalarchiv und abgeleitete Analysen, keine bereits erteilte Registryfreigabe. Im Review festhalten: statistische EXR-Daten, automatischer begrenzter Abruf, unveränderte Originalbytes, dauerhafte Archivierung, interne Analyse, Attribution und die ausgeschlossenen Drittinhalte. Referenzkurse sind Informationskurse; die ECB rät von ihrer Nutzung als Transaktionskurs ab. Tatsächliche Broker-FX, Gebühren und Wechselbuchungen bleiben Ledgerdaten. ML-Training ist separat zu prüfen und wird durch diesen Portfolio-Refresh nicht freigegeben.

Der vorhandene `EcbFxCollector` fordert **beide** täglichen Reihen `EXR.D.CHF.EUR.SP00.A` und `EXR.D.USD.EUR.SP00.A` gemeinsam an. Sie bedeuten CHF beziehungsweise USD **je EUR**. Daher:

| Benötigter Kurs | Ableitung | Erforderlicher Nachweis |
| --- | --- | --- |
| EUR/CHF | CHF je EUR direkt | Kanonische CHF-Reihe mit Original-ID, Datum und lokalem Kenntniszeitpunkt |
| EUR/USD | USD je EUR direkt | Kanonische USD-Reihe mit denselben Herkunftsfeldern |
| USD/CHF | `(CHF je EUR) / (USD je EUR)` mit Decimal | Beide konkreten Legs, deren Daten, Versionen und Kenntniszeitpunkte; kein Kehrwertfehler |

`MarketQueryService.fx` gibt die Leg-IDs, Original-IDs, Daten, `known_at`, `retrieved_at`, Ableitung und Carry-Dauer aus. Ein Kreuzkurs ist kein separat beobachteter Brokerkurs. Bei der Liveabnahme müssen beide Legs zum gleichen tatsächlichen Referenztag passen. Abweichende oder fehlende Legs und übertragene ältere Kurse sind ausdrücklich zu prüfen; `AVAILABLE` allein beweist keine aktuelle Tagesabdeckung. Fehlende Daten werden nicht durch Null ersetzt.

Exakte Antwortbytes werden vor dem Parsen archiviert. `includeHistory=false` lädt den aktuell veröffentlichten Stand; es beweist **keine vollständige historische Revisionshistorie**. Wiederholungen desselben Fensters verwenden vorhandene ETag-/Last-Modified- und Content-Hash-Checkpoints. Später entdeckte Korrekturen behalten neue Raw- und Versionsnachweise; Konflikte bleiben gegebenenfalls in Quarantäne. Der Rückblick darf keine damalige lokale Beobachtung erfinden. Der Refresh prüft ein überlappendes Fenster von 32 Kalendertagen; ältere Korrekturen brauchen einen gezielten vorhandenen Backfill. Die [API-Hilfeseite](https://data.ecb.europa.eu/help/api/overview) war am Prüftag über das Recherchewerkzeug nicht abrufbar; deshalb ist keine neue numerische ECB-Quote behauptet.

## OpenFIGI: was eine ISIN-Abfrage tatsächlich belegt

Die [API-Dokumentation](https://www.openfigi.com/api/documentation) erlaubt Mapping ohne Key mit 25 Requests/min und 10 Jobs/Request, mit Key 250/min und 100 Jobs/Request. Search/Filter besitzen eigene Limits. Bei HTTP 429 gilt `Retry-After`; der vorhandene lokale Adapter bleibt konservativer begrenzt. Nach [FAQ](https://www.openfigi.com/about/faq) sind FIGI-Symbologie und zugehörige Metadaten offen nutzbar; Rechte fremder Eingabekennungen bleiben gesondert zu betrachten.

| Anzeige / Identität | Belastbare Aussage |
| --- | --- |
| Name, FIGI, Ticker, `exchCode`, Typ/Sektor | Können von der Mappingantwort geliefert werden; null bleibt fehlend. `exchCode` ist nicht automatisch ein ISO-MIC. |
| MIC und Handelswährung | Als Requestfilter möglich; die normalen Responsefelder garantieren ihre Rückgabe nicht. Vorhandene Instrumentmetadaten und unabhängige Listingbelege müssen passen. Nicht aus Ticker oder ISIN erraten. |
| Listed/delisted | Unlisted Equities sind standardmäßig ausgeschlossen; `includeUnlistedEquities=true` erweitert die Suche. Das ist kein vollständiges historisches Listingregister und kein einzelnes garantiertes Statusfeld. |
| Eindeutiger Kandidat | Bleibt ein prüfpflichtiger Kandidat. Die bestehende Mapping-Accept-Aktion braucht eine ausdrückliche Auswahl des FIGI und das zugehörige Original. Mehrdeutigkeit darf nicht automatisch akzeptiert werden. |

Vorhandener Weg: **Instrument anlegen → Kennung/ISIN prüfen → Mapping anfordern → Original und Kandidaten vergleichen → konkrete Auswahl bestätigen**. Für MIC-/Währungsfilter und Einbezug unlisted Equities steht der bestehende `OPENFIGI`-Datenbetriebsauftrag zur Verfügung. Ein bestätigter FIGI erteilt keine Kursrechte und keine Preisabdeckung.

## Kostenlose Kurskandidaten – getrennte Rechte und Abdeckung

Alle Angaben sind Dokumentationsprüfungen vom **28.10.2026**, keine positive Liveabnahme. Keine Quelle wurde während PR9C aktiviert.

| Kandidat | Abruf, Limits und Marktabdeckung | Originalarchiv, Analyse/ML und Aktualität/Actions | Entscheidung für den vorhandenen Core |
| --- | --- | --- | --- |
| **Alpha Vantage** | [Support](https://www.alphavantage.co/support/): normalerweise 25 kostenlose Requests/Tag. [Dokumentation](https://www.alphavantage.co/documentation/): Daily Compact mit letzten 100 Datenpunkten, Full premium; Symbolbeispiele und ETF-Produktangebot belegen keine flächendeckende CH-/EU-Abdeckung. | [Bedingungen](https://www.alphavantage.co/terms_of_service/) beschreiben persönliche nichtkommerzielle Analyse/Forschung, mit Nutzerqualifikation und EULA. Dauerhafte unveränderliche Raw-Aufbewahrung einschließlich Vertragsende und konkrete ML-Nutzung sind nicht als pauschale Freigabe belegt. Realtime/15-Minuten-Daten sind separat lizenziert. Angepasste Reihen berücksichtigen Splits/Dividenden; der bestehende Adapter verwendet ausschließlich rohe Daily-Daten. Keine Actions- oder Total-Return-Freigabe daraus ableiten. | Vorhandener Adapter technisch nutzbar, **nur je bestätigt lizenziertem Symbol/MIC/Währung/Zeitraum**. Key optional für die Plattform, erforderlich für diesen Provider. Keine unbeschränkte Gratis-Historie. |
| **Twelve Data Basic** | [Preisliste](https://twelvedata.com/pricing): 8 API-Credits/min und 800/Tag, US-Aktien/ETFs, FX; globale EOD-Aktien/ETFs im bezahlten Grow-Angebot. Listingwährung, Börse und Rechte können planabhängig sein. | [Bedingungen §§2/3/12/16](https://twelvedata.com/terms): Display/Non-Display und Drittbörsenrechte getrennt; Speicherung nur im erlaubten Zeitraum, Löschung nach Vertragsende grundsätzlich innerhalb 30 Tagen. **Das passt ohne schriftliche Sonderregel nicht zum unveränderlichen Langzeitarchiv.** Keine allgemeine ML- oder Actions-Freigabe und keine kostenlose CH-/EU-Gesamtabdeckung belegt. | **NOT_APPROVED_FOR_IMMUTABLE_ARCHIVE**. Kein Adapter/Key eingerichtet. Eine neue Integration wäre erst nach eigenem Rechte- und Parservertrag sinnvoll. |
| **Yahoo** | [Rechteseite](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html) lieferte erneut HTTP 999. Keine erfolgreiche neue Vollprüfung; bisheriger ausdrücklicher Erlaubnisvorbehalt für automatisiertes Sammeln bleibt. | Keine neu belegten Archiv-/ML-/Scrapingrechte. Erreichbare Kursseiten oder Bibliotheken ersetzen keine Erlaubnis. | **BLOCKED** bis ausdrücklicher belegter Freigabe. Kein Umgehungsversuch. |
| **Stooq** | [Bedingungsseite](https://stooq.com/t/?i=515) verlangt Browserverifikation; Rechte und verbindliche Quote konnten nicht geprüft werden. | Automatik, Roharchiv, Weiteranalyse/ML, Adjustments und Coverage deshalb offen. | Kein automatisierter Datenzugriff, keine positive Abdeckungsbehauptung. |
| **SIX / andere Börsenwebseiten** | [SIX-Lizenzseite](https://www.six-group.com/en/products-services/the-swiss-stock-exchange/market-data/data-licensing.html) war über das Recherchewerkzeug nicht abrufbar. | Öffentliches Display beweist keine automatisierte Abruf-/Archiv-/ML-Lizenz. Kein kostenloser umfassender CH-Feed nachgewiesen. | Kein Scraping. Konkreten Datenvertrag gesondert beschaffen oder rechtmäßigen manuellen Export verwenden. |
| **Manueller eigener Broker-/lizenzierter Export** | Bestehender Originalupload mit Preview und Mapping; kein neuer Providerabruf. CH-/US-/EU-/ETF-Daten können bei passender Importstruktur und tatsächlichen Exportrechten verarbeitet werden. | Nutzer muss Aufbewahrungs-/Analyse- und gegebenenfalls ML-Rechte am Export selbst belegen. Unadjustierte Kurse, Währung und Listing eindeutig; Actions gesondert importieren/reviewen. | Verfügbarer technischer Ersatzpfad. **Kein tatsächlicher Privatbestand wurde bereitgestellt oder importiert.** |

## Deterministischer Refresh im vorhandenen Vertrag

[`ops/holdings_refresh.py`](../ops/holdings_refresh.py) liest über die authentifizierte lokale API die **aktuelle** Ledgerbewertung, Instrumentdetails, Quellenregistry und Datenbetriebsgrenzen. Nicht-nullwertige Stückzahlen werden über Konten dedupliziert; negative FX-Cashbestände werden berücksichtigt. CHF ist die unterstützte Basiswährung, EUR/USD sind die vorhandenen Fremdwährungen. Neue Holdings werden beim nächsten Aufruf neu gelesen, ausgeschiedene Holdings nicht weiter geplant. Kein Preis wird aus einer Bewertung oder einem alten Namen erfunden.

Für Auswahl und erneute Prüfung vor dem Enqueue gelten gleichzeitig:

1. Quelle in der bestehenden Registry `APPROVED`, tatsächlich enabled, geprüfter Kenntniszeitpunkt nicht zukünftig, Review noch gültig, HTTPS-Bedingungsbeleg, positive konfigurierte Quote.
2. Vorhandener Datennutzungszweck (`prices` oder `fx_rates`) **und** ausdrücklich geprüfte `raw_archive`- und `derived_analysis`-Rechte. Diese Zusatzkennungen dokumentieren den strengeren Refresh-Scope; sie sind keine automatisch erteilte Rechtsbewertung. `ml_training` ist nicht Teil dieses Auftrags.
3. Existierender Collector. Gegenwärtig kommt für automatische Preise nur der vorhandene Alpha-Adapter infrage; das ist eine technische Adapterauswahl nach erfüllter Abdeckung, kein allgemeiner Anbieterfallback.
4. Preislisting passt exakt zu internem Instrument, aktivem Listing, Providerticker, MIC, Handelswährung, Aktien-/ETF-Typ und dem gesamten angefragten Intervall. Ein Widerspruch zur Holdingswährung sperrt die Auswahl.
5. ECB-Scope erlaubt beide tatsächlich angefragten EUR-Inputreihen und das ganze Fenster. Ein einziger ECB-Job liefert die benötigten EUR-/USD-CHF-Grundlagen; zwei identische Downloads pro Fenster werden vermieden.

Die maschinenlesbaren Tokens stehen **im bestehenden append-only Quellenreview-Scope**, zusammen mit dem verständlichen Rechtebeleg. Es gibt keine zweite Quellenregistry und keine Schemaänderung:

```text
# Preisquelle: UUID/SYMBOL/MIC/WÄHRUNG/TYP/DATEN sind tatsächliche Reviewwerte.
instrument=UUID
price_listing=UUID|SYMBOL|MIC|WÄHRUNG|STOCK-ODER-ETF|YYYY-MM-DD|YYYY-MM-DD

# ECB: beide Inputs werden tatsächlich vom bestehenden Collector angefragt.
fx_inputs=EXR.D.CHF.EUR.SP00.A,EXR.D.USD.EUR.SP00.A
fx_coverage=YYYY-MM-DD|YYYY-MM-DD
```

Tokens sind durch Leerraum getrennt; ein Listingtoken enthält keinen Leerraum. Doppelte/widersprüchliche Listingtokens, fehlende Werte oder ein abgelaufener Scope führen zur Enthaltung. Das Source-Scope-Limit bleibt 2’000 Zeichen; größere Bestände brauchen einen gesondert entworfenen Vertrag statt Kürzung oder unsicherer Pauschalfreigabe. Die Alpha-Collectorprüfung auf `instrument=UUID` bleibt erhalten. Diese Planung ersetzt nicht die Backendrechteprüfung bei jedem tatsächlichen Netzwerkversuch.

Alle geplanten Jobs durchlaufen die vorhandene Preview. Deren konservative `maximum_requests` werden gegen das konfigurierte Tagesmaximum, Alpha 25/Tag und die Vier-Job-Grenze geprüft. Die Vorschau besitzt **keine Kenntnis über die aktuell verbleibende Providerquote**; die persistente serverseitige Prüfung pro Versuch bleibt zwingend. Bei einem zu großen Batch warten oder gezielt über den vorhandenen Datenbetrieb arbeiten. `--execute` erzeugt nur von der API zugelassene Jobs; Queue-Vollstand, Rechtewiderruf und Identitätsänderung bleiben Fehler. Kein Jobstatus behauptet schon eine echte Datenabnahme.

## Ausführbare Operatorfolge nach tatsächlicher Freigabe

### 1. Entscheidung und Netzwerk vorbereiten

Ein autorisierter Operator hält privat die konkreten Primärbelege, Rechte für automatisierten Abruf/Originalarchiv/Analyse, Attribution, exakte Serien/Listings, Quote und nächste Prüfung fest. Kein vorgeschlagenes Datum oder Name in dieser Anleitung ist ein erteilter Entscheid. In **Einstellungen → Datenquellen** Review erfassen, danach getrennt aktivieren. Alternativ im bereits autorisierten API-Container den vorhandenen CLI-Vertrag nutzen:

```text
python -m app.sources.cli list
python -m app.sources.cli review ECB --status APPROVED --terms-url https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html --scope "TATSÄCHLICHER-RECHTEBELEG UND DIE OBIGEN AUSGEFÜLLTEN FX-TOKENS" --use fx_rates --use raw_archive --use derived_analysis --note "PRIVATER-BELEG-MIT-FUNDSTELLE-UND-ZWECK" --reviewer "TATSÄCHLICHER-OPERATOR" --next-review YYYY-MM-DD --rate-limit-per-minute 1
python -m app.sources.cli enable ECB
```

Platzhalter vor Ausführung durch tatsächliche belegte Entscheidungen ersetzen. Die konservative lokale Minutequote ist keine von der ECB behauptete Quote. Die Core-Netze bleiben intern; ein nach Security- und Hostreview erlaubter Provider-Egress ist gesondert vorzubereiten. Ein erfolgreicher Review darf keinen stillen Netzwerkumbau auslösen. Ohne freigegebenen Authentisierungsweg beziehungsweise bei erforderlicher interaktiver TOTP den vorhandenen Browser verwenden.

### 2. Kleinen ECB-Abruf abnehmen

In **Datenbetrieb** einen einzelnen `ECB_FX`-Auftrag mit Quelle `ECB`, `series=EUR_CHF`, Start/Ende höchstens 32 vergangene Kalendertage anlegen. Für die erste Prüfung ein kleines abgeschlossenes TARGET-Intervall wählen. Preview kontrollieren, Auftrag starten, tatsächlichen Jobabschluss und Fehlercode ablesen. Der bestehende direkte Endpoint `POST /api/v1/fx/providers/ecb/collect` mit `{"start":"YYYY-MM-DD","end":"YYYY-MM-DD"}` ist alternativ für einen einzelnen autorisierten manuellen Abruf vorhanden; für dauerhafte Checkpoints den Datenbetriebsjob vorziehen.

Den tatsächlichen Originalnachweis aus dem Collector-Ergebnis über den vorhandenen **Validierung → Originalnachweis** prüfen: konkrete Raw-ID, SHA-256, erfolgreiche Byteprüfung, Quellenscope und echte Abruf-/Beobachtungszeit. Kein Modellexperiment starten. Über die bestehenden Abfragen `GET /api/v1/fx/rate?base=EUR&quote=CHF&on_date=YYYY-MM-DD`, entsprechend `EUR/USD` und `USD/CHF`, beide Inputlegs und die Decimal-Ableitung kontrollieren. Im tatsächlichen Portfolio die angezeigte FX-Herkunft, das Datum und den Freshnessstatus abgleichen. Fehlende Kurse oder Actions dürfen das Portfolio nicht scheinbar vollständig machen.

Identischen Auftrag wiederholen: keine doppelten kanonischen Werte, neuer Abruf-/No-New-Data-Nachweis und bestehender Sync-Checkpoint. An einem **späteren echten Veröffentlichungstag** erneut abrufen und den tatsächlich neuen Stand nachweisen. Erst dieser getrennte Zeitpunkt belegt Kontinuität. Antwortschemafehler, 429, Timeout und Rechtewiderruf weiterhin ausschließlich mit Offline-Fixtures simulieren, niemals durch absichtliche Überlastung des Providers.

### 3. Aktuelle Holdings vorbereiten, ausführen und nachlesen

Zugangsdaten ausschließlich über geschütztes Prozess-Environment `IIP_OPERATOR_USERNAME` und `IIP_OPERATOR_PASSWORD` bereitstellen. Sitzungscookies bleiben im Arbeitsspeicher, Logout wird versucht; kein Tokenexport. Jede Ausgabe erhält einen neuen privaten Pfad unter ignoriertem `backups/` oder außerhalb des Repositorys.

```powershell
python ops/holdings_refresh.py --origin https://PRIVATER-HOST --ca C:/privat/root.crt --portfolio-id PORTFOLIO-UUID --output backups/refresh-VORSCHAU-ZEITPUNKT.json
python ops/holdings_refresh.py --origin https://PRIVATER-HOST --ca C:/privat/root.crt --portfolio-id PORTFOLIO-UUID --execute --output backups/refresh-START-ZEITPUNKT.json
python ops/holdings_refresh.py --origin https://PRIVATER-HOST --ca C:/privat/root.crt --portfolio-id PORTFOLIO-UUID --inspect-receipt backups/refresh-START-ZEITPUNKT.json --output backups/refresh-CHECK-ZEITPUNKT.json
```

`--inspect-receipt` liest nur vorhandene private Job-IDs aus dem vorigen Receipt und fragt deren vorhandene API-Checkpoints ab; es startet keinen weiteren Providerabruf. Fehler, Teilabschluss und Fortschritt bleiben sichtbar. `JOBS_SUCCESS_NOT_LIVE_VALIDATED` bedeutet ausdrücklich nur technischen Jobabschluss; Originale, Qualität, Rechte, tatsächliche Anzeige und der zweite Veröffentlichungstag müssen zusätzlich geprüft werden. Fehlende Listingabdeckung und nicht unterstützte FX erscheinen als `MANUAL_IMPORT_OR_REVIEW`; gültige Teilaufträge können separat in der bestehenden Queue liegen. Der Gesamtstatus bleibt bei Lücken `BLOCKED`. Es wird kein autonomer Wiederholungsplan installiert.

### 4. Rechtmäßigen manuellen Weg nutzen

Vorhandenen Originalexport privat sichern, seine Rechte und Spalten prüfen. In **Instrumente** ISIN/Listing/MIC/Währung bestätigen; unter **Datenimport** unadjustierte Kurse und FX getrennt hochladen, Preview/Mapping prüfen und explizit übernehmen. Splits und Dividenden mit tatsächlichen Belegen gesondert importieren und Coverage instrument-/intervallspezifisch reviewen. Danach Ledger/Depotauszug und Datenqualität abgleichen. Wiederholung oder Korrektur erzeugt die bestehenden technischen/kanonischen Nachweise; Originale und verworfene Beobachtungen bleiben erhalten. Kein synthetischer Beispielexport ist ein tatsächlicher Privatbestand.

## Technische Prüfung und verbleibende Abnahme

**12 fokussierte lokale Fixturetests bestanden** (`python -m unittest ops.tests.test_holdings_refresh -v`): aktuelle Holdings/negative Cashbestände, Deduplication, keine Providerannahme ohne Registry, getrennte Rechte-/Aktivierungs-/Ablaufgates, exakte Listing-/Zeitraumidentität, widersprüchliche Scopes, beide ECB-Inputs, nichtfinite/fehlende Werte, Währungswiderspruch, konservative Quoten und unverfälschte Fehler-Checkpoints. Kein Test benötigt einen Finanzprovider oder gemeinsame Backend-/Browserdienste.

| Gate | Tatsächlicher Zustand | Konkreter fehlender Nachweis |
| --- | --- | --- |
| Dokumentationsprüfung | COMPLETED_WITH_LIMITS, 28.10.2026 | ECB-API-Hilfe und blockierte Rechteseiten konnten nicht neu vollständig gelesen werden. |
| Versionierter Quellenentscheid | BLOCKED_BY_SOURCE_APPROVAL | Echter autorisierter Reviewer, konkrete Rechte-/Scopebelege und getrennte Aktivierung. |
| Initiale reale ECB-Abnahme | NOT_EXECUTED | Erlaubter Egress, kleiner echter Abruf, geprüfte Originalbytes/Hash, Kanonik und Frontendbezug. |
| Fortlaufender Refresh | NOT_LIVE_VERIFIED | Zweiter tatsächlicher Veröffentlichungstag mit Checkpoint- und Freshnessnachweis. |
| CH-/US-/EU-/ETF-Kurse | PER_LISTING_NOT_ACCEPTED | Je Listing passender lizenzierter Endpoint oder rechtmäßiger Export, Währung, Historie und Actioncoverage. |
| Reales Portfolio | NOT_PROVIDED | Private Depotoriginale, Ledgerabgleich und tatsächliche unabhängige Benutzerabnahme. |

Die Dokumentation und der fail-closed Planer schließen den technischen Alpha-Fallbackfehler. Sie schließen keine Quellen-, Host-, Security-, Prognose- oder Empfehlungsfreigabe.
