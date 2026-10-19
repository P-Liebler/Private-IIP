# PR2 – Gesamtbericht

Stand: 19.10.2026. **PR2 TECHNICAL IMPLEMENTATION ABGENOMMEN. Reale Modell- und Strategievalidierung bleibt gesperrt.**

| Bereich | Fachlicher Status |
| --- | --- |
| PR2A | BLOCKED_BY_SOURCE_APPROVAL |
| PR2B | BLOCKED_BY_REAL_DATA |
| Reale Forecasts | V2 FORECASTS NOT VALIDATED |
| Reale Empfehlungen | V3 RECOMMENDATIONS GATED |
| Zielinstallation | V3+ PRODUCTION NOT RELEASED |

Ausgangsstand: lokales und Remote-main `cfa8c51230d42f6a1d3cc0b766a8c2449dd04ec4`. Der ausdrücklich geforderte PR1-Workflow `38889975378` wurde als **completed/success** geprüft; dessen Job `116936818464` einschließlich Backend, Frontend und Browser war erfolgreich. Kein älterer P10-Workflow wurde dafür eingesetzt. Lokale PR1-Baseline erneut: **232 Backendtests bestanden**.

PR2 ergänzt eine einzige append-only Evidenztabelle (`0019_validation`, 76 Tabellen) und verwendet vorhandene PR1/P6/P7/P9-Dienste. Es gibt keine zweite Collector-, Dataset-, ML- oder Recommendation-Architektur. Source-/ML-/Strategy-Gates bleiben wirksam. Kein Finanzprovider-Liveaufruf, keine neue reale Source-Freigabe, kein Brokerauftrag und keine Promotion wurde ausgeführt.

## Änderungen und Fehlerkorrekturen

Readiness über Quellen, Datenherkunft, Coverage, PIT, Dataset und quantitative Partitionen; Rechte-Checklisten und begrenzte Pilot-Orchestrierung; unveränderliche Experimentverträge mit unberührtem OOS; vorhandene P7-/P6-Kosten- und Baseline-Evaluation; gepinnte Regime-Regeln; aktuelles Forward Shadow mit späteren Outcomes; P9-Strategieprüfung und vier Bedienansichten.

Korrigiert wurden benutzerübergreifende PR1-Jobdeduplizierung, das fehlende Quality-Payload im P7-Finanzpfad sowie die fehlende Weitergabe des bestehenden Collections-Checkpoint an den isolierten Restore-Container. Neue FX-Kosten werden explizit verbucht. Historische Requests, Finanzdaten, Vorhersagen, Artefakte und Dependency-Locks bleiben erhalten.

## Prüfprotokoll

| Prüfung | Ergebnis |
| --- | --- |
| Backend-Regression | 257 bestanden, einschließlich aller 232 bisherigen Fälle; 277,20 s |
| Neue gezielte PR2-Suite | 25 bestanden; zusätzlich zwei Nachprüfungen der letzten Guards bestanden |
| Ruff / Format | Bestanden; 283 Backenddateien formatiert |
| Mypy | Bestanden; 197 App-Dateien |
| Frontend | Lint, Typecheck und Standalone-Build bestanden |
| Alembic | Upgrade und Driftprüfung bestanden; frische Migration 0019_validation / 76 Tabellen |
| Abhängigkeiten | pip check bestanden; numerische/Assistant-Locks und Frontend-Lock unverändert |
| Compose / Images | Lokale und produktive Syntax geprüft; Images gebaut |
| Betriebs-Smokes | Celery-Task und MinIO-Roundtrip erfolgreich; MLflow-Health HTTP 200 |
| Browser | 20 bestanden: alle 15 bisherigen Fälle plus fünf neue PR2-Fälle |
| Isolierter Restore | Bestanden; 290 Raw-Objekte, zehn PR2-Belege, Golden-Wert exakt CHF 10'180 |

Lokale Nachweise liegen unter `backups/pr2-verified-regression.txt`, `pr2-focused-final.txt`, `pr2-last-guards.txt`, `pr2-static-accepted.txt`, `pr2-format-accepted.txt`, `pr2-frontend-final.txt` und `pr2-migrations.txt`. Ein bekannter Starlette/httpx-Deprecation-Hinweis bleibt; keine Finanzprovider-Anfragen in der Testsuite.

Ein Zwischenlauf fand eine PostgreSQL-Gruppierung mit verschiedenen JSON-Key-Bindparametern im Forward-Report; der Ausdruck wird nun gemeinsam verwendet und ist per Integrationstest geprüft. Die OOS-Reservierung gilt auch für neue Dataset-Versionen desselben Universums/Horizonts. Doppelte Regime-Namen sind unzulässig.

Die erste Browserprüfung fand eine veraltete lokale Golden-FX-Fixture und eine unpräzise Wartebedingung auf einen älteren Collector-Auftrag. Der anschließende Research-Fall verlangte zusätzlich eine zum aktuellen Testkurs passende Aktien-/Split-Basis. Die Produkt-Stale- und Split-Basis-Gates bleiben unverändert. Der strikt auf Testmodus, ausdrücklichen Opt-in und benannte disposable Fixtures begrenzte Helper `scripts.refresh_restore_fixture` ergänzt datierte **SYNTHETIC**-Originale über bestehende Importer und versionierte Fakten. Alte Beobachtungen bleiben erhalten; Wiederholung ändert keine kanonischen Werte. Neue Importbelege dürfen entstehen. Diese Daten sind keine echten Finanzdaten. Der CSV-Browserfall wartet nun auf die konkrete neue Job-ID.

## Git, Infrastruktur und Reproduzierbarkeit

Branch `main`; Änderungen lokal und uncommitted, kein Push/Release. Remote-main am 19.10.2026 erneut unverändert geprüft. Neue Dienste: RealDataReadinessService, RealDataPilotService, ValidationExperimentService, ForwardValidationService sowie unveränderliche ValidationRecords und deren Restore-Checkpoint. API und Celery verwenden dieselben Einstellungen und Domainmodule. Keine neuen Bibliotheksabhängigkeiten.

Backup `backups/pr2-acceptance/sets/20261019T053043Z-51488`, nach Stop aller API-/Worker-/Scheduler-/Web-Schreibprozesse. Isolierter Restore **19.10.2026, 05:31:39–05:32:55 UTC**, erfolgreich; eigene Container, Netzwerk und Volumes anschließend bereinigt. Die folgenden erwarteten Checkpoints wurden an den Restore übergeben und geprüft:

| Archiv | Verifizierter Stand |
| --- | --- |
| P6 | Dataset a4c9d4ff-07de-44d0-a89b-53e843648994; unveränderter Hash dd5cd6ef97b9248eb148725797470069b9b33635df15f8506d61bf99761ea538 |
| P7 | Modell 678d4cd7-776b-4183-bbb6-18a0b4a0b506; Artefakt 9706d2dc2631d0cfde24ddaad3ccd4f41b686351cd5b82ecd5e0a96fc18f5c94; strenge Runtime-/MLflow-Prüfung |
| Prognosen | 26 archivierte Einträge; null Outcomes, keine daraus behauptete reale Forecast-Güte |
| P8 | 36 Risk-Snapshots, 18 Szenarien, 18 What-if-Runs; exakte Hashes und Quellenpins |
| P9 | Zehn Recommendations und neun Profile; Regeln, Reviews und Historie unverändert reproduzierbar |
| P10 | Zwei Dokumente/Chunks/Embeddings, sechs Nachrichten, zwölf Alert-Evaluationen, drei Briefs, acht Optimizer-Runs; exakte Inhalte/Embeddings |
| Quellen / Collector | 20 Sources, zehn Rechtebelege, vier Jobs; bestehender Collections-Checkpoint jetzt tatsächlich durchgereicht |
| PR2 | Zehn append-only Belege; Hash 5267e3d8b68ce39aed15065f0fd88fdbe237e94822e32cf39ecc26de7dfca373 |
| Portfolio | Login und vollständige Bewertung exakt CHF 10'180 |

Details: `backups/pr2-checkpoint.json`, `pr2-e2e-final.txt`, `pr2-fixture-refresh.json`, `pr2-technical-archive.json`, `pr2-restore.txt` und `pr2-acceptance/runtime/restore-status.json`. Numerische und Assistant-Locks sowie alte Modellmanifeste wurden nicht verändert. Die 212 nummerierten Hauptabschnitte des Masterplans bleiben erhalten.

Die PR2-Restoreprobe enthält ausschließlich **synthetische technische** Pilot-/Experiment-/Strategiebelege: Pilot c66622d6-87db-4915-9e57-d4f2b7d9b46e ist vor Netzwerkzugriff blockiert; Protokoll 67041d9a-f0b0-40c9-93a8-093be353bfd9 registriert vier einfache Kandidaten für 30/90 Sessions, startet wegen fehlender Real-Daten keinen ML-Job; Strategie e26513f6-8eb1-4552-803c-fdd7482f406b bleibt blockiert. Die zusätzliche synthetische 90-Session-Datasetversion c76649e8-d2f7-4e07-9837-7679d8a0a609 erzeugt keine behauptete historische Modellperformance. Es existiert kein nachgewiesener realer Forward-Shadow-Track-Record und keine reife reale Outcome-Serie.

## Endstatus und verbleibende Fehler

PR2A und PR2B sind technisch funktionsfähig und getrennt dokumentiert. Alle lokalen technischen Abnahmegates sind bestanden. Keine offenen reproduzierten Implementierungsfehler aus dieser Abnahme; der Starlette-Deprecation-Hinweis bleibt bekannt. Reale Quellenrechte, Originaldaten, historische PIT-/Membership-/Action-Abdeckung sowie unabhängige OOS-/Forward-/Strategieevidenz fehlen weiterhin. Das sind ausdrückliche fachliche Sperren. Collection- und Forward-Automatik bleiben aus; der kontrollierte Assistant-Testmodus ist zurückgesetzt. Der normale lokale Stack ist wieder gesund; APP_ENV=local, ASSISTANT_TEST_MODE=false, DATA_COLLECTION_ENABLED=false und FORWARD_SHADOW_ENABLED=false wurden am laufenden API-Prozess geprüft.

## Datenbefund und Freigaben

Keine neuen rechtmäßig bereitgestellten Real-Originale. SEC, ECB, SNB, OpenFIGI, Alpha Vantage und Company IR bleiben ungeprüft/deaktiviert; MANUAL_CSV hat nur seinen bestehenden Upload-Scope, Yahoo bleibt gesperrt. Der synthetische Archiv-Audit `219e9547-cbeb-4e21-874d-09818a708c98` weist konkrete Sperren statt positiver Echt-Dateneignung aus. Acht gleichwährungsbezogene FX-Sitzungen sind keine acht Provider-Fixings. Ohne echte historische Evidenz kein reales Training, keine OOS-Ergebnisse und keine Strategieannahme.

Separate Abnahmen: [PR2A](PR2A_REAL_DATA_ACCEPTANCE_REPORT.md), [PR2B](PR2B_MODEL_VALIDATION_REPORT.md). [Verbleibende konkrete Schritte](validation/REMAINING_BLOCKERS.md).

PR2 autorisiert keine endgültige Homelab-Produktionsabnahme. Kein Push oder Release; neue Remote-CI für diese Änderungen wurde nicht ausgeführt.

Der Fixture-Refresh benötigt ausdrücklich `APP_ENV=test`, `ALLOW_SYNTHETIC_FIXTURE_REFRESH=true` und die drei bestehenden `E2E_USERNAME`-/`E2E_PORTFOLIO_ID`-/`E2E_RESEARCH_INSTRUMENT_ID`-Referenzen. Er läuft weder beim Start noch im normalen lokalen oder produktiven Betrieb.
