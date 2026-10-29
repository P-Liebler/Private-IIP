# ADR-028: Archivintegrität und historische Runtime getrennt nachweisen

Datum: **29.10.2026**. Status: **additive Integritätsprüfung implementiert; normative Ablösung der historischen Runtime vorgeschlagen, nicht beschlossen**.

## Anlass und unveränderliche Grenzen

Das historische Recovery-Image enthält offene Critical-/High-Befunde. Der bestehende dynamische Vertrag `PR5_LEGACY_VERIFICATION_V1` prüft JSON-Artefaktbytes, Trainings-/Konfigurationsmetadaten, Lockdateien und installierte Distributionsversionen. Er führt weder historisches Training noch Modellinferenz aus. Trotzdem beweist sein erfolgreicher Lauf zusätzlich, dass die alte Python-Runtime den begrenzten Prüfcode ausführt.

Der PR9-Vertrag verlangt diesen separaten Lauf weiterhin ausdrücklich. Ein moderner Parser darf dessen Ergebnis nicht als eigene historische Ausführung ausgeben. [ADR-022](ADR-022-preserve-model-dependency-pins.md), der P7-Modelllader und die ursprünglichen Archive bleiben erhalten. Insbesondere bleiben Dependency-Gates im aktiven Modelllader unverändert.

## Implementierte additive Entscheidung

`PR10_ARCHIVE_INTEGRITY_RECOVERY_V2` ergänzt die bestehenden Nachweise. [`ops/verify_archive_recovery.py`](../../ops/verify_archive_recovery.py) arbeitet unter dem aktuellen Operator-Python und:

1. verlangt einen **separat aufbewahrten erwarteten SHA-256 des ursprünglichen RC-Manifests**; es übernimmt keinen erwarteten Hash aus dem neu gelieferten Modell oder Restorebericht;
2. prüft dessen Inhaltschecksumme und die darin gebundenen unveränderten ursprünglichen Static-/Restoreberichte;
3. bindet Modellbytes an den ursprünglichen Artefakthash; damit sind auch die im Artefakt enthaltene Trainingskonfiguration und der Code-/Dependency-Vertrag gebunden; abweichende Begleitmetadaten werden abgelehnt;
4. liest die beiden historischen Lockdateien und exakten SBOM-Metadaten erneut aus einem **niemals gestarteten**, digestgebundenen Container mit dem bestehenden begrenzten PR9-Leser; es vergleicht ursprünglichen SBOM- und Metadatenmanifesthash sowie alle Pins;
5. vergleicht ausschließlich die **gemeldeten** zehn Archivhashverträge des übergebenen Berichts mit dem ursprünglichen Bericht, einschließlich Prognosen/Outcomes, Dataset, Modell, Risiko, Empfehlungen, Intelligence und technischen Historien; auch die gemeldeten Werte für Goldenstichtag, CHF 10'180 und Stale-Price-Vertrag müssen übereinstimmen; es greift dafür auf keine wiederhergestellte DB oder S3-Instanz zu;
6. schreibt ausschließlich einen neuen Ergebnisbeleg; es ändert weder Artefakte noch DB-Zeilen, Modelle, Forecasts, Ausgangsmanifeste oder Lockfiles.

Ein Hash authentisiert keinen Herausgeber. Die vertrauenswürdige Beschaffung und unabhängige Aufbewahrung des ursprünglichen Manifestpins bleiben eine Operatorpflicht. Der Vergleich eines übergebenen Berichts beweist **keinen neuen Restore, keine wiederhergestellten Archivbytes und keine eigenständige Prüfung der Produzentenaussagen**. Identische SHA-256 des gelieferten und ursprünglichen Berichts ergeben zwingend `ORIGINAL_RECEIPT_RECHECK_ONLY`, auch bei einem anderen Dateipfad. Unterschiedliche Berichtsbytes begründen ebenfalls keine Frische oder Authentizität. Die Zahl wird nur als `reported_verified_backup_files` ausgegeben.

## Getrennte Aussagen

| Nachweisebene | Neuer Vertrag | Bisheriger dynamischer Vertrag |
| --- | --- | --- |
| Ursprüngliche JSON-Artefaktbytes, erwarteter Hash, Trainings-/Konfigurationsmetadaten | Ja | Ja |
| Historische Lockbytes und installierte Distributionsversionen im exakten Image | Ja, statisch gelesen | Ja, durch alte `importlib.metadata` gelesen |
| Gemeldete Forecast-/Outcome- und weitere Historienhashes | Nur Vergleich der gelieferten Berichtsangaben; keine wiederhergestellten Archivbytes geprüft | Teil des getrennten Restorebelegs, nicht des Verifiercodes |
| Alte Python-Runtime startet und führt den begrenzten Prüfcode aus | **Nicht ausgeführt, nicht bewiesen** | Ja, auf genau diesen Prüfcode beschränkt |
| Historische Modellinferenz oder Training numerisch reproduziert | **Nicht ausgeführt, nicht bewiesen** | **Auch dort nicht ausgeführt und nicht bewiesen** |
| Forecastvalidierung, Modell-/Strategiepromotion oder Securityfreigabe | Nein | Nein |

Die Ergebnisfelder `required_legacy_runtime_check_satisfied=false`, `historical_runtime_execution=NOT_EXECUTED_NOT_PROVEN` und `security_approval=false` sind verpflichtend. Ein eventuell im übergebenen Restorebericht vorhandener früherer Legacy-Lauf wird als **separater** Vorgang ausgewiesen.

`integrity_verified=true` gilt ausschließlich für `SUPPLIED_ARTIFACT_BYTES_AND_HISTORICAL_IMAGE_METADATA_ONLY`: die tatsächlich gelesenen gelieferten Modellbytes und historischen Image-Metadaten. `fresh_restore_executed_by_this_verifier`, `fresh_restore_proven_by_this_verifier`, `restored_database_accessed_by_this_verifier`, `restored_object_store_accessed_by_this_verifier` und `restored_archive_bytes_checked_by_this_verifier` bleiben sämtlich **false**. Eine Freigabe, die einen frischen Restore verlangt, muss den eigentlichen Produzentenlauf unabhängig binden und überprüfen.

## Nicht getroffene normative Entscheidung

Die neue Prüfung wird **nicht** automatisch anstelle der vorhandenen Legacy-Pflicht in Restore, Release-Manifest, Core-Scope oder Archivcheckpoint eingehängt. Das historische Image bleibt im erforderlichen Recovery-Scope. Der PR9-Sicherheitsblocker wird durch den neuen Beleg nicht entfernt.

Eine spätere Ablösung muss ausdrücklich entscheiden, ob Private Core V1 nur Integrität benötigt oder ob historische Runtime-Ausführbarkeit zu seinen akzeptierten Recovery-Anforderungen gehört. Sie braucht einen versionierten neuen Restore-/Release-Vertrag mit negativer Regression gegen fehlende/ersetzte Archivanker, unveränderte alte Verträge und einen tatsächlichen isolierten Restore. Eine eventuell aufgeschobene historische Ausführung ist als solche sichtbar zu halten. Wissenschaftliche Wiederholung und P7-Promotion bleiben eigene Aufgaben.

Falls der alte Lauf weiterhin Pflicht ist, gilt nur der [befristete, digest- und findingbezogene Reviewpfad](../security/PR10_LEGACY_RECOVERY_REVIEW.md). Es liegt keine Ausnahmeentscheidung vor.

## Prüfung

**14 neue Offline-Fixturetests bestanden**, ergänzend zu den bestehenden Static-/Legacy-Tests. Sie verwerfen unter anderem neu berechnete Modellhashes, geänderte ursprüngliche Belege, abweichende Training-/Konfigurationsdaten, veränderte gemeldete Archivhashes, gemeldeten fehlgeschlagenen Restore/Cleanup, veränderten gemeldeten Goldenstichtag, ersetzte Metadaten/SBOMs und umetikettierte Imageausführung. Zwei zusätzliche Semantiktests sichern, dass eine Bytekopie des ursprünglichen Berichts und ein lediglich anders datierter Bericht niemals einen frischen Restore oder eigene Archivbyteprüfung begründen.

Der [tatsächliche korrigierte PR10-V2-Lauf](../security/pr10-20261029/archive-integrity-original-receipt-recheck-v2.json) prüfte die gelieferten vorhandenen synthetischen Modellbytes mit **66 Pins** gegen das unveränderte PR9-RC-Manifest. Der wiederverwendete ursprüngliche Bericht vom **28.10.2026** wird korrekt als `ORIGINAL_RECEIPT_RECHECK_ONLY` mit **1'385 gemeldeten Dateihashes** ausgewiesen; dies ist kein neuer Restore, kein Zugriff auf wiederhergestellte Archive und kein realer Portfolio-Pilot. Der [erste V1-Beleg](../security/pr10-20261029/archive-integrity-original-restore.json) bleibt unverändert, seine allgemeineren Ergebnisnamen werden durch die ausdrücklichen V2-Aussagegrenzen präzisiert.
