# P7: Konservative Freigabe

`p7-conservative-promotion-v1` steht vor der Testauswertung fest. Gemeinsam erforderlich: reale strenge PIT-Belege, keine synthetischen Daten, 1000 TRAIN- und 500 OOS-Beobachtungen, 600 unterschiedliche OOS-Signaldaten, drei nicht überlappende Folds, Leakage-Audit, mindestens 2 % Verbesserung gegenüber passenden statistischen Baselines, bestandene Kosten-Backtests, stabile Fold-Verluste (Ratio höchstens 2), geprüfte Artefakte, belegter Codecommit und dokumentierte Model Card.

Classification: Platt-Kalibrierung und OOS-ECE höchstens .05. Regression: OOS-Intervall-Coverage zwischen .75 und .95. Nicht auf einen Targettyp anwendbare Gates ersetzen keine komplementären Forecast-Modelle. Operatoren können fehlende Daten nicht durch Scores oder veränderte Schwellen überstimmen.

Keine aktuelle reale historische Datenfreigabe. Die bekannte vier-Session-Simulation besitzt keine vollständigen 30-/90-Labels. `NO RELIABLE FORECAST` bleibt zulässig. P8 darf nach technischer P7-Abnahme unabhängig vom Modellgate beginnen.
