# Point-in-Time Datasets

P6, 2026-10-13. Normativ bleiben Masterplan 75–95 und 158. Ein Dataset ist eine unveränderliche, nutzergebundene Version; keine Sammlung aktueller Zeiger. Configuration, Manifest, Feature-Snapshots, explizite Ausschlüsse und getrennte Target-Beobachtungen liegen in JSONB. Tabellen werden über Alembic verwaltet. Datenbank-Trigger verhindern Änderungen vorhandener P6-Versionen.

## Verfügbarkeit

`STRICT_PIT` verlangt öffentlichen Wissenszeitpunkt, lokale Beobachtung und einen bis zum Cutoff gespeicherten Review. `USER_ASSERTED` und `UNVERIFIED` bestehen dieses Gate nicht. `LOCAL_FIRST_OBSERVATION` belegt ausschließlich den eigenen Beobachtungszeitpunkt; eine ältere manuelle Veröffentlichung wird dadurch nicht verifiziert. `VERIFIED_PUBLIC_TIMESTAMP` und `VERIFIED_SOURCE_DOCUMENT` erfordern Originalreferenz, geprüften Zeitstempel, Methode und konkrete Review-Begründung. Reviews sind append-only und erhöhen die historische Vertrauensstufe niemals rückwirkend. Alte Fakten ohne Review bleiben unbekannt.

`RECONSTRUCTED_HISTORICAL` lässt nachträglich importierte validierte Marktdaten zu. Aktuelle Korrekturen dürfen nur in diesem ausdrücklich gekennzeichneten explorativen Modus in ältere Marktfenster eingehen. Fundamentals, Estimates, News und Macro behalten ihre tatsächlichen lokalen Zeitgrenzen. Rekonstruktion erfüllt kein strenges ML-Gate. Synthetische Testhistorie ist eine Simulation und kein reales Archiv.

## Identität und Replay

SHA-256 über sortierte Configuration, Manifest, Rows und Quality. Das Manifest enthält Git-Basiscommit (`CODE_COMMIT`, andernfalls ausdrücklich UNVERIFIED), Hash aller Backend-Quelldateien, Dependency-Lock, Kalender-/Feature-/Target-/Action-/FX-/Availability-Policies sowie Versions- und Raw-Bezüge. Keine Zufallsstrategie; Seed null. Wiederholte identische Inputs verwenden dieselbe Dataset-Version.

`POST /datasets/{id}/rebuild` lädt ausschließlich gepinnte Versionen, prüft ihre einzelnen Inhalte, Raw-Bytes und Feature-/Content-Hashes und reproduziert das gespeicherte Dataset durch Replay der unveränderlichen Artefakte. Keine Neuauswahl heutiger Canonical-Versionen. Fehlende oder veränderte Raw-/Canonical-/Feature-Versionen geben einen expliziten Fehler. Frühere Entwicklungsartefakte ohne Content-Beleg werden ausdrücklich abgewiesen. Ein Replay der gespeicherten Artefakte ist keine Neuberechnung alter Software mit heutigen Regeln. Code-Manifeste bleiben pro Prozess ab dem ersten Build stabil; nach Codeänderungen ist vor neuen Runs ein Neustart erforderlich.

## Grenzen und Betrieb

Default maximal 30 Instrumente, 400 Sessions, ein gleichzeitiger Run und 240 Sekunden. Dieselben Settings gelten für API und Worker. Builds laufen momentan begrenzt im API-Prozess; Celery bleibt vorhanden, führt aber keinen zusätzlichen P6-Collector aus. `pit_jobs` protokolliert Start, Abschluss, Progress 0/100 und Fehlercode. Abgebrochene Prozesse werden beim Statusabruf nach Timeout als FAILED markiert. Überschrittene Limits erzeugen keinen teilweise erfolgreichen Dataset-Stand.

Private Universe-/Dataset-/Backtest-/Job-IDs anderer Nutzer liefern 404. Eine fehlende Beobachtung bleibt fehlend. Quality weist Mitgliedschaft, Preise, FX, Action Coverage, fehlende Features und Labels aus. Feature-Missingness ist kein Ersatzwert und keine automatische ML-Freigabe.
