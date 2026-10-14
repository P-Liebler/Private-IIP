# P8 — Portfolio Risk, Szenarien und V2.5-Abnahme

**Stand:** 2026-10-14. Ausgangscommit: `552e96b106903422d4d07a5e4eb5ba1e56873878`. Normativ: Masterplan, insbesondere Risiko-/Szenarioabschnitte und einheitliche Roadmap. [P7 wurde vor Beginn von P8 separat technisch abgenommen](P7_ACCEPTANCE_REPORT.md).

## Getrennte Status

| Bereich | Ergebnis |
| --- | --- |
| TECHNICAL STATUS | **P8 FUNCTIONAL — RISK DATA LIMITED** |
| RISK DATA STATUS | Aktuelle belegte Bewertung/Exposure verfügbar; vollständige reale Kalender-/Action-/Return-Historie des Referenzportfolios fehlt |
| V2.5 DEPLOYMENT STATUS | **NOT RELEASED** — Homelab/VPN, echte Client-CA-Vertrauensprüfung, unabhängiger Backup-Mount, realer Host-Backupplan und Schlüssel-Recovery bleiben offen |
| P7-Modellstatus | SHADOW; keine reale Produktionsfreigabe; **V2 NOT VALIDATED** |
| Remote CI | **NOT VERIFIED** — Änderungen nicht gepusht |

P9 und P10 wurden nicht implementiert. Kein Broker, keine echten Orders und keine autonomen Empfehlungen. Keine externe Finanzquelle wurde aktiviert oder live abgefragt. Alle finanzielle Testwerte sind ausdrücklich synthetische lokale Fixtures.

## Lieferung

- `PortfolioRiskService`: tägliche P4-Ledger-TWR mit exakten externen Flows, anschließende Referenzkalender-Aggregation, geprüfte Kurse/FX/Actions und historische Hard-Gates. Keine Auffüllung offener Börsentage; Closed-Market-Marks sind ausdrücklich geregelt.
- Stichprobenvolatilität × √252, matched Beta, vollständiger EOD-Drawdown mit Peak/Tief, historischer Type-7-VaR 95%, tatsächlicher Tail-CVaR, Korrelationen über exakt 30/90/252 Referenzperioden mit Zell-Stichproben.
- Über Accounts zusammengeführte Instrumentkonzentration, Largest/Top-3/Top-5/HHI sowie Sektor/Industrie/Land/Handelswährung mit UNKNOWN. Netto-FX berücksichtigt Wertpapiere und negative Cashbestände. Wirtschaftliche Umsatzwährung bleibt ohne Belege unverfügbar.
- Versionierte Health-Rubrik für Diversification, Concentration, Volatility, vollständige P5 Quality, Accounting-Currency-Exposure und einen belegten 20-Session-Volumen-Liquiditätsproxy. Alle Eingaben/Gewichte/Gates sichtbar; kein Gesamtscore verdeckt Lücken. Der Proxy behauptet weder Spreads noch Ausführbarkeit.
- Sieben v1-Szenariodefinitionen; getrennte direkte Positions-, Currency-Translation-, Beta-Markt- und reine Risikoparameter-Schocks. Benutzerbestätigte Benchmark-Proxies müssen zur tatsächlichen Snapshot-Benchmark-ID passen; unmodellierte Positionen bleiben sichtbar, vollständige Impact-NAV bleibt bei Teilabdeckung null. Freie Positions-/FX-Schocks vorhanden.
- Reiner What-if-Kernel: kopierte Bestände, explizite Gebühren/Spread/Slippage, Cash-/FX-/Quantity-Gates, positive NAV, keine Shorts/impliziten Kredite und keine Ledger-Mutation. Allocation, Kosten, Health, Korrelationen und Szenarien vorher/nachher. Hypothetische historische Kennzahlen verwenden ausdrücklich konstante vorgeschlagene Gewichte auf gepinnter Historie; keine behauptete tatsächliche Performance. Unberechnete Accounting-PnL/Cost-Basis wird null.
- Vier unveränderliche Tabellen in `0014_portfolio_risk`: risk_snapshots, scenario_definitions, scenario_runs, what_if_runs. Canonical-Inhaltshashes, Raw-Hashes, Parent-/Resultat-/Konfigurationshashes; spätere Korrekturen erzeugen neue Records.
- User-owned APIs für Risiko, paginierte History, Einzelresultate, Correlations/Exposures, Szenarien und What-if. Kleine History-Zusammenfassungen verhindern das Laden von 100 vollständigen wissenschaftlichen Payloads. Maximal 30 Instrumente, 252 Sessions, 20 Trades, globale Rechenlocks, 120 Sekunden Timeout; keine MLflow-/LLM-Abhängigkeit.
- Portfolio-Tabs Risiko, Korrelationen, Szenarien und What-if. Alle Zahlen stammen aus den Backendresultaten. Snapshot-Auswahl, fehlende Daten, Subscore-Grundlagen, Teilwirkungen, pro-forma-Vergleich und Kosten sind sichtbar.

Formeln und Grenzen: [Portfolio Risk](architecture/portfolio-risk.md), [Szenarien](architecture/scenarios.md), [What-if](architecture/what-if.md). Architekturentscheidungen: ADR-018 und ADR-019. Die sechs P7-Architekturdokumente bleiben gültig.

## Messbare Abnahme

| Prüfung | Nachweis |
| --- | --- |
| Backend-Gesamtregression | **155 Tests bestanden**; bekannte upstream Starlette/httpx-Deprecation, kein Fehler |
| Änderungen nach Gesamtregression | Betroffene What-if-/API-/Accounting-Goldens zusätzlich bestanden; abschließender 9-Test-Kernel-Lauf bestanden |
| Browser-Gesamtregression | **10 Tests bestanden**, letzter voller Lauf 2.8 Minuten; P4/P5/P6/P7 sowie Risiko-/What-if-Flows |
| Frontend | Lint ohne Warnungen, Typecheck und finaler Production-Build bestanden |
| Backendqualität | Ruff, Format und Mypy bestanden (138 App-Quelldateien); kein Schema-Drift |
| Migrationen | Upgrade bestehend und vollständig frisch bis **0014**, **50 erforderliche Tabellen**; 0001–0012 unverändert |
| Risiko-Goldens | std/Beta, anfänglicher Drawdown-Peak, VaR .11345 und CVaR .120 bei 13 echten Tail-Werten der synthetischen Testreihe; konstante/zu kurze/gappige Reihen unavailable |
| Actions/FX/Kalender | Raw-Split/Dividend mit einmaliger FX-Umrechnung, kein Adjusted-Close-Doppelzählen; fehlender offener Kurs und fehlende Coverage sperren Returns; geschlossenes US-Marktmark mit tatsächlichem FX |
| Exposure/Szenarien | Account-Aggregation/UNKNOWN; Beta-/Sektor-Lücken, parameter-only Volatilität, direkter Schock und negative FX-Cashbestände |
| What-if | Kauf/Verkauf, Kosten, keine fehlenden Quotes/FX/Überverkäufe/Cashüberschreitungen, konsistente NAV/Weights, JSON-History-Beta und unveränderter realer Ledger |
| Ownership/Immutability | 401/404, Future-as-of 422, UPDATE-Trigger; alte Risikoantwort bleibt nach akzeptierter Kurskorrektur identisch |
| Celery/MinIO | Tatsächliche Smoke-Aufgabe und Object-Roundtrip bestanden; P7 echter synthetischer ML-Worker-Lauf separat nachgewiesen |
| Monitoring | P8-Metrik-Exposition geprüft; promtool: **9 Alarmregeln gültig**; Grafana-Konfiguration erweitert, tatsächliche Alarmzustellung bleibt Deployment-Gate |
| MLflow-Ausfall | Server vollständig gestoppt: Research und Risiko verfügbar, reales Test-Ledger-NAV weiterhin exakt **CHF 10'180**; Server danach wieder gestartet |
| Backup/Restore | **Isolated restore PASSED**, einschließlich Modell/Datasets, Prognosen, Risiko/Szenario/What-if und CHF 10'180 |

Die 13 zusätzlichen P8-Tests bestehen aus neun Statistik-/Exposure-/What-if-Goldens, drei Markt-/Kalender-/Liquiditäts-Goldens und einem vollständigen lokalen API-/Datenbankflow. Keine Tests rufen reale Finanzprovider auf.

## Konkrete Ergebnisse und Datenlücken

Referenzportfolio: CHF 10'000 Einzahlung, 10 USD-Aktien zu 100, akzeptierter Close 120 und USD/CHF .9. Sein P4-Ledger enthält USD-Cash −1'000. Daher: Wertpapiere CHF 1'080 + USD-Cash CHF −900 + CHF-Cash 10'000 = **CHF 10'180**.

USD/CHF −10% verändert dieses Netto-USD-Exposure um **CHF −18**, resultierende NAV CHF 10'162. Der Browser prüft außerdem einen expliziten −25%-Positionsschock von CHF −270. Ein hypothetischer Kauf über CHF 100 kostet bei Defaultkosten CHF 1.10; hypothetische NAV CHF 10'178.90. Die tatsächlichen Transaktionen und tatsächliche NAV bleiben identisch.

Die Börse dieses lokalen Referenzinstruments ist unbekannt. Es wird keine NYSE-Zuordnung erfunden. Deshalb fehlen validierte historische Portfolio-Returns, Volatilität, Beta, Drawdown, VaR/CVaR und Korrelationen in dieser Fixture korrekt. Aktuelle Exposure, Konzentration und direkte FX-/Positionshypothesen bleiben belegbar. Historische Kennzahlen sind separat mit ausdrücklich synthetischen Goldens geprüft; das beweist keine vollständige reale Datenhistorie. P7-Abstentionen bleiben unverändert sichtbar.

## Restore-Evidenz

Backup: `backups/p8-acceptance/sets/20261014T113054Z-63548`.

Isolierter Restore: **2026-10-14 11:32:51–11:34:57 UTC**, `success=true`. Neue getrennte PostgreSQL-/MinIO-Instanzen ohne Hostports; temporäres Projekt mit Volumes anschließend entfernt. Geprüft: Alembic 0014, Raw-SHA, unveränderlicher P6-Dataset-Replay, P7-Modell und dessen Dataset/MLflow-Run/Artefaktkopie, exakte Prediction-/Outcome-History, alle Risiko-/Szenario-/What-if-Records samt Parent-/Canonical-/Raw-Hashes, Login und **CHF 10'180**.

- Modellartefakt-SHA: `9706d2dc2631d0cfde24ddaad3ccd4f41b686351cd5b82ecd5e0a96fc18f5c94`.
- Prediction-History-SHA: `9b5b753f8ac1f2168576b86588d24df4f67f7591014039560080590c0b65aa9e` — drei Abstentionen, null reale Outcomes.
- Risk-History-SHA: `ee85672d31897bf1075a6c70f1488bdcda2404c7995cac6cf035cb54ba077361` — vier Risiko-Snapshots, drei Szenarien, zwei What-if-Läufe.

Backup-/Restore-Artefakte bleiben lokal und Git-ignoriert. Keine realen Passwörter oder Secrets wurden in Berichte aufgenommen.

## Verbleibende Gates

Reale historische Completeness/PIT-Evidenz und Modellfreigabe fehlen weiterhin. Yahoo bleibt BLOCKED/deaktiviert; übrige ungenehmigte Live-Quellen bleiben UNKNOWN/deaktiviert. Nur ausdrücklich bezeichnete lokale Testquellen sind freigegeben. Mandatory paid API/cloud: keine. Hardware und Betrieb bleiben separate Kosten.

Technische P7/P8-Abnahme ist abgeschlossen. **V2 bleibt NOT VALIDATED, V2.5 bleibt NOT RELEASED. STOP BEFORE P9.**
