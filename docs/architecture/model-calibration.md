# P7: Kalibrierung und Intervalle

Platt Scaling lernt ausschließlich im getrennten Calibration Window. Begrenzte Logits und logistische Regression; mindestens 100 Beobachtungen und 20 je Klasse, andernfalls `CALIBRATION_UNAVAILABLE`. TEST wird nach abgeschlossener Kalibrierung ausgewertet. Brier, ECE und Bin-Beobachtungen bleiben sichtbar.

Regression verwendet ein 80-%-Split-Conformal-Intervall aus absoluten Calibration-Residuen. Gleichzeitige Instrumente werden je Datum zusammengefasst; nur horizonweise auseinanderliegende Daten werden ausgewählt. Maximale Residuen je ausgewähltem Datum und Rang `ceil((n+1)*.8)` bestimmen den Radius. Mindestens 30 Datumsblöcke; andernfalls `INTERVAL_UNAVAILABLE`.

Calibration- und OOS-Coverage werden getrennt ausgewiesen. Finanzmärkte erfüllen nicht automatisch Stationarität/Austauschbarkeit; keine bedingungslose Coverage-Garantie. Normale Forecasts verlangen freigegebene Classification und Excess-Return-Regression für dasselbe Dataset und denselben Horizont.
