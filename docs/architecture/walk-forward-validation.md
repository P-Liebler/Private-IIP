# Purged Walk-Forward

P6. `WalkForwardSplitter` verwendet geordnete Zeitfenster und tatsächliche Labelintervalle. Kein Shuffle. Training vor Validation vor finalem Test; letzter Test ist kein Parameterselektionsbereich. Unbeendete oder noch nicht verfügbare Labels sind nicht zugelassen.

Embargo ist mindestens der größte verwendete Target-Horizont. Die Grenze wird mit dem instrumentbezogenen gepinnten Kalender um N Sessions zurückgerechnet und geprüft. Sowohl vor Validation als auch vor Test gilt das konservative Embargo. Training-/Validation-Beispiele werden entfernt, wenn Label-Ende oder Label-Availability die jeweilige Sicherheitsgrenze erreichen/überschreiten. Grenzgleichheit ist ausgeschlossen; finale verfügbare Testlabels dürfen am final_end enden.

`POST /datasets/{id}/splits` speichert Configuration, Partitionen, Purge-Ergebnisse, Policy und Content-Hash. Mehrere Exchanges werden pro Instrument behandelt. No-Skill 0.5 und Zero Excess Return sind fest definierte Referenzmodelle. Prävalenz und historischer Mittelwert werden ausschließlich aus den resultierenden Trainingszeilen und vor deren Trainingscutoff verfügbaren Labels geschätzt. Fehlende Trainingslabels ergeben null, keine erfundene Prävalenz. Kein P7-Modelltraining oder Kalibrator.
