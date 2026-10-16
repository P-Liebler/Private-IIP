# PR1 – Real Financial Data Readiness

Prüfstand: 2026-10-16. **PR1 COLLECTORS FUNCTIONAL.** Lokale technische Abnahme, keine Quellen-, Modell-, Strategie- oder Produktionsfreigabe. PR2 wurde nicht begonnen.

## 1. Start-Commit und Ausgangsstand

`main`, `4ded0e61efdd071ed06596c616f51f9ccb5475f0`, anfangs sauber. P0–P10 waren technisch implementiert; reale Quellen, historische Abdeckung, P7-Prognosen, P9-Strategien und die Zielinstallation hatten weiterhin offene Gates. Numerische und Assistant-Dependency-Locks bleiben bytegleich.

## 2. Baseline

195 Backendtests bestanden, Ruff/Mypy und Alembic-Driftprüfung bestanden. Die 13 vorhandenen Browserfälle wurden bestätigt: zunächst 12 bestanden, ein Login vor vollständiger API-Bereitschaft lief in den Timeout; dieser Fall bestand beim isolierten Wiederholen. Keine Live-Provideraufrufe in Tests.

## 3. Geprüfte Quellen

Primärdokumentation vom 15./16.10.2026: SEC Fair Access/EDGAR APIs, ECB SDMX/Copyright, SNB API/Copyright und konkrete Monatsverträge, OpenFIGI API/offene Symbologie, FRED/ALFRED/Terms, Alpha Vantage Dokumentation/Support/Terms, Yahoo Terms, SIX-Datendienste und ESMA-ESEF. Bei Stooq und individuellen IR-/RSS-Seiten wurde keine pauschale Archivierungs-/Abruffreigabe nachgewiesen. Links, Datenumfang, Limits und offene Rechte stehen in der Matrix.

## 4. Source-Rights-Matrix

[SOURCE_RIGHTS_MATRIX.md](data/SOURCE_RIGHTS_MATRIX.md) trennt technische Eignung, private Nutzung, automatisierten Abruf, lokale/historische Speicherung, abgeleitete Analyse, Attribution/Retention und echte Operatorentscheidung. UNKNOWN bleibt UNKNOWN. Rechteentscheidungen werden append-only gespeichert; Review deaktiviert, Aktivierung prüft separat erneut. Alte Registry-/Auditdaten erzeugen keine erfundene frühere Entscheidungshistorie.

## 5. Kostenlose API-Kandidaten

SEC, ECB und OpenFIGI bieten dokumentierte Zugänge ohne verpflichtenden Key/API-Tarif. Konkreter Scope und Datenrechte müssen trotzdem geprüft werden. SNB ist serienabhängig, insbesondere bei FX-Drittrechten. Alpha ist optional mit persönlichem Key und kleinem freien Kontingent; uneingeschränkte Langzeitarchivierung bleibt ungeklärt. FRED/ALFRED ist optional konfigurierbar, ohne neuen Collector. 0 CHF Pflicht-API-Gebühren umfasst keine Hardware-/Betriebskosten.

## 6. Weiterhin gesperrt

Yahoo bleibt BLOCKED ohne ausdrückliche Erlaubnis. Stooq und weitere nicht konkret freigegebene Quellen bleiben UNKNOWN/deaktiviert. Kein Stealth, Mirror, Captcha-, Login-, Entitlement- oder Premium-Bypass. Persönliche Keys gewähren keine zusätzlichen Nutzungsrechte.

## 7. Implementierte Collector

SEC Submissions/Company Facts/Primary Filing, ECB tägliche EXR EUR→CHF/USD, SNB monatliche Policy-/Referenzreihen, OpenFIGI Mapping mit Filtern und expliziter Annahme, optional Alpha kompakte rohe Tages-OHLCV, firmenspezifische IR-CSV und geprüfter manueller PDF-Weg, RSS-Metadaten sowie bestehende manuelle Importe. Kein allgemeiner IR-Scraper, kein FRED-Collector und kein täglicher SNB-FX-Parser.

Gemeinsamer Transport: Gate vor DNS und vor jedem Versuch, öffentliche DNS-Adressen an der Verbindung gepinnt, HTTPS/Hostbindung, keine Redirects/Proxy-Umgebung, begrenzte Bytes/Timeouts/Retry-After/Backoff, exakte Antwortbytes vor Parser, unveränderte Canonical-Writer und konservative Quoten. Fehlerantworten bleiben Raw-Evidenz. Unvollständige Transfers werden als Fehler erfasst. Keys erscheinen nicht in URL-Logs.

## 8. Tatsächliche Datenproben

Kein produktiver Live-Smoke wurde ausgeführt: reale externe Quellen sind nicht genehmigt/aktiviert. Der zulässige Zustand lautet SOURCE_NOT_APPROVED. Die Dokumentationsprüfung nutzte das offizielle SNB-R-Skript und zwei kleine öffentliche Vertragsreferenzen für Januar 2024 (`snboffzisa`, `devkum`). Diese wurden weder importiert noch als Produktpfad/LIVE_TESTED abgenommen. Offline-Tests und Browserimporte sind explizit synthetisch und belegen keine echte Marktqualität.

## 9. Historische Kurse

Keine vollständige reale mehrjährige CH/US/EU-Abdeckung behauptet. Alpha `compact` liefert höchstens 100 Beobachtungen und wechselt nicht automatisch auf Premium/Full. Vorschau begrenzt Instrumente, Zeitraum und maximale Requests; Ergebnisse und Coverage zeigen tatsächlich verfügbare Daten. Fehlende Open-Preise erzeugen NO_FILL. Korrekturen erhalten frühere Versionen; Quarantäne ersetzt keine guten Kurse.

## 10. Corporate Actions

Explizite Split-/Dividenden-/Reverse-Split-/Ticker-/Delisting-Typen und quellengenaue Belege; Sonderdividenden behalten ihre ursprüngliche Klassifikation. Operatorreviews sind instrument-, typ-, intervall- und versionsgebunden. Eine bloße Ereignisliste beweist keine Vollständigkeit. Quantitative Total-Return-Pfade bleiben bei nicht unterstützten Ereignissen oder fehlendem Split-/Dividenden-Nachweis gesperrt. Merger/Spinoff werden nicht geraten. [Action-Vertrag](data/CORPORATE_ACTION_COVERAGE.md).

## 11. FX und Makro

ECB verwendet unveränderte P3-Direkt-/Inverse-/Cross-Logik, datierte Legs und Carry-Grenzen. Konflikte gehen in Quarantäne. SNB-Monatswerte sind MacroObservation-Versionen, niemals tägliche Bewertungs-FX. 304/gleiche Bytes ändern nur Betriebs-Erfolgszeiten, nicht kanonische Werte/Wissenszeitpunkte; 304 ohne Cache ist ungültig. Echte historische Macro-Vintages bleiben unbekannt. Monatliche Datierung ist kein Intraday-Veröffentlichungsbeleg.

## 12. SEC Fundamentals

Bestehende Taxonomie-/Einheiten-/Perioden-/Filing-Verträge und Versionierung bleiben. Expliziter User-Agent/Kontakt, globale 5/s unter der SEC-10/s-Grenze, persistente Raw-Antworten, begrenzte Versuche und IDs vor HTTP. Recent Submissions sind kein vollständiges historisches Filing-Archiv. Unbekannte Kennzahlen/Tags/Akzeptanzzeiten bleiben fehlend; keine automatische Rechnungslegungsangleichung.

## 13. CH-/EU-Fundamentals

Konkrete firmenspezifische Dokumentverträge; geprüfter CSV-Import oder begrenzter PDF-Upload mit Original, SHA, Seite, exaktem Zitat, Definition und IFRS/Swiss-GAAP-FER/US-GAAP-Basis. Vorschau erzeugt null Finanzfakten. Erst ausdrückliche menschliche Bestätigung erzeugt eine neue beleggebundene Fact-Version; Korrekturen bleiben nachvollziehbar. Kein OCR-/LLM-Raten und keine universelle ESEF-Nutzungsfreigabe.

## 14. PIT

Öffentliche Verfügbarkeit, erste lokale Beobachtung und spätere Review sind getrennt. Neue Datentypen werden ab erster eigener Nutzung archiviert; heutige Downloads werden nicht rückdatiert. Coverage bewertet strenge Preis-/FX-Verfügbarkeit zu historischen Signalen, Kalender, Actions und Membership. Reconstructed Research wird nicht zu STRICT_PIT. [Historische Policy](data/HISTORICAL_DATA_POLICY.md).

Die Schemaerweiterung hätte alte P6-Zeilenhashes verändert. ADR-024 versioniert deshalb den Serialisierungsvertrag: neue Manifeste pinnen genaue Felder; alte Manifeste schließen ausschließlich bekannte neue Felder mit exakten Migrationsdefaults aus. Nicht standardmäßige neue Evidenz lässt den alten Replay scheitern. Kein Umschreiben archivierter Manifeste und keine Abschwächung von Modell-/Dependency-Gates. Alter Dataset-Replay wurde mit unverändertem Hash `dd5cd6ef97b9248eb148725797470069b9b33635df15f8506d61bf99761ea538` bestätigt.

## 15. Survivorship

Listing/Delisting und bekannte Ereignisse werden angezeigt. OpenFIGI-Unlisted-Suche beweist kein vollständiges historisches Universe. Strenge Membership verlangt zeitgerechte Evidenz, Intervallabdeckung und Delisting-Angaben. Heutige Watchlists/Bestände sind keine frühere Indexzusammensetzung. Reale historische Membership bleibt unvollständig.

## 16. Scheduler und Backfill

Persistente private Jobs mit Vorschau, idempotenter Duplikatprüfung, begrenzten Chunks, Datenbank-Sperren, Fortschritt, Cancel/Resume, Retry und Audit. Ein Commit der Daten erfolgt vor Fortschrittsbestätigung; Neustarts erhalten den Stand. Rechts-/Operatorentzug gilt auch für alte Jobs. Höchstens vier aktive Aufträge, zehn konfigurierte Zeitpläne, 30 Instrumente pro Request und fünf Jahre begrenzter Gesamtzeitraum; weitere Providerfenster gelten separat. Wiederkehrende externe Collection bleibt standardmäßig aus. API/Worker/Scheduler teilen Settings und Services.

## 17. Data Operations UI

`/data-operations`: Instrumentensuche, Datentyp/Quelle, Datumsgrenzen, CSV-Original, Vorschau der Requests, Start, private Historie/Fortschritt, Cancel/Resume/Resultate. `/settings/data-sources`: Ablauf-/Rechtegate, Review-Belege, separate Aktivierung, Historie, letzte Importe/Fehler. Instrumentenseite: Sitzungen/Lücken/Quarantäne, OHLC/Open/Volumen, FX, Action-Typen/Ereignisse, Fundamentalperioden/Restatements und PIT. Ein unbekannter Kalender wird nicht als vollständige Bewertung ausgegeben.

## 18. P4–P10-Integration

Bestehende Raw-/Canonical-/Ledger-/Research-/Feature-/ML-/Risk-/Recommendation-Services werden weiterverwendet. Coverage macht Hindernisse sichtbar und erzeugt keine Promotions. P10 `getDataQuality` kann vorhandene instrumentbezogene Evidenz erklären; Tools bleiben read-only. Kein Netzwerkcollector in Frontend/LLM, keine autonome Order, kein Eingriff in Ledger oder alte Prognosen.

## 19. Offene Datenlücken

Mehrjährige rechtlich freigegebene Aktien-/Action-Historie, verifizierte Delistings/Membership, echte damalige Verfügbarkeiten, vollständige Macro-Vintages, firmenspezifische CH/EU-Berichte und produktive Live-Smokes fehlen. Fremde Retention-/BFIX-Rechte und optionale Keys benötigen echte Entscheidungen. Unbekannte/stale Werte bleiben sichtbar; keine Null-/Fake-Fallbacks. [Limits](data/REAL_DATA_LIMITATIONS.md).

## 20. Tests und Qualität

Abschließende vollständige Backend-Regression: **232 bestanden in 118,52 Sekunden**, eine bestehende Starlette-Deprecation-Warnung. 37 zusätzliche Fälle gegenüber der Baseline decken Transport/Gates/DNS/Redirects/Größen/Fehler, Parser, SNB-Korrekturen/304, optionale Kurse/Quarantäne, PDF-Bestätigung, private Jobs, Immutable-Reviews und geteiltes Tagesbudget ab. Wiederholte Tests erschöpften zunächst den persistenten synthetischen Tagesbudgettopf. Collector-Vertragstests verwenden nun einen Mock-Limiter; die gesonderten Quotenprüfungen führen echtes Valkey/Lua mit eigenen Schlüsseln aus und prüfen unveränderte Minuten-/Sekundenlimits sowie ein quellübergreifendes Tagesbudget. Keine produktiven Budgets wurden zurückgesetzt oder Guards entfernt.

Ruff/Format/Mypy (186 Quelldateien), Frontend lint/typecheck/Standalone-Build, Compose-Build und beide Compose-Konfigurationen bestanden; die Produktionskonfiguration wurde nur mit synthetischen Konfigurationswerten gerendert, nicht ausgerollt. Alembic ohne Drift, frische Migration, pip check, Celery und MinIO-Smokes bestanden.

**15 verschiedene Browserfälle bestätigt**: alle 13 bestehenden Fälle bestanden im Gesamtlauf; die zwei neuen Operations-Fälle bestanden nach Korrektur ihrer Selektoren und eines echten Frontend-Mapping-Feldfehlers gemeinsam in 39 Sekunden. Der CSV-Fall archiviert ein gekennzeichnetes synthetisches Original, prüft null externe Requests, startet einen persistenten Job, wartet auf Celery-SUCCESS und prüft den vorhandenen Open-Kurs bei weiterhin unverifizierter Action-Coverage. Keine Quelle wurde dabei genehmigt. Lokale Logs liegen unter `backups/pr1-final-regression.txt`, `pr1-browser-final.txt`, `pr1-browser-operations.txt` und `pr1-web-final.txt` und werden nicht eingecheckt.

## 21. Migrationen

`0017_data_operations` ergänzt vier Tabellen: Jobs, Sync, Rechteentscheidungen und Coverage-Snapshots. `0018_provider_evidence` ergänzt typisierte Action-Evidenz, Eventdetails und optionale Macro-Metadaten sowie unveränderliche Review-/Coverage-Updatesperren und Alpha UNKNOWN/deaktiviert. Frühere Migrationen unverändert. Upgrade und frische Migration auf `0018_provider_evidence` mit **75 Tabellen** bestanden; lokale Iterationsdatenbank wurde auf die endgültigen Trigger/Seeds abgeglichen. Vor Verwendung auf einer anderen bereits migrierten Entwicklungsdatenbank deren Schema prüfen.

## 22. Restore

**Bestanden am 2026-10-16, 10:33:33–10:34:34 UTC.** Backup `backups/pr1-acceptance/sets/20261016T103306Z-23484`: PostgreSQL und **246 Raw-Objekte**, vollständige Dateiprüfsummen. Hintergrundprozesse wurden vor dem Checkpoint gestoppt, danach die API für das Backup. Restore in eigenem zufälligem Compose-Projekt mit separatem PostgreSQL/MinIO/Valkey/API, anschließend nur dessen Ressourcen entfernt. Die lokale Umgebung wird wieder im normalen Modus betrieben: APP_ENV=local, ASSISTANT_TEST_MODE=false, wiederkehrende Collection=false.

Geprüft: Head 0018, private Anmeldung, Raw-Hashes, gepinnter P6-Dataset-Replay, P7-Modellartefakt inklusive unveränderter numerischer Dependency-Gates und MLflow-Metadaten, Prediction-/Risk-/Scenario-/What-if-/Recommendation-/Assistant-Historien einschließlich exakter Embeddings sowie exakt **CHF 10'180**. Keine Archivmanifeste geändert und keine Guards gelockert.

Der zusätzliche Collections-Hash `53dd24303a11495376749a45446be1e31d28da1bb8c71748292ba5aa133d3c28` stimmt nach Restore exakt überein. Er umfasst 20 Quellen, 6 Rechtebelege, 1 abgeschlossenen synthetischen Importjob, 11 Kursversionen, 2 FX-Versionen, 30 Fundamentalfakten, 38 Action-Versionen und 8 Action-Reviews. Sync, Coverage-Snapshots und Macro-Versionen enthalten in diesem gesicherten Bestand jeweils **keine Datensätze**; ein befülltes produktives Sync-/Makroarchiv wird damit nicht behauptet. Deren Schreib-/Korrekturverträge sind separat offline getestet. Checkpoint: `backups/pr1-checkpoint.json`; Restore-Nachweis: `backups/pr1-acceptance/runtime/restore-status.json` mit success=true. Das lokale Backup ersetzt nicht den unabhängigen Produktionsmount oder einen nachgewiesenen automatischen Sicherungszeitplan.

## 23. Remote CI

Vom Nutzer bestätigter Ausgangslauf: `38751875228`. Neue Änderungen wurden nicht gepusht. **REMOTE CI NOT VERIFIED FOR THIS CHANGE.** Der Workflow übernimmt die explizite synthetische Operator-Konfiguration auch für Worker/Scheduler. Keine neue Remote-Abnahme oder Release behauptet.

## 24. Unabhängige Quellenstatus

[PROVIDER_INVENTORY.md](data/PROVIDER_INVENTORY.md) führt IMPLEMENTED, OFFLINE_TESTED, LIVE_TESTED, OPERATOR_APPROVED, ENABLED und SCHEDULED getrennt auf. Alle realen externen Produktpfade sind LIVE_TESTED=Nein, OPERATOR_APPROVED=Nein, ENABLED=Nein, SCHEDULED=Nein. MANUAL_CSV behält seinen bestehenden Upload-Scope; TEST_-Quellen sind nur synthetische Fixtures. Dokumentationszugang ist kein Produkt-Live-Smoke.

## 25. Echte Readiness

**PR1 COLLECTORS FUNCTIONAL · SOURCE APPROVAL PARTIAL · REAL DATA COVERAGE PARTIAL · V2 FORECASTS NOT VALIDATED · V3 RECOMMENDATIONS GATED · V3+ PRODUCTION NOT RELEASED.** Kein reales Coverage-Prozent aus Fixtures. Homelab/VPN, Browser-CA, unabhängiger Backup-Mount/-Zeitplan und Schlüssel-Recovery bleiben Zielinstallationsgates.

## 26. Hindernisse für zuverlässige Prognosen

Es fehlen ausreichend lange rechtmäßige, vollständige, zeitgerecht belegte Preis-/Action-/FX-/Fundamental-/Membership-Daten sowie reale Out-of-sample-/Kalibrierungs-/Intervall-/Strategienachweise. Mehr Daten allein bestehen keine P7-/P9-Gates. Vorhandene Modelle bleiben SHADOW; schlechte Prognosen/Outcomes und Abstentionen bleiben unverändert sichtbar. Der lokale LLM kann diese Zustände erklären, keine Freigabe erzeugen.

## 27. Nächste Etappe

Nach echter Operatorfreigabe zuerst kleine reale, begrenzte und archivierte Collector-Smokes und deren Coverage prüfen. Danach separat **PR2 – Real Historical Validation & ML/Recommendation Acceptance** beauftragen. PR1 endet mit seinem Abschlussbericht; PR2, Modell-/Strategie-Promotion, Brokerintegration, echter Handel und Produktionsfreigabe wurden nicht begonnen.
