# PR2B – Model & Strategy Validation

Stand: 19.10.2026. **BLOCKED_BY_REAL_DATA · V2 FORECASTS NOT VALIDATED · V3 RECOMMENDATIONS GATED.**

**PR2B TECHNICAL FUNCTIONAL – technisch abgenommen.** 257 Backendtests, 20 Browserfälle und isolierter Restore bestanden. Es wurden keine realen Modelle oder Strategien validiert.

## Voraussetzungen und geprüfte Architektur

PR2A wurde zuerst separat als durch Quellenfreigaben blockierter technischer Zwischenstand dokumentiert. Es liegen keine neuen freigegebenen Originaldaten für einen echten Pilotbestand vor. PR2B verwendet daher die zulässige Alternative des Auftrags: technische Infrastruktur umsetzen und testen, fachliche Validierung sperren.

P7 behält Train-only Preprocessing, Purged Walk-Forward, tatsächliche Label-Purges, Session-Embargo, separate Calibration, Baselines, Conformal-Intervalle, MLflow, Artefakt- und Promotion-Prüfungen. P6 bleibt Dataset-/Ausführungsquelle; P9 bleibt die einzige Recommendation Engine. Numerische/Assistant-Locks, alte Dataset-Hashes und Modellmanifeste wurden nicht migriert oder abgeschwächt.

## Umgesetzt

- Append-only Experimentregistrierung für beide Horizonte, Classification/Excess Return, Logistic/Linear und optionale bestehende komplexere Modelle. Parametergrid, Kosten, Features, Zeitfenster, Metriken, Quellenpolitik und Code werden vorab gepinnt. Bereits exponierte oder reservierte finale OOS-Fenster bleiben gesperrt.
- Real-Readiness vor jedem PR2-Trainingsstart; blockierte Kandidaten erzeugen keinen ML-Job. Wiederaufnahme bindet vorhandene P7-Runs an den registrierten Auftrag. Vergleiche prüfen Artefakt, Dataset und bestehende Promotion-Gates.
- Finanzvergleich über P6 einschließlich Cash-/No-Change-Baseline und expliziter FX-Ausführungskosten. Behoben: fehlendes Quality-Payload im bisherigen P7-Finanzpfad. Kosten werden nicht doppelt vom Cash abgezogen; bestehende Requests behalten ihre bisherigen Defaults.
- Registrierte Regime-Regeln verwenden ausschließlich gepinnte Features. Fehlende Benchmark-/Makro-/Volatilitätsbelege bleiben unbekannt. Keine Regimeklassifikation anhand späterer Renditen.
- Kontrollierte aktuelle SHADOW-Prognosen über die bestehende P7-Pipeline. Keine Rückdatierung oder automatische Quellenaktivierung. Fehlende reale Evidenz führt zu dauerhafter Abstention.
- Persistente Policy-Zeitpläne, Wiederanlauf-/Sitzungsdeduplizierung, Outcomes mit tatsächlicher Reife und versionierten Korrekturen, paginierte Historie und begrenztes Forschungsmonitoring. Globale Automatik bleibt standardmäßig aus.
- P9-Strategieprüfung bindet Portfolio und Dataset, sperrt synthetische Herkunft, erhält historische Replay-/Forecast-/Risiko-/Operator-Gates. Kein Trading, keine Strategie- oder Modellpromotion.
- Ansichten für Model comparison, Forward Shadow History und Strategy evaluation; Source-Arbeitsnotizen vergeben keine Rechte.

## Tatsächliche Ergebnisse

Keine reale OOS-Auswertung durchgeführt. Keine belastbare Classification-, Regression-, Calibration-, Intervall-, Regime- oder Netto-Alpha-Aussage verfügbar. Keine reale gereifte Forward-Historie nachgewiesen. Werte bleiben nicht verfügbar; technische Fixtures werden nicht als Anlageergebnisse ausgegeben.

Die unveränderten Mindestgates (u. a. 1.000 Training, 500 OOS, 600 verschiedene OOS-Signaltage, drei Folds) sowie alle zusätzlichen Baseline-, Calibration-, Intervall-, Stability-, Finanz- und Review-Gates bleiben verpflichtend. `SHADOW` und `NO RELIABLE FORECAST` sind zulässige fachliche Ergebnisse.

Technische Abschlussnachweise stehen gesammelt im [PR2-Gesamtbericht](PR2_ACCEPTANCE_REPORT.md). Detaillierte Verträge: [Experiment](validation/ML_EXPERIMENT_PROTOCOL.md), [OOS](validation/OOS_MODEL_RESULTS.md), [Forward](validation/FORWARD_SHADOW_PROTOCOL.md), [Strategie](validation/STRATEGY_EVALUATION.md).

Die technische Restaurationsprobe registriert unter `67041d9a-f0b0-40c9-93a8-093be353bfd9` vier einfache Kandidaten auf ausdrücklich synthetischen 30-/90-Session-Datasets. Queue bleibt `EXPERIMENT_BLOCKED`; Vergleich `53d75d5a-b57a-427c-b6d7-b8fb7fc2fdfb` enthält `NOT_RUN` und keine Modellmetriken. Strategie `e26513f6-8eb1-4552-803c-fdd7482f406b` bleibt `BLOCKED_BY_REAL_DATA` mit `metrics: null`. Diese Protokolle wurden zusammen mit den bestehenden P7/P8/P9/P10-Historien exakt restauriert. 26 vorhandene P7-Archiveinträge und null Outcomes sind kein realer Forward-Track-Record. Keine zusätzliche künstliche SHADOW-Modellartefaktdatei wurde für eine positive Abnahme erzeugt.

## Offene Abnahme

Reale Rechte/Daten/PIT-/Membership-/Action-Coverage fehlen. Nach Beschaffung neuer Evidenz sind neue unveränderliche Audits und Experimente erforderlich. Bestehende blockierte Berichte werden nicht umgedeutet. Keine PRODUCTION-Promotion, keine echten Empfehlungen und keine V3+-Zielinstallation freigegeben. Abschließende Homelab-Abnahme folgt separat nach PR2.
