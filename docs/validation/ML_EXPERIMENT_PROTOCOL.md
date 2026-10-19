# Unveränderlicher Experimentvertrag

PR2 verwendet P7-Training, MLflow, Registry und P6-Replay. Es existiert keine zweite Trainingspipeline. Vor Auswertung werden beide Horizonte (30/90 Handelssitzungen), Classification und Excess Return, Datensatz, Features, Seed, Suchkomplexitäten, Kosten, Folds, Quellenpolitik und Hypothese registriert. Logistic und Linear sind je Horizont erforderlich; komplexere vorhandene Modelle sind optionale zusätzliche Kandidaten.

Train/Validation/Calibration/finales OOS sind chronologisch. Purging und Embargo verwenden tatsächliche Label-Verfügbarkeit und Sessions; Embargo mindestens der Horizont. Keine Random-Shuffle-Validierung, keine Anpassung anhand finaler OOS-Ergebnisse. Reservierte oder zuvor ausgewertete finale Fenster desselben Universums/Horizonts können auch nach Erstellen einer neuen Dataset-Version nicht in einer neuen Registrierung wiederverwendet werden. Eine Kopie des Universums schafft keinen wissenschaftlich unberührten Test; Operatoren dürfen diese Herkunft nicht verschleiern. Maximal zwölf Kandidaten, fünf Folds und 1.000 Protokolle je Benutzer; Kapazitätsgrenzen sperren weitere Registrierung konservativ.

Registrierung pinnt Implementierung, Parametergrid, bestehende Promotion-Regeln und Baselines. Queue und Vergleich verlangen denselben Code-Manifeststand. Dateneignung wird vor Queue erneut geprüft. Ein blockierter Kandidat erzeugt einen Bericht, keinen Trainingsjob. Abbruch nach P7-Queue-Persistenz wird über Run-Konfiguration und Protokollbindung wiederaufgenommen.

Classification: Brier, ECE, ROC/PR-AUC, Precision, Recall, F1, Balance und Kalibrierungskurve. Regression: MAE, RMSE, Bias, Pearson und Spearman. P7 liefert Intervallniveau und empirische OOS-Coverage; keine erfundenen Unsicherheitsbänder. Model Cards binden Artefakt/Dataset, Features, Zeitfenster, Evaluation und bekannte Ausfallgründe.

Finanzielle Vergleiche laufen durch P6: Modell, No Change (explizit Cash), Benchmark, Equal Weight, Momentum und Quality/Value. Neue Trainingsaufträge pinnen Commission sowie Spread-, Slippage- und FX-Kosten. Historische Backtest-Requests behalten FX-Kosten-Default 0; alte Artefakte werden nicht neu geschrieben. Ausführung nach Signal, echte FX-Verfügbarkeit, Corporate Actions und Cash bleiben verpflichtend.

Regime-Regeln werden vorab als Schwellen auf gepinnten Benchmark-, Volatilitäts- oder Makrofeatures definiert. Fehlendes Feature bedeutet unbekanntes Regime. Mindestens 50 Beobachtungen und 30 Signaltage je Regel; fehlende der sechs Regime verhindern umfassende Robustheitsaussagen. Zeitlich korrelierte Beobachtungen sind keine unabhängigen Stichproben.

Keine automatische Promotion. Quantitative Kriterien plus bestehende Operator-Reviews bleiben nötig. Numerische und Assistant-Dependency-Locks bleiben unverändert.
