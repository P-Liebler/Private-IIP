# P7 — KI-Prognosen und technische V2-Abnahme

**Stand:** 2026-10-14. **Start:** `main`, `552e96b106903422d4d07a5e4eb5ba1e56873878`. Normativ: Masterplan 85–103, 157–158 und 208–210. P9/P10 wurden nicht begonnen.

## Status

| Bereich | Ergebnis |
| --- | --- |
| Technische Implementierung | **P7 FUNCTIONAL — MODELS SHADOW / DATA LIMITED** |
| Modell-Promotion | Keine produktive Freigabe |
| V2-Prognoseprodukt | **NOT VALIDATED** |
| Reale Zielinstallation | Bestehende P4-Gates bleiben offen |

Diese Zwischenabnahme erlaubt den angeforderten Beginn von P8; ein freigegebenes P7-Modell ist dafür nicht erforderlich.

## Ausgangslage und Datenbereitschaft

Lokaler und entfernter Main-Head stimmten überein; Ausgangsverzeichnis sauber. Baseline erneut: **113 Backend- und 6 Browser-Tests bestanden**. Der Ausgangsauftrag meldet erfolgreiche GitHub Actions; die unabhängige Commit-Workflow-Abfrage lieferte keine Runs. Die neuen Änderungen wurden nicht gepusht: **REMOTE CI NOT VERIFIED**.

Die ursprüngliche P6-Simulation `a4c9d4ff-07de-44d0-a89b-53e843648994` hat vier Beobachtungen, null geeignete Trainingszeilen und vier fehlende 30-Session-Labels. Erforderliche Momentum-/Volatilitätsfeatures fehlen. Ihr unveränderlicher Replay besteht; das ist kein reales historisches Archiv. `P7DataReadinessService` prüft gepinnte Originalbytes, Canonical-/Feature-Inhalte, Snapshot-Instrument, Cutoffs, fehlende Pflichtfeatures und Labelintervalle. Die Zustände STRICT_PIT_ELIGIBLE, RECONSTRUCTED_RESEARCH_ONLY, INSUFFICIENT_HISTORY und DATA_QUALITY_FAILED sind getrennt; synthetische Evidenz kann nie `production_data_eligible` werden.

Mehrjährige Daten entstehen aus zwei bis acht originalen, angrenzenden P6-Fenstern. Höchstens 30'000 Zeilen/16 Jahre, identische Versions-/Kalender-/Currency-/Universe-Policies; keine verschachtelten Fenster, Lücken, Überschneidungen oder heutigen Neuabfragen. Der P6-Content-Hash bleibt erhalten. Target-Vertrag v2 ergänzt insbesondere Wissen/Reviews der täglichen FX-Beobachtungen im Volatilitätslabel; ältere v1-Artefakte werden nicht umgeschrieben.

## Training, Evaluation und Unsicherheit

Unterstützt: Logistic Regression, Linear Regression, LightGBM Classifier/Regressor und XGBoost Classifier/Regressor. Lokale CPU-Dependencies: scikit-learn 1.9.1, LightGBM 4.7.0, XGBoost CPU 3.4.1 mit gepinnten NumPy/SciPy und Dependency-Locks. MLflow 3.17.1 hat einen eigenen Lock und startet nur im Profil `ml`. Keine GPU, bezahlte API oder Cloud ist erforderlich.

Vier zeitliche Fenster mit mindestens horizonlangem Börsensession-Embargo und tatsächlichem Label-Purge. Keine Random-Splits. Skalierung, optionale Median-Imputation, Missing-Flags und Entfernen konstanter Features lernen ausschließlich TRAIN. Finanzielle Pflichtfeatures bleiben Hard-Gates. Begrenzte deterministische Komplexitätssuche verwendet einen zusätzlichen gepurgten TRAIN-Holdout; äußere Validation/Calibration/Test beeinflussen diese Auswahl nicht. Configuration, Seed, Source-/Dependency-Hash, Search-Ergebnisse und Hyperparameter sind versioniert. Jobzeiten dokumentieren die tatsächliche Dauer.

Classification-Metriken: ROC-/PR-AUC, Precision/Recall/F1, Brier, ECE, Klassenverteilung und Confusion Matrix. Regression: MAE/RMSE/Bias/Pearson/Spearman. Konstant-/Prävalenz- und Zero-/TRAIN-Mean-Baselines verwenden identische Labels. Finanzielle OOS-Scores und Benchmark/Equal-Weight/Momentum/Quality-Value werden über dieselbe P6-Engine mit Next-Open und Kosten geprüft; unavailable/No-Fill-Ergebnisse bestehen kein Gate.

Platt Scaling hat ein getrenntes Calibration Window. Conformal-Intervalle benötigen mindestens 30 nicht überlappende Calibration-Datumsblöcke. Unter unzureichender Historie bleiben Kalibrierung beziehungsweise Intervalle unavailable. Empirische Coverage ersetzt keine Stationaritäts-/Austauschbarkeitsannahme. Date-Cluster und Moving-Block-Bootstrap vermeiden eine behauptete Unabhängigkeit gleichzeitiger Aktienlabels.

## Tatsächlich ausgeführte Trainingssimulation

Der vollständige Celery-Lauf `77caf0ff-9934-4bbb-bcf2-5d3474c4b9c2` endete COMPLETED. Modell `678d4cd7-776b-4183-bbb6-18a0b4a0b506` bleibt **SHADOW**. Das ausdrücklich synthetische Kernel-Dataset enthält keine handelbare Marktserie; sein Kosten-Backtest ist absichtlich unavailable. Diese Simulation testet Training/Registry/Storage, keine reale finanzielle Güte.

Synthetische OOS-Evaluation: 502 Beobachtungen, ROC-/PR-AUC 1, Brier 0.0000674029, ECE 0.00264394. Die konstruierten Testlabels erklären diese Werte; sie sind **keine reale Aktienprognoseleistung**. Keine historischen Marktperioden oder echten OOS-Ergebnisse werden erfunden.

Offene Promotion-Gates dieses Modells: reale strenge Historie, synthetische Evidenz, zu wenige OOS-Signaldaten/Folds, fehlender Kosten-Backtest, Model Card und UNVERIFIED_CODE. Vorab definierte `p7-conservative-promotion-v1`-Schwellen verlangen unter anderem 1000 TRAIN-/500 OOS-Zeilen, 600 unterschiedliche OOS-Daten, drei Folds, mindestens 2 % Baseline-Verbesserung, ECE ≤ .05, passende Intervall-Coverage .75–.95 und stabile Perioden. Ein Operator kann diese Schranken nicht überstimmen. Bestehende Champions müssen bei vergleichbaren Daten mindestens erreicht werden.

## Registry, Vorhersagen, Sicherheit und Monitoring

`0013_ml_registry` ergänzt fünf Tabellen: ml_training_runs, ml_model_versions, model_promotion_reviews, predictions und prediction_outcomes. Die vier historischen Artefakttabellen weisen UPDATE zurück; Jobs behalten kontrollierte Statuswechsel. Eigene Modellzustände EXPERIMENT/VALIDATION/SHADOW/PRODUCTION/RETIRED entstehen über separate Reviews. Username-Allowlist plus Ownership schützen Administration. Artefakte sind intern erzeugtes JSON/native Tree-Formate, mit SHA-/Konfigurations-/Dependency-Prüfung; keine fremden Pickles oder beliebige Code-Ausführung.

MLflow: Basic Auth, keine Hostports, ein Worker, PostgreSQL-Schemas iip_mlflow/iip_mlflow_auth und MinIO-Artefakte. Parameter/Metriken/Artefakte und challenger/champion-Aliases sind integriert; Application-Status bleibt maßgeblich. Telemetrie ist deaktiviert. Authentifizierter Artifact-Upload/Download und Hashvergleich bestanden.

Predictions einschließlich NO RELIABLE FORECAST bleiben append-only. Die normale Instrumentseite verlangt freigegebene Classification/Excess-Return-Modelle; aktuelle Membership, Actions und Pflichtfeatures werden erneut geprüft. Calibration-Support und finite Ausgabegrenzen verhindern ungeprüfte Zahlen. Zusätzliche Return-/Volatilitätsmodelle können separat verfügbare Werte liefern. Native Tree-SHAP beziehungsweise lineare Beiträge erklären Faktoren ohne Kausalbehauptung. Outcomes entstehen erst nach vollständiger Realisierung; Korrekturen bleiben separate Versionen. Aktuelle echte Outcomes fehlen, weil keine reale Prognose freigegeben wurde.

Geschützte Readiness/Composition, Training-/Cancel-/Run-, Model-/Review-/Evaluation-/Monitoring- und Forecast-/History-/Outcome-APIs sind vorhanden. `/models` und die Instrumentseite zeigen tatsächliche Backend-Ergebnisse. Monitoring erfasst Jobs, Abstention/Fehler, Status, Missingness/Freshness und realisierte Kalibrierung. Erhebliche Drift erzeugt SHADOW; automatische Rückkehr zu PRODUCTION ist gesperrt. Kein Broker, keine echten Orders, kein Assistent.

## Technische Nachweise

| Prüfung | Ergebnis |
| --- | --- |
| Backend-Gesamtregression | **142 bestanden**, eine bekannte upstream Starlette-Warnung |
| Browser-Gesamtregression | **8 bestanden** in einem vollständigen Lauf |
| Ruff/Format/Mypy | Bestanden; gezielte Checks nach letzten Vertragskorrekturen |
| Frontend lint/typecheck/build | Bestanden; geschützte `/models`-Route gebaut |
| Bestehende/frische Migrationen | Head 0013; **46 erforderliche Tabellen**, Alembic driftfrei |
| Modell-/Leakage-/Kalibrierungs-Goldens | Sechs reproduzierbare Estimatoren, Train-only Preprocessing, getrennte Fenster, Embargo/Future-Labels, synthetische Promotion gesperrt |
| Auth/Immutability | Fremde Model-/Job-/Prediction-IDs geschützt; UPDATE abgewiesen |
| Outcome-Golden | Unreife Labels unavailable; falsche Prognose bleibt erhalten |
| Celery/MinIO | Smoke und vollständiger synthetischer Trainingsjob bestanden |
| MLflow-Ausfall | Dienst gestoppt: Research erreichbar und Golden-Portfolio exakt CHF 10'180 |
| Isolierter Restore | **PASSED**, siehe unten |

Der Browsertest erkannte einen Literal-Query-Fehler (`horizon=30` als Text); beide Query-Verträge wurden korrigiert und mit echtem Parameter getestet. Kaltstart-Wartebedingungen wurden explizit gemacht; der abschließende vollständige Browserlauf bestand.

## Recovery

Backup `backups/p7-acceptance/sets/20261014T083212Z-66788`. Isolierter Restore bestand am 2026-10-14 (08:35–08:39 UTC): Head 0013, Original-Raw-Hash, gepinnter P6- und P7-Dataset-Replay, Application-/MLflow-Modellartefakt-SHA, MLflow-Run-Metadaten, vollständiger Prediction-/Outcome-History-Hash, Login und **CHF 10'180**. Drei gespeicherte Ablehnungen und null reale Outcomes wurden exakt erhalten. Temporäre Restore-Instanz wurde entfernt.

Artefakthash: `9706d2dc2631d0cfde24ddaad3ccd4f41b686351cd5b82ecd5e0a96fc18f5c94`. Prediction-History-Hash: `9b5b753f8ac1f2168576b86588d24df4f67f7591014039560080590c0b65aa9e`. Backup/Testartefakte bleiben lokal und Git-ignoriert. Diese Prüfung ersetzt keine echte Produktionssicherung, Schlüssel-Recovery oder VPN-/CA-Abnahme.

## Grenzen und nächster Schritt

Keine vollständige reale PIT-/Delisting-/Action-/FX-Historie; keine echte Forecast-Promotion. Statistische Simulationen bleiben sichtbar getrennt. Unsicherheit ist empirisch und bei kleinen Stichproben unavailable. FX/Kosten verwenden die bestehenden täglichen Referenzregeln, kein Orderbuch. P4-Zielgates und alle nicht genehmigten Quellen bleiben gesperrt. **P8 beginnt nach dieser technischen Zwischenabnahme; P9/P10 bleiben gesperrt.**
