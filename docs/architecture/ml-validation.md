# P7: Zeitliche Validierung

Vier streng getrennte Fenster: TRAIN, VALIDATION, CALIBRATION, TEST. Jede Grenze hat mindestens den Target-Horizont an tatsächlichen Börsensessions Embargo. Ein früheres Label muss vor dem nächsten Embargo vollständig realisiert und lokal verfügbar sein. `signal < label_start < label_end <= label_available_at` wird geprüft. Random Splits sind nicht konfigurierbar. OOS-Fenster verschiedener Folds dürfen sich nicht überschneiden.

Classification: ROC-AUC, Average Precision (PR-AUC), Precision, Recall, F1, Brier, zehn gleichbreite ECE-Bins und Confusion Matrix. Ein-Klassen-AUC bleibt null. Regression: MAE, RMSE, Bias, Pearson/Spearman; konstante Reihen erhalten keine erfundene Korrelation.

Constant 50 %, TRAIN-Klassenprävalenz, Zero Return und historische TRAIN-Mittelwerte werden auf identischen Testlabels verglichen. Investierbare Baselines und Modell-Scores durchlaufen dieselbe P6-Engine, denselben Zeitraum, Next-Open und dieselben Kosten. Modell-Scores sind getrennte OOS-Signale; gespeicherte Features oder Finanzdaten werden nicht verändert.

Moving-Block-Bootstrap gruppiert Instrumente nach Signaldatum und verwendet horizonlange Datumsblöcke. Unter zehn vollständigen Blöcken bleibt Unsicherheit unavailable. 200 Wiederholungen, fester Seed, 95-%-Intervall. Überlappende Aktienlabels sind keine unabhängigen Fälle. Ein statistischer Vorteil allein beweist keine handelbare Profitabilität.
