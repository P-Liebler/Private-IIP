# P7: Unveränderliche Prognosen

Predictions und Ablehnungen sind nutzergebunden und append-only. Zeit, Cutoff, Instrument, Horizont, Modell/Dataset/Feature-Snapshot und Ergebnis bleiben erhalten; DB weist UPDATE zurück. Fehlende Freigabe, Pflichtfeatures, Action Coverage oder Artefakte erzeugen `NO RELIABLE FORECAST`.

Die normale UI zeigt nur freigegebene Forecasts. Experimente liegen unter `/models`. Lineare Faktoren sind Modell-Assoziationen auf transformierten Features, keine Kausalbehauptungen.

Outcomes verwenden den P6-Target-Vertrag: Entry nächster Open, 30/90 Sessions, rohe Preise plus Actions, belegte FX und Verfügbarkeit. Unvollständige Fenster haben keinen Outcome. Korrekturen erzeugen eigene Outcome-Versionen; falsche ursprüngliche Prognosen bleiben sichtbar.

Die Prognosehistorie ist in Seiten von maximal 100 Records über `offset` erreichbar; die UI bietet ältere/neuere Seiten. Auch schlechte oder abgelöste Prognosen bleiben abrufbar.
