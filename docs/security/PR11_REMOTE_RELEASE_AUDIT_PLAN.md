# PR11A – Plan für den vollständigen Remote-Releaseaudit

Stand: **29.10.2026**. Status: **REMOTE_FULL_AUDIT_NOT_EXECUTED**.
Dieser Plan erteilt keine Übertragungs-, Runner-, Security- oder
Produktionsfreigabe. Es wurden weder Images übertragen noch ein Push,
Workflow-Dispatch oder ein neuer Build ausgelöst.

## 1. Tatsächlicher CI-Stand

Der [Actions-Lauf 40900032608](https://github.com/P-Liebler/Private-IIP/actions/runs/40900032608)
für `d0feaa67f1505ef247fb5dd199938f0f592230d7` ist erfolgreich:
Verify bestätigt **321 Backendtests, 192 Hosttests und 31 Browserfälle**.
Security-CI hat Scanner/DB, Source-Secrets, Dependencyprüfungen und den
API-/Web-Paketcheck bestanden. Der vollständige Core-/Recoveryaudit wurde
**nicht angefordert und übersprungen**. Der
[Originalbeleg](pr11-20261029/remote-ci.json) bindet Run, Artefakt und Hashes;
ein grüner Gesamtstatus ist keine vollständige Releaseprüfung.

Der bestehende Ablauf liegt in
[security.yml](../../.github/workflows/security.yml),
[ci_full_image_audit.py](../../ops/ci_full_image_audit.py),
[security_audit.py](../../ops/security_audit.py),
[validate_sboms.py](../../ops/validate_sboms.py) und
[security_ci_status.py](../../ops/security_ci_status.py). Es wird keine
parallele Auditengine eingeführt.

**Versionsvorbehalt:** Der historische Remotecommit `d0feaa67...` enthält im
Full-Step den PR10-Scope und 13 Pflichtkomponenten einschließlich
Legacy-Verifier. Der aktuelle PR11-Arbeitsstand desselben bestehenden
Workflows wurde gezielt auf den V2-Scope und seine zwölf Pflichtkomponenten
umgestellt; der dynamische Legacy-Verifier bleibt separat gesperrt. Die
High-/Critical- und Vollständigkeitsgates bleiben erhalten. Diese lokale
Änderung ist noch kein Remoteaudit. Vor einem späteren PR11-Dispatch müssen
tatsächlich ausgecheckter reviewter Workflowstand, finaler Scope und zwölf
Pflichtkomponenten übereinstimmen. `full_inventory: true` auf der alten
Revision würde weiterhin PR10 prüfen. Dieser Plan führt keine neue
Workflowengine ein und behauptet keinen fertigen Transportkanal.

## 2. Exakter geplanter Gegenstand

Autorität ist der neue
[PR11-Core-Scope](../../ops/releases/pr11-core-v1-scope.json), Vertrag
`PRIVATE_CORE_SCOPE_V2`, mit dem ausdrücklich beschlossenen
`PRIVATE_CORE_ARCHIVE_RECOVERY_V1`-Recoveryvertrag. Erwartet werden **zwölf
Pflichtdienste aus acht verschiedenen Imagebytes**:

| Pflichtdienste | Exakte unveränderte PR10-Imagebasis für die Vorbereitung |
| --- | --- |
| `api`, `worker`, `scheduler` | `private-iip/backend@sha256:c1e07fe093e36a214e8e8c343d98600a609573e09a8ec15ab94ab5aaba17a869` |
| `web` | `private-iip/web@sha256:6f316c3ee13108daf042ca2bfcd4b5d36d59fbef8deaa1e316ed98cc137588d5` |
| `postgres` | `private-iip/postgres@sha256:2c9e0b298784e97215aef421ec0b2058631527d0872ce9fbf4c03592baed764f` |
| `valkey` | `valkey/valkey@sha256:081c2f5cb575efc901aa80ff9cdbd1ec6a301682fd35e1ebb4b0990a4a4a8507` |
| `minio` (bestehender Servicename für SeaweedFS) | `private-iip/seaweed@sha256:6bdab6cd91262be0040850c1a6a8add2cf14e0edfdd5d7bbcd7894e8c7177039` |
| `caddy`, `ca-export`, `storage-init` | `private-iip/caddy@sha256:6416b8c2e10d8d62b131dbf3755c01069d7b3dcdb7af720b76c8aeed8bc9dcaf` |
| `prometheus` | `prom/prometheus:v3.15.1@sha256:fa3302279710be2f21a8301ec17a8b4f2301fd829bd113839b3b6b02b6f191a2` |
| `backup` | `private-iip/mc@sha256:a6648014767c128e3bbc04bae0d731c1426413bfa4a64d9e451085ea872eda0f` |

Die Tabelle ist kein Ersatz für den versiegelten Scope: Ändert ein Digest,
endet diese Vorbereitung; erst neue exakte Bytes und eigene Evidenz erlauben
eine neue Ausführung. API-/Web-Images aus dem normalen CI-Neubau sind
separate Buildartefakte und dürfen die privaten Core-Pins nicht ersetzen.

Der dynamische Legacy-Verifier bleibt als deaktivierter Archivgegenstand
mit `optional_dynamic_legacy_status: SECURITY_BLOCKED` getrennt und gesperrt;
sein Originalimage, Metadaten und Befunde bleiben erhalten. Seine bisherige
Statistik **1 Critical / 47 High** wird weder gelöscht noch zu null erklärt.
Seine spätere freiwillige Ausführung verlangt einen eigenen aktuellen Audit
und eine tatsächliche findingbezogene Autorisierung. Der verpflichtende
Core-Restore muss zuvor sämtliche V2-Archivverträge ohne alte
Python-Ausführung tatsächlich erfüllen. Das datenbasierte Metadatenarchiv
mit den 66 unveränderten Paketpins ist ein eigener hashgebundener
Recoverybeleg, kein neuntes Runtimeimage. Sein SHA und der unabhängig
erhaltene originale PR10-Manifesterwartungshash müssen mit
`archive_recovery` übereinstimmen; das Auspacken oder Ausführen alter
Pythonbibliotheken ist damit nicht autorisiert.

Der konkrete vollständige Restoreprüfer benötigt zusätzlich je Backup einen
**vor dem Lauf unabhängig gepinnten aktuellen Erwartungsbeleg**
`PRIVATE_CORE_RESTORE_EXPECTATIONS_V1`. Dieser bindet das aktuelle
Backupmanifest, Run, Datei-/Rohobjektzahl und alle zehn aktuellen Archivhashes;
der alte Modellanker bleibt getrennt unverändert. Spätere gültige Backups
werden dadurch nicht auf den alten PR10-Run oder dessen Aggregate festgelegt.
Dieser Imageaudit ist selbst kein Restore und ersetzt auch keine reale
Portfolioabnahme ohne Researcharchive.

## 3. Benötigte echte Operatorentscheidung

Der Releaseoperator muss den konkreten, isolierten Remote-Auditrunner und
den geschützten Transport der **bereits vorhandenen Originalbytes**
autorisieren. Derzeit fehlen Runnerzugang und Übertragungsfreigabe. Es
werden keine Credentials abgefragt, gespeichert oder in Git vorbereitet.

Der aktuell konfigurierte Job nutzt `ubuntu-latest`. Für diese frische
Umgebung ist kein privater Image-Import implementiert. Ein lokal vorhandenes
Image steht dort nicht automatisch bereit. Auch ein Self-hosted Runner ist
nicht stillschweigend konfiguriert: Runnerwahl, zulässige Revision und
Zugriffsgrenzen sind vor einer solchen tatsächlichen Nutzung gesondert zu
prüfen. GitHub beschreibt Runner-/Workflowrechte und den Schutz vor
unvertrautem Code ausdrücklich als eigene
[Sicherheitsaufgabe](https://docs.github.com/en/actions/reference/security/secure-use).

Zulässige Vorbereitung ist ein vom Operator bereitgestellter isolierter
Runner, dessen **derselbe Dockerdaemon** die Originalimages vor dem Audit
nachweislich enthält. Die vorhandenen CLI-Werkzeuge können dort mit dem
reviewten Checkout ausgeführt werden; eine manuelle Remoteausführung wird
auch als solche protokolliert und nicht als erfolgreicher GitHub-Job
ausgegeben. Eine spätere CI-Anbindung benötigt einen tatsächlich
autorisierten Eingang in genau diesen Job. Sie wird hier nicht erfunden.

Kein Rebuild, Tag-Pull, Digestsubstitut, automatischer Registrywechsel oder
Einspielen privater Nutzerdaten ist Bestandteil dieses Plans.

## 4. Transport und Identität vor dem Scan prüfen

1. **Ursprung binden:** Genau acht freigegebene, bereits vorhandene Images
   selektieren. Vor dem Export für jedes Image Scope-Referenz,
   `docker image inspect`-ID, vorhandene RepoDigests, OS/Architektur/Variante
   und den Config-Digest separat erfassen. Nur die erlaubten Felder
   extrahieren; vollständiges Inspect mit `Config.Env` nicht veröffentlichen.
2. **Geschützten Payload erzeugen:** Ein leeres, eindeutig eigenes
   Exportverzeichnis benutzen. Die gelieferten Originalmanifest-,
   Config- und Layerbytes samt Exportformat protokollieren. Für jede
   übertragene Datei Größe und SHA-256 auf dem Ursprung berechnen und den
   freigegebenen Transportbeleg unabhängig binden. Ein SHA erst auf dem
   Empfänger ist keine unabhängige Erwartung. Archive enthalten ausschließlich
   Images, keine Volumes, Backups, `.env`, privaten CAs oder Finanzoriginale.
3. **Empfang prüfen:** Vor Import alle Payload-SHAs und Größen mit den
   unabhängig erhaltenen Erwartungen vergleichen. Nur im freigegebenen
   Auditdaemon importieren; keine produktiven Dienste starten. Ursprungs-
   und Empfangszeit, Runner-/Daemonversion und die verantwortliche
   Freigabereferenz im geschützten Beleg festhalten.
4. **Identität nach Import prüfen:** Jede ursprüngliche `repository@sha256`
   muss unverändert auflösbar sein und das vorab gebundene Image enthalten.
   Configbytes erneut hashen, Plattform explizit prüfen und die erhaltene
   Manifest-/Index-/Config-Verknüpfung kontrollieren. Unterschiedliche
   Archive müssen nicht bytegleich sein; der tatsächlich transportierte
   Payload muss seinen eigenen vorab gebundenen SHA besitzen. Ein späterer
   Scannerexport erhält einen zusätzlichen eigenen Archivhash.
5. **Abbruch bei Verlust:** Fehlendes Image, uneindeutige Plattform,
   abweichender Config-/Payloadhash oder verlorene Digestreferenz führt zu
   **SCAN_INCOMPLETE**. Nicht anhand eines vertrauten Tagnamens weitermachen.

### Manifestdigest ist nicht automatisch Config-ID

Ein Registry-Index, sein plattformspezifisches Manifest und das referenzierte
Configobjekt haben unterschiedliche Hashes. Docker dokumentiert insbesondere
die getrennten [Multi-Plattform- und Manifestdigests](https://docs.docker.com/dhi/explore/security-concepts/digests/).
Der aktuelle Releasevertrag prüft zusätzlich
`docker image inspect(reference).Id == scope_digest`. Dieser lokal geprüfte
Containerstore-Vertrag muss auf dem Remote-Daemon tatsächlich erfüllt sein;
ein klassischer Store kann an dieser Stelle eine Config-ID liefern.

[docker image load](https://docs.docker.com/reference/cli/docker/image/load/)
stellt Images und Tags wieder her. Daraus folgt keine allgemeine Garantie,
dass ein beliebiger Export/Import alle ursprünglichen RepoDigests oder
OCI-Indexidentitäten erhält. Die ausgewählte Export-/Importform und der
Store müssen deshalb anhand der vorhandenen Originalbytes verifiziert
werden. Ein Tag mit digestähnlichem Namen, ein anderer Registryindex oder
die Gleichsetzung von Config- und Manifestdigest repariert den Vertrag
nicht. Kann der vorhandene Identitycheck auf diesem Runner nicht erfüllt
werden, bleibt der Audit unvollständig; kein Abschwächen des Checks.

Der vorhandene Scannerpfad in `security_audit.py` bindet separat
`config_digest` aus den exportierten tatsächlichen Configbytes und vergleicht
Trivys `Metadata.ImageID` damit. Diese bereits vorhandene Unterscheidung
bleibt erhalten.

## 5. Bestehenden Auditablauf ausführen

Erst nach erfülltem Transport-/Identityvertrag:

1. Reviewte Revision mit unveränderten numerischen Locks, vollständigem
   Scope und den gebundenen öffentlichen Konfigurationsdateien auschecken;
   deren Hashes protokollieren. `create_security_ci_env.py` erzeugt ein
   ausschließlich synthetisches Auditenv. Keine Produktivsecrets verwenden.
2. Den im Workflow gepinnten **Trivy 0.76.0** installieren: Linux-Archivhash
   und daraus ermittelten Binaryhash prüfen. Über
   `prepare_vulnerability_db.py` die aktuelle DB aus den vorhandenen
   offiziellen Bezugsquellen prüfen/beschaffen. DB-Version, Byteshash,
   Metadaten-/Akquisitionshash und Aktualisierungs-/Abrufzeit binden;
   zulässiges DB-Alter maximal 48 Stunden. Downloadfehler oder veraltete DB
   sind keine bestandene Prüfung.
3. Bestehende Offlineverträge, Source-Secrets- und getrennte Python-/NPM-
   Dependencyprüfungen ausführen. Deren normale API-/Web-Buildprüfung bleibt
   getrennte CI-Evidenz; ihre neuen Images ersetzen keine Core-Pins.
4. Für den vollständigen Schritt ausdrücklich
   `ci_full_image_audit.py --release-scope <finaler PR11-Scope>` mit dem
   vorhandenen Auditenv, Scanner, Binaryhash, DB-Cache und einem neuen
   leeren Outputpfad verwenden. Dieser Zweig prüft die aufgelöste
   Compose-Konfiguration, zwölf Dienste, exakte Pins und lokale Verfügbarkeit;
   er baut und pullt die Releaseimages nicht. Der normale Zweig ohne
   `--release-scope` ist hierfür ungeeignet.
5. `validate_sboms.py` muss die **zwölf einzelnen originalen CycloneDX-
   SBOMs** per gebundenem Hash und gepinntem Schema prüfen. Acht verschiedene
   Images erlauben gemeinsame Bytes, aber kein Auslassen eines Dienstes
   oder bloßes Hochrechnen aus API/Web. Scannerlauf, Inventar, Original-SBOMs,
   Scopehash, öffentliche Konfigurationshashes und
   `release-scope-audit.json` müssen denselben ausgeführten Stand bezeichnen.
6. Den unveränderten High-/Critical-Paketcheck für exakt die zwölf aktiven
   Namen durchführen und den Gesamtstatus mit `security_ci_status.py`
   erzeugen. `package-only` bleibt ein Paketcheck, keine Releasefreigabe.
   Aktuell ist wegen des offenen Caddy-High-Befunds ein echter blockierter
   Paketstatus zu erwarten; er darf nicht unterdrückt werden.

Die Auflösung von Env-/Composekonfigurationen darf nur deren Hash und
freigegebene Felder als Evidenz veröffentlichen. Ein solcher Audit startet
keine Plattform, Migration, Finanzcollection, historische Runtime oder
Modellpromotion.

## 6. Evidenz, Ergebnis und Abschluss

**Öffentlich freigebbar:** Allowlist-Inventar, zwölf Scanrecords, zwölf
unveränderte SBOM-Originale mit Hashes, formale SBOM-Prüfung,
Scanner-/DB-Belege, Scope, öffentliche Konfigurationshashes,
`release-scope-audit.json`, bereinigte Dependency-/Source-Statusbelege und
der tatsächliche Laufstatus. Vor einem Upload alle ausgewählten Dateien
prüfen. Die bestehende Workflow-Allowlist ist die Ausgangsbasis.

**Geschützt belassen:** Imagepayloads und Transportzugänge, rohe
Scanner-/Fehlerausgaben, vollständige Inspect-/Compose-JSON,
Secret-Matches, Umgebungsdateien, Schlüssel, CAs, Backups und
Finanzoriginale. Kein pauschaler Verzeichnisupload und keine Erweiterung der
öffentlichen Cacheinhalte um Images oder Anwendungsevidenz.

| Tatsächliches Ergebnis | Aussage |
| --- | --- |
| Fehlende Originalbytes / Identity- oder Scopeabweichung / fehlende oder ungültige SBOM / fehlgeschlagener Scan | `SCAN_INCOMPLETE`; nie null Findings |
| Vollständiger Scan mit offenem High/Critical | `SECURITY_BLOCKED`; findingbezogener tatsächlicher Securityentscheid bleibt erforderlich |
| Vollständige automatische Checks ohne offene Paketblocker | Technische Evidenz; **keine automatische Security-, Zielhost- oder Operatorfreigabe** |
| Manueller Remoteaufruf erfolgreich | Neuer manueller Remote-Beleg; der Status eines historischen oder nicht ausgeführten GitHub-Jobs ändert sich nicht |

Bis ein tatsächlich autorisierter Transport-/Runnerweg besteht, ist dieser
konkrete Plan der Übergabestand. Kein künstlicher Dispatch ohne private
Imagebytes und kein Ersatz des fehlenden Remoteaudits durch weitere lokale
synthetische Testarchive. Historische PR8-/PR9-/PR10-Belege bleiben
unverändert, der [Caddy-Entscheid](PR11_CADDY_REVIEW.md) offen und der
Produktivstart gesperrt.
