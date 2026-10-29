# PR10C – Reale Datenversorgung

Prüfdatum **29.10.2026**. **BLOCKED_BY_SOURCE_APPROVAL / LIVE_NOT_EXECUTED**.
Es wurden Dokumentationsseiten geprüft, keine Finanz-API-Requests ausgelöst.
Keine Quelle wurde freigegeben oder aktiviert. Private Depotoriginale und eine
abgenommene Zielumgebung liegen für diesen Arbeitsschritt nicht vor.

## Entscheidung

Die erste konkrete Quelle bleibt der vorhandene ECB-Tages-FX-Collector.
EUR/CHF und EUR/USD werden gemeinsam geprüft; USD/CHF ist eine nachvollziehbare
Decimal-Ableitung dieser beiden Eingangsreihen. Ein Operator muss den
vorbereiteten [Rechte- und Nachweisbogen](data/PR10_SOURCE_OPERATOR_REVIEW.md)
mit tatsächlichen Entscheidungen ausfüllen. Der Bogen erteilt keine Freigabe.

| Zustand | Tatsächlicher Nachweis in PR10C |
| --- | --- |
| Dokumentierte Quellenprüfung | ECB und OpenFIGI am 29.10.2026 erneut gelesen; API-Hilfe der ECB nicht erreichbar |
| `TECHNICALLY_VERIFIED` | Gezielter ECB-Scopefix: 15 neue Offlinefälle, zusammen mit bestehender Transportregression 50 Tests bestanden; kein neuer Produktionsimagenachweis daraus |
| `LIVE_SOURCE_VERIFIED` | **Nein:** kein autorisierter Liveabruf, keine tatsächlichen Raw-/Canonical-/UI-Belege |
| `AUTOMATIC_REFRESH_VERIFIED` | **Nein:** kein erstes und späteres echtes Ereignis, keine dauerhafte Versorgung abgenommen |
| Aktien-/ETF-Coverage | **Offen je Listing:** keine konkreten Bestände oder Listingrechte vorgelegt |
| Reales Portfolio | **Nicht geprüft:** Security-, Zielumgebungs-, Backup- und Originalvoraussetzungen fehlen |

Die alten [PR9C-Nachweise](PR9C_REAL_DATA_ENABLEMENT_REPORT.md) bleiben mit ihrem
Prüfdatum erhalten. Ihre damalige Registrybeobachtung wird nicht als neue
Read-only-Registryprüfung vom 29.10. ausgegeben. Eine externe Source-Freigabe
wurde im PR10-Auftrag nicht mitgeteilt.

## 1. Primärdokumentation und Rechte

### ECB

Die [ECB-Copyrightbedingungen](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html)
erlauben freie Nutzung direkt bezogener Informationen mit korrekter Wiedergabe,
Quellenangabe und Kennzeichnung eigener Änderungen. Für namentlich gezeichnete
Autorenwerke gelten Ausnahmen. Das ist eine brauchbare Grundlage für den
konkreten Review statistischer EXR-Daten, keine bereits erfasste
Registryentscheidung. Automatisierter Endpointzugriff, unverändertes
Originalarchiv, dauerhafte Aufbewahrung und interne Ableitung müssen im
konkreten Entscheid erfasst sein. Drittinhalte und ML-Training sind daraus
nicht pauschal freigegeben.

Die [Referenzkursseite](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html)
beschreibt normalerweise Veröffentlichung um 16:00 CET an Arbeitstagen außer
TARGET-Schließtagen und EUR als Basis. Sie warnt vor Verwendung der
Informationskurse für Transaktionen. Die App nutzt sie deshalb als
Referenzbewertung; tatsächliche Brokerwechsel, Spreads und Gebühren bleiben
Ledgerdaten. Eine geplante Veröffentlichung ist kein beobachteter
Kenntniszeitpunkt und keine garantierte Tagesverfügbarkeit.

Die Dokumentationsseiten [API-Überblick](https://data.ecb.europa.eu/help/api/overview)
und [API-Daten](https://data.ecb.europa.eu/help/api/data) lieferten beim
Recherchezugriff am 29.10.2026 HTTP 503. Es wird keine neue verbindliche
numerische ECB-Quote behauptet. Ein lokales Limit von einer Anfrage pro Minute
ist eine vorgeschlagene konservative Konfiguration, kein Anbieterzitat.
Öffentlich angezeigte Werte wurden nicht importiert oder als Finanzbeleg
übernommen.

### OpenFIGI

Die [API-Dokumentation](https://www.openfigi.com/api/documentation) nennt für
Mapping ohne Key 25 Requests/min und 10 Jobs/Request, mit Key 250/min und 100
Jobs/Request. Search/Filter haben eigene Grenzen von 5 beziehungsweise 20/min.
429 erfordert Warten gemäß `retry-after`. MIC und `exchCode` sind alternative
Filter; Währung kann gefiltert werden. Die normale Mappingantwort garantiert
kein MIC-/Währungsfeld. Unlisted Equities sind standardmäßig ausgeschlossen;
`includeUnlistedEquities` erweitert die Suche. Das belegt keine vollständige
historische Listingchronik. Die lokale Integration sendet einen Mappingjob pro
Request; ein Key ist nicht zwingend.

Die [Terms](https://www.openfigi.com/docs/terms-of-service), zuletzt dort mit
27.11.2018 bezeichnet, widmen FIGI-Identifier der Allgemeinheit und gestatten
ihre Nutzung und Ableitung. Sie garantieren keine Richtigkeit der
Beschreibungen und erteilen keine Markenlizenz. Die
[FAQ](https://www.openfigi.com/about/faq) beschreibt offene FIGI-Symbologie und
zugehörige Metadaten sowie fehlende Ausgabe fremder geschützter Identifier.
Rechte an eingegebenen Drittkennungen und der konkrete archivierte
Antwortumfang bleiben im Review explizit. Ein FIGI-Mapping liefert keine Kurse.

## 2. Tatsächlich implementierter ECB-Vertrag

Quellcode: [`EcbFxCollector`](../backend/app/providers/ecb_fx.py),
[`fetch_response`](../backend/app/providers/http.py),
[`provider_canonical`](../backend/app/services/provider_canonical.py),
[`MarketQueryService.fx`](../backend/app/services/market_queries.py).

| Punkt | Implementierung / Abnahmegrenze |
| --- | --- |
| Origin | `https://data-api.ecb.europa.eu` mit festem öffentlichem Host und gepinnter DNS-Verbindung |
| Pfad | `/service/data/EXR/D.CHF+USD.EUR.SP00.A` fragt **immer beide** Eingangsreihen an |
| Eingangsreihen | `EXR.D.CHF.EUR.SP00.A` = CHF je EUR; `EXR.D.USD.EUR.SP00.A` = USD je EUR |
| Request | `startPeriod`, `endPeriod`, `format=csvdata`, `includeHistory=false`; pro Collectoraufruf höchstens 32 vergangene Kalendertage |
| Parser | `ecb-exr-csv-v2`: tägliche EUR/SP00/A-Reihen, zulässige Währungen, positive endliche Decimal-Werte, eindeutiger Tag/Währung, keine Tage außerhalb des Requests |
| Original | Exakte begrenzte Antwortbytes vor Parsing, Raw-ID, SHA-256, Request-/Empfangszeit; verifizierte Rücklesung vor Kanonik |
| Wiederholung | Request-/Parserversion pinnen; vorhandene ETag-/Last-Modified-/Content-Hash-Zustände; identische Daten bleiben idempotent |
| Revision | Aktuell geladener Stand, keine vollständige Vintagehistorie; neue lokale Beobachtung wird nicht rückdatiert; Konflikte bleiben reviewpflichtig |
| Leere / partielle Antwort | Parser garantiert nicht beide Reihen an jedem Tag; selbst technisches `SUCCESS` beweist keine vollständige FX-Abdeckung |

Für USD/CHF muss beim ersten Echtbeleg gelten:

```text
USD/CHF = (CHF je EUR) / (USD je EUR)
```

Beide konkreten Leg-IDs müssen denselben tatsächlich veröffentlichten
Referenztag, den freigegebenen ECB-Source-Eintrag und geprüfte Originale haben.
`MarketQueryService.fx` kann allgemein auch andere akzeptierte Quellen sowie
übertragene ältere Legs verwenden. Deshalb sind `source_ids`, `legs`,
`rate_date`, `carry_days`, `derived`, `known_at` und `retrieved_at` zu prüfen.
Ein vorhandener direkter manueller USD/CHF-Kurs ist kein Beweis für den
ECB-Kreuzkurs. Unterschiedliche Leg-Tage oder `AVAILABLE` mit Carry sind nicht
als aktuelle vollständige Tagesabnahme zulässig. Keine Werte werden zu Null
ergänzt.

### Nachgewiesene Scope-Lücke und gezielte Korrektur

Der unveränderte PR9-Stand prüft im Collector und HTTP-Transport `APPROVED`, `enabled`,
gültigen Review und `fx_rates`. Die strengeren PR9-Tokens `fx_inputs` und
`fx_coverage` sowie `raw_archive`/`derived_analysis` werden dort noch nicht
ausgewertet. Nur der Holdings-Planer prüft sie. Ein direkter ECB-Job kann den
Planer umgehen; das ist eine konkrete Vertragslücke.

Die isolierte Offline-Reproduktion verwendete das unveränderte PR9-Image
`private-iip/backend@sha256:5a925e0ea0bfffabeda6ee735f60db9d0235b3ab149b059984f9150cf0d21667`,
`--network none` und `httpx.MockTransport`: synthetisch freigegeben war nur die
CHF-Reihe für 01.–02.02.2024, tatsächlich angefragt wurden CHF **und** USD für
03.01.2024. Der Transport erhielt ausschließlich `fx_rates` als Nutzungsrecht,
übergab dennoch eine synthetische Antwort an den gemockten Raw-Store und
erreichte den gemockten Canonical-Writer mit `SUCCESS`.
Kein wirklicher Operatorentscheid und kein Providerrequest war beteiligt.

**Gezielte Korrektur:** `EcbFxCollector.require_scope` verlangt vor dem Abruf
die bestehenden beiden `fx_inputs`, genau ein deckendes `fx_coverage` sowie
`fx_rates`, `raw_archive` und `derived_analysis`. Doppelte, fehlende oder
widersprüchliche Scopefelder sperren den Request. Dieselbe Prüfung kontrolliert
in `BackfillJobService.preview` das vollständige angefragte Intervall, bevor
ein Job entsteht. Der bestehende HTTP-Transport erhält einen optionalen
synchronen `scope_validator`: vor Clienterzeugung und nach erneuter
Registryprüfung in jedem Versuch. Andere Provider behalten ihren bisherigen
Vertrag. Ein geänderter Review stoppt einen laufenden Request statt dessen
neue Rechte zu erben; die bereits archivierte 429-Antwort bleibt erhalten.

Historische freie Reviewtexte bleiben unverändert erhalten. Sie beweisen
maschinenlesbar weder die beiden Inputs noch das konkrete Zeitintervall. Für
diesen konkreten Pfad ist ein neuer append-only Review erforderlich; keine
alte Entscheidung wird nachträglich umgedeutet.

**Regression am 29.10.:** 15 neue Tests in
[`test_pr10_ecb_scope.py`](../backend/tests/unit/test_pr10_ecb_scope.py) bestanden;
zusammen mit `test_pr1_providers.py` und `test_pr7_provider_review.py` sind
**50 Offlinefälle** grün. Geprüft sind fehlende Archiv-/Analyserechte,
einseitige/ungültige/doppelte Scopes, vollständiges Backfillfenster,
Reviewänderung während Synclookup/Retry, erhaltene erste Fehlerbytes und der
positive exakte Request mit Raw-Verifikation vor Kanonik. Die Fixtureläufe
verwenden das vorhandene Entwicklungsimage mit schreibgeschützt gemountetem
aktuellem Code und deaktiviertem Netzwerk. Sie sind kein Nachweis eines neuen
gescannten Produktionsimages. Der [öffentliche technische Beleg](data/pr10-ecb-scope-regression.json)
bindet Log- und Quellcodehashes. Gezielte Ruff- und Mypy-Prüfungen der drei
geänderten Backenddateien sind ebenfalls grün; der eigentliche Rechteentscheid
bleibt offen.

## 3. Ausführbare erste und spätere Liveabnahme

Der [Operatorbogen](data/PR10_SOURCE_OPERATOR_REVIEW.md) enthält den bestehenden
Review- und Jobvertrag. Die Reihenfolge bleibt:

1. Securityfreigabe, geeignete private Umgebung, Recovery und autorisierten
   Datenoperator feststellen. Für private Portfoliooriginale gelten zusätzlich
   PR10D. Ohne diese Voraussetzungen nur isolierte synthetische Tests.
2. Primärbelege mit Datum/Fundstelle privat sichern; konkrete ECB-Reihen,
   erlaubtes Intervall, Nutzungen, Attribution, Quote und nächstes Review
   entscheiden. Bestehende Source Registry reviewen, **danach getrennt**
   aktivieren. Erlaubten Egress zu genau dem offiziellen Host prüfen; weder
   interne Compose-Netze noch OpenShift-NetworkPolicies still öffnen.
3. Ein kleines abgeschlossenes TARGET-Intervall in **Datenbetrieb** als
   `ECB_FX` mit Quelle `ECB` vorschauen, dann einmal starten. `series=EUR_CHF`
   wählt beim vorhandenen ECB-Collector nicht einen einzelnen Leg; der Request
   enthält weiterhin beide Eingangsreihen.
4. Tatsächlichen Jobabschluss, Fehler, `raw_ingestion_id`, Status und
   Parserkennung prüfen. Über **Validierung → Originalnachweis** die
   Originalbytes/SHA-256 verifizieren. Erst echte Provideroriginale dürfen
   append-only als `REAL_PROVIDER` eingeordnet werden; synthetische Originale
   bleiben synthetisch.
5. Serien, Antwortdatum, Canonical-IDs, Quellenscope, Qualität und gegebenenfalls
   Quarantäne kontrollieren. `GET /api/v1/fx/rate` für EUR/CHF, EUR/USD und
   USD/CHF mit explizitem `on_date` lesen. Beide Inputs und die oben genannte
   Kreuzrechnung abgleichen. Das tatsächliche Portfolio muss genau diese
   Herkunft/Legs und Aktualität zeigen; fehlende Preise/Actions dürfen die
   Gesamtbewertung weiter sperren.
6. **Identischen** Job erneut ausführen. Bei laufendem Auftrag darf dessen
   vorhandene ID zurückgegeben werden; nach Abschluss ist ein neuer
   Abrufnachweis nötig. Keine doppelten kanonischen Werte; neue Raw- oder
   No-New-Data-Evidenz und vorhandenen Synczustand prüfen. Ein HTTP 304 ist
   keine neue FX-Beobachtung und darf alte `known_at` nicht erneuern.
7. An einem **späteren tatsächlichen Veröffentlichungstag** einen neuen kleinen
   erlaubten Abruf ausführen. Neue Referenzdaten, tatsächliche Abrufzeit,
   Canonical-/Raw-IDs und UI-Freshness separat protokollieren. Ein zweiter
   sofortiger identischer Abruf beweist keine fortlaufende Versorgung.
8. Erst nach zwei getrennten Echtbelegen, erlaubtem Zeitplan, Quote,
   Fehlermonitoring und ausdrücklichem globalem/individuellem Opt-in eine
   vorhandene wiederkehrende Sammlung aktivieren. Tests für Timeout, 429,
   Schemafehler, Rechtewiderruf und Retry bleiben offline; keine absichtliche
   Providerüberlastung.

Der vorhandene [`ops/holdings_refresh.py`](../ops/holdings_refresh.py) bleibt
der Bestandsplaner: Vorschau standardmäßig, `--execute` stellt bestehende Jobs
ein, `--inspect-receipt` liest vorhandene Jobcheckpoints. Er fragt das Fenster
bis **gestern** ab und weist keine heutige Veröffentlichung nach. Sein
`JOBS_SUCCESS_NOT_LIVE_VALIDATED` ist kein fachliches Live-Gate. Zugangsdaten
gehören nur in geschützte Prozessvariablen; Cookies verbleiben im Speicher.
Bei interaktiver TOTP-Anforderung den Browser verwenden. Private Receipts
bleiben außerhalb von Git, unter geschütztem ignoriertem `backups/` oder in
einem privaten Verzeichnis. Es wurde kein Zeitplan installiert.

## 4. OpenFIGI nach konkreter Freigabe

Der vorhandene `OPENFIGI`-Datenbetriebsjob nimmt genau ein bereits geprüftes
Instrument, verwendet dessen ISIN oder FIGI und sendet vorhandene MIC/Währung
als Filter. Ein normales Instrument-Mapping verwendet dagegen das vorhandene
Exchangefeld; beide Pfade dürfen nicht als identische Filteranfrage ausgegeben
werden. Der gemeinsame Provider archiviert die exakte Antwort vor Parsing.

Nach einem autorisierten Review für `mapping` samt Originalarchiv und Analyse:
einen kleinen Mappingjob vorschauen/starten, Raw-SHA und tatsächliche
Requestfilter prüfen. Kandidaten mit ihren vorhandenen FIGI-, Ticker-, Typ-,
Namens- und Exchangefeldern vergleichen. `exchCode` ist kein automatisch
nachgewiesener ISO-MIC. Fehlen MIC, Währung oder gültiger Listingzeitraum,
bleiben diese Angaben offen oder werden durch einen unabhängigen berechtigten
Listingbeleg geprüft. Kein Land oder Ticker-Suffix ersetzt diesen Nachweis.

`MappingService.accept` prüft die ausgewählte FIGI gegen **das gespeicherte
Original**; die ausdrückliche Auswahl bleibt selbst bei `UNIQUE_CANDIDATE`
erforderlich. Mehrfachtreffer, No-Match, unlisted und spätere Wiederholung
separat protokollieren. Keine Annahme des ersten Treffers und keine
Preisdatenfreigabe aus der Mappingbestätigung ableiten.

## 5. Aktien/ETFs und manueller Weg

Der Nutzer wünscht allgemeine ISIN-Unterstützung; konkrete Holdings sind nicht
vorgegeben. Es wird keine bereits belegte CH-/US-/EU-/ETF-Gesamtabdeckung
behauptet und keine erneute Frage nach 1–5 Instrumenten gestellt. Die
[PR9-Kandidatenprüfung](PR9C_REAL_DATA_ENABLEMENT_REPORT.md) bleibt ein
datierter früherer Dokumentationsbefund, keine neu datierte Vertragsprüfung.

Für den ersten tatsächlichen Bestand ist im privaten Bogen **je Listing** zu
erfassen: ISIN, interne ID, MIC, Handelswährung, Typ, Providerticker/Endpoint,
tatsächliche Datenabdeckung und Frequenz, Abrufrecht, Raw-Speicherung,
Langzeitarchiv, Analyse/ML getrennt, Split-/Dividendencoverage und Stichtag.
Alpha Vantage ist ein vorhandener Adapter, kein automatischer Gratisfallback.
Yahoo/Stooq/andere Seiten erhalten keine Freigabe aus Erreichbarkeit oder
Bibliotheksverfügbarkeit. Fehlende Rechte/Abdeckung bleiben
`MANUAL_IMPORT_OR_REVIEW`.

Ein rechtmäßiger manueller Export ist für Core V1 ein vollständiger
Beschaffungsweg: private Originalablage, explizites Listing, Preview/Mapping,
unadjustierte Preise und FX, gesonderte Actions/Coveragereviews, danach
Ledger-/Depotauszugabgleich. Er ersetzt keine fehlende Kursquelle durch
erfundene Livewerte. Manueller Import kann einen echten Portfolio-Pilot
ermöglichen, ohne `AUTOMATIC_REFRESH_VERIFIED` zu behaupten.

## 6. Noch fehlende externe Nachweise

Der abschließende [Produktionsimage-Regressionsbeleg](security/pr10-20261029/regression-final.json)
ergänzt die fokussierten Fixturetests um **321 Tests je neuem Backendbuild**,
eigene Scans und beide vollständigen Restores. Auch daraus folgt keine
Quellenfreigabe. Die erneute [read-only Prüfung nach der Browserregression](security/pr10-20261029/source-registry-post-regression.json)
bestätigt ECB/OpenFIGI weiterhin UNKNOWN und deaktiviert, ohne Approval oder
Reviewdatum. Testmodus, Collection, Forward-Scheduling und temporäre
Operatorrollen sind aus. Kein Live-Finanzproviderrequest wurde ausgelöst.

| Voraussetzung | Benötigter tatsächlicher Beleg |
| --- | --- |
| Quellenentscheid | Verantwortlicher Operator, konkrete Rechte/Fundstellen, Scope, Verwendungsarten, Quote, nächstes Review und getrennte Aktivierung |
| Privater Zielbetrieb | Gewählter tatsächlich zugänglicher Host/Cluster, Securityfreigabe, TLS/VPN/Egress, sichere Originalablage und Recovery |
| ECB Initialabruf | Kleiner echter Request, Originalbytes/Hash, Serien/Datum, Canonical-IDs, gültige reale FX-Herkunft in der Bewertung |
| Kontinuität | Zweiter späterer Veröffentlichungstag mit neuem echten Abruf/Checkpoint und geprüfter Aktualität |
| OpenFIGI live | Konkreter freigegebener Mappingrequest, gespeicherte Kandidaten und ausdrücklicher Identitätsentscheid |
| Kurse/Actions | Listingbezogener Lizenz-/Exportnachweis, gültige Kurse und separat geprüfte Actions |
| Reales Portfolio | Vom Nutzer bereitgestellte private Originale erst nach PR10D-Voraussetzungen; tatsächlich erklärter Depotabgleich |

Dokumentation, Offline-Regression, ein grüner Collectorjob, eine Argo-Sync oder
ein LLM-Text erteilen keines dieser externen Gates.
