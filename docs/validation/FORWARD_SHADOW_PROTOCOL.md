# Forward Shadow Protocol

`/models/forward-validation` zeigt **FORWARD_ARCHIVED_SHADOW**, ausdrücklich experimentell. Retrospektive Protokolle tragen **RETROSPECTIVE_PIT_EXPERIMENT**. Ein rückblickender Test ist keine damals gespeicherte Prognose. Erzeugungs- und Informationszeit werden niemals rückdatiert.

Eine Policy bindet eigene SHADOW-Classification-/Regression-Modelle desselben Datasets/Horizonts, 1–5 bestehende Instrumente und Quellenpolitik. Die vorhandene P7-Prognosepipeline prüft reale Herkunft, Featurequalität, Membership, Kalibrierung und Artefaktabhängigkeiten. Fehlende Voraussetzungen erzeugen eine dauerhafte `ABSTAINED`-Prognose mit Grund und ohne erfundene Werte.

Zwei ausdrückliche Schalter sind nötig: `FORWARD_SHADOW_ENABLED` (standardmäßig false) und aktivierte Policy. Die Oberfläche kann Policy-Zeitpläne stoppen. Der stündliche Scheduler verarbeitet höchstens zehn Policies einschließlich Fehlversuchen; persistierte Dispatch-Versuche ermöglichen Rotation. Einzelne Runs sind auf 180 Sekunden begrenzt. Kein Collector oder Source Gate wird dadurch aktiviert.

Ein stabiler Schlüssel je Policy/Instrument/veröffentlichter Sitzung verhindert doppelte Prognosen nach Neustart. Erfolgreiche Prognosen pinnen Modell-, Dataset-, Feature-, Kalender- und Zieldefinition. Spätere Outcomes verwenden denselben P6-Targetvertrag, tatsächliche 30/90 Handelssitzungen, Actions, FX und Benchmark. Vor Reife keine Bewertung. Korrigierte Inputs erzeugen neue Outcome-Versionen; ursprüngliche und falsche Prognosen bleiben sichtbar.

Outcome-Prüfung nutzt einen persistierten Cursor und kleine Seiten mit zehn Prognosen; Wiederholung ist idempotent. Die Historienansicht ist paginiert. Statistik verwendet höchstens die jüngsten 500 gereiften Prognosen je Horizont, unabhängig von der sichtbaren Seite. Unter 50 verschiedenen gereiften Erzeugungstagen keine aggregierte Validierung. Drift benötigt zwei Fenster mit jeweils 50 Tagen; feste Forschungsschwellen für Wahrscheinlichkeitsverschiebung, ECE und Brier lösen keine Promotion aus. Abhängigkeit korrelierter Beobachtungen bleibt ausgewiesen.

Aktuell fehlt reale Forward-Historie. Nachträgliche technische Zeitreise-Tests sind keine solche Historie. P9 akzeptiert experimentelle SHADOW-Ergebnisse nicht als validierte Produktionsprognosen.
