# Modellruntime und TLS-Dependency-Update

## PR5 – implementierter Stand vom 22.10.2026

Normale API und Celery verwenden `certifi==2026.10.19` und prüfen beim Start den Lock und die tatsächlich installierte Version. Der Runtimevertrag lautet `PR5_CORE_CERTIFI_20261019_PDF_6211_V2`. Zusätzlich wurde nach aktuellem Audit pypdf von 6.20.1 auf 6.21.1 migriert; neue Dokumente tragen einen neuen Parservertrag, bestehende Versionen bleiben erhalten. Numerische Pins bleiben erhalten. Neue Modelle erhalten den neuen vollständigen Lockvertrag. Alte Modelle bleiben in der normalen API mit `ARTIFACT_DEPENDENCY_MISMATCH` gesperrt.

Der ursprüngliche Core-Lock liegt unter `backend/legacy_contracts/pr4/requirements.lock`. `scripts.export_legacy_model` exportiert nach Eigentums- und Originalhashprüfung ausschließlich ein internes JSON-Artefakt. `ops/verify_legacy_model.py --image <Archivimage@sha256:…> --envelope <private Datei> --output <neue Datei>` prüft es separat mit `--network none`, read-only, UID 10001, ohne Mounts/Secrets/Socket und mit Ressourcenlimit. Es führt keinen Modellcode aus. Hash, Metadaten, ursprünglicher Lock und tatsächlich installierte Pins müssen übereinstimmen. Fehlende historische Assistant-Verträge werden explizit ausgewiesen, nicht nachgetragen. Ein Lauf gegen das unveränderte synthetische Archiv ist bestanden; kein automatisches API-Routing oder historische Prognoseneuberechnung wurde eingeführt.

`restore_verify.py --legacy-image <digest>` verlangt zusätzlich zur Daten-/Objektprüfung diesen isolierten Prozess. Der Schalter allein ist keine Kompatibilitätsfreigabe. Aktuelle End-to-End-Ergebnisse stehen im [PR5-Abnahmebericht](../PR5_ACCEPTANCE_REPORT.md). Normale Dependency-Prüfungen bleiben strikt. Security-, Zielhost-, Quellen-, Modell- und Strategiefreigaben bleiben separat.

## Historischer Entscheidungsstand PR4 (21.10.2026)

Die folgenden Abschnitte dokumentieren die Ausgangslage vor PR5. Aussagen über einen unveränderten Core oder einen noch nicht implementierten Prozess gelten für diesen früheren Stand.

## Konkreter Konflikt

Der frische pip-audit-Lauf meldet `certifi==2026.7.22` mit `PYSEC-2026-4320` / [GHSA-6q48-6c7w-9gw2](https://github.com/advisories/GHSA-6q48-6c7w-9gw2), veröffentlicht am 20.10.2026. [Herstellerrelease 2026.10.19](https://github.com/certifi/python-certifi/releases/tag/2026.10.19) ist der empfohlene korrigierte Stand. Kompromittierte Zwischen-CA-Schlüssel können bei zusätzlicher Kontrolle des Netzwerkpfads TLS-Angriffe ermöglichen. Keine eigene Ausnutzbarkeit oder Nichtbetroffenheit behauptet.

`code_manifest()` bindet den vollständigen Inhalt von `requirements.lock`, nicht nur NumPy/Scipy. `ModelRegistryService.artifact()` vergleicht diesen exakten Vertrag. Selbst ein einzelner certifi-Pinwechsel sperrt daher alte Modelle mit `ARTIFACT_DEPENDENCY_MISMATCH`. Diesen Check zu entfernen, certifi aus alten Verträgen zu streichen oder neue installierte Versionen unter einem alten Lock zu verstecken wäre keine zulässige Migration.

MLflow hat einen separaten Lock und speichert/serviert Trackingmetadaten und Artefakte. Sein certifi-Patch kann unabhängig gebaut, gescannt und mit authentifiziertem S3-/TLS-Roundtrip geprüft werden. Das löst den Backend-Core-Befund nicht.

## Sicherer Kompatibilitätsweg

1. Bestehenden Core-Lock, alte Imagebytes, P6-Dataset-/P7-Artefakthashes und den konsistenten Daten-/Objektbackupbestand erhalten. Der neue isolierte Restore prüft diesen alten Vertrag unverändert.
2. Gepatchte Core-Runtime als separate neue Runtimeversion entwickeln. Nur den beabsichtigten certifi-Pin ändern; numerische Pins erhalten. Neuer Lockhash, Image-/Config-Digest, SBOM, Audit, Code-/Konfigurationsvertrag und vollständige Regression sind notwendig.
3. Alte Modelle ausschließlich unter ihrem archivierten exakten Vertrag in einer gesonderten, für externe Netzzugriffe gesperrten Verifikations-/Replayumgebung laden. Die vorhandene Restoreumgebung nutzt ein internes Docker-Netz. Keine alten Images als normale Collector-/API-Runtime für produktive externe TLS-Anfragen betreiben.
4. Ein späteres Legacy-Replay muss Eingaben/Artefakte über Hashes und interne IDs binden, ausschließlich typisierte Resultate zurückgeben und weder Source-Gates noch Ledger/Archive verändern. Eine solche Laufzeitrouting-Erweiterung ist noch nicht implementiert oder freigegeben.
5. Neue Modelle nur unter der neuen Runtime neu trainieren und nach den bestehenden P7-/PR2-/P9-Verträgen separat validieren. Alte Ergebnisse erhalten, keine Manifeste umschreiben und keine automatische Promotion.

## Aktuelle Entscheidung und Restgefahr

Der Core-Lock bleibt bewusst unverändert, damit historische Artefakte weiterhin streng prüfbar sind. **Der certifi-Befund bleibt ein konkreter Critical-Release-Blocker mit verfügbarem Fix**, bis der beschriebene getrennte Runtimeweg und seine Tests abgeschlossen sind. Er wird weder ignoriert noch als behoben ausgewiesen. Quellen bleiben deaktiviert, Collection/Forward aus; diese Einschränkungen ersetzen keine Security-Freigabe. Produktive Nutzung bleibt gesperrt.

Vor einer Freigabe: verantwortlicher Runtime-/Security-Review, tatsächliche Netzwerkisolation, kompatibler gepatchter Core, Legacy-Replay-Verträge, vollständiger Modell-/Restore-Nachweis sowie aktueller Audit aller geänderten Digests. Keine selbst ausgestellte Ausnahme wegen des Kompatibilitätskonflikts.
