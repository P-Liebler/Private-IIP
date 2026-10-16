# ADR-024: Exakte P6-Hashes bei Schemaerweiterungen

Datum: 2026-10-16. Status: angenommen für PR1.

## Problem

P6 pinnt vollständige Zeileninhalte als SHA-256. Migration 0018 ergänzt Action-/Coverage-/Macro-Metadaten. Auch fachlich leere neue Spalten würden den ursprünglichen Zeilenhash eines Altarchivs verändern. Bestehende Manifeste und Modelle dürfen deshalb weder umgeschrieben noch mit einer pauschal abgeschalteten Hashprüfung geladen werden.

## Entscheidung

Neue Dataset-Manifeste verwenden `row-fields-v2` mit explizit gepinnter Feldmenge je Entität. Rebuild prüft Feldmenge, vollständigen Zeilenhash, Dataset-Inhalt und Raw-Hash unverändert strikt. Unbekannte Schemata oder fehlende Felder schlagen fehl.

Alte Manifeste ohne Schemamarker verwenden ausschliesslich den dokumentierten v1-Vertrag. `version_hashing.V1_ADDITIONS` kennt genau die in 0018 ergänzten Spalten. Diese dürfen für den v1-Hash nur dann ausgeblendet werden, wenn sie exakt den bekannten Migrationsdefaults entsprechen: null oder die ursprüngliche SPLIT/DIVIDEND-Gesamtcoverage. Jeder andere Wert ergibt `PINNED_VERSION_CHANGED`. Alle ursprünglichen Felder werden weiterhin byteäquivalent serialisiert und gegen ihren ursprünglichen Hash geprüft. Kein beliebiges Ignorieren unbekannter Spalten.

## Nachweis und Grenze

Der bestehende Dataset-Hash `dd5cd6ef97b9248eb148725797470069b9b33635df15f8506d61bf99761ea538` wurde nach der Migration als `VERIFIED_PINNED_REPLAY` bestätigt. Bestehende Dataset-/Modell-/Prognosedaten wurden nicht geändert. Modell-Promotion, Abhängigkeitspins und Artefaktprüfungen bleiben unverändert. Weitere Schemaänderungen benötigen einen neuen ausdrücklichen Vertrag und erneute Replay-Prüfung.
