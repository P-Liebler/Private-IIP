# PR10A – Securityentscheid und exakter Releaseumfang

Stand **29.10.2026**: **LOCAL_SYNTHETIC_VERIFIED / SECURITY_BLOCKED /
NOT_APPROVED**. Lokale Prüfung abgeschlossen, keine Securityausnahme erteilt.

## 1. Tatsächlicher GitHub-Lauf

Ausgangs-HEAD und bei Arbeitsbeginn abgefragtes `origin/main`:
`dd601be4bf916550932c9d9067bad1cf7c10c2c6`. Der angeforderte
[Lauf 40883463238](https://github.com/P-Liebler/Private-IIP/actions/runs/40883463238)
ist abgeschlossen: **Verify success / Security success**. Der
[Originalindex](security/pr10-20261029/remote-ci.json) bindet die tatsächlich
heruntergeladenen Artefaktbytes und deren Memberhashes.

| Teilprüfung dieses tatsächlichen Remote-Laufs | Ergebnis und Aussagegrenze |
| --- | --- |
| Verify | 306 Backend-, 155 Host-, 31 Browserfälle sowie statische Prüfungen erfolgreich |
| Dependency-Audits | Core/Support, getrenntes optionales MLflow und NPM erfolgreich |
| Scanner / Datenbank | Verifiziert verfügbar; kein fehlender Scan als Nullbefund behandelt |
| Image-Audit | API/Web und ihr High-/Critical-Paketgate erfolgreich |
| Vollständiger Runtime-/Recovery-Scope | **SKIPPED / NOT_REQUESTED_NOT_VERIFIED** |
| Release | **NOT_APPROVED** |

`SCAN_INCOMPLETE`-/`SECURITY_BLOCKED`-Ausgaben in negativen Unitfällen sind
keine fehlgeschlagenen Jobs. Die zwei Actions-/Runner-Migrationshinweise sind
Warnungen. Ein grüner API-/Web-Workflow prüft nicht automatisch den vollständigen
Core einschließlich Legacy-Recovery. Die lokalen PR10-Arbeitsbytes wurden
nicht gepusht und haben keinen neuen Remote-Lauf. Der vollständige manuelle
CI-Audit wählt nun den neuen PR10-Scope; die bestehenden Gates bleiben erhalten.

## 2. Änderungen und Archivvertrag

### Legacy: moderne Integrität und historische Ausführung getrennt

Der neue additive [`verify_archive_recovery.py`](../ops/verify_archive_recovery.py)
prüft gelieferte ursprüngliche Modellbytes, unabhängig gepinnte Erwartungen,
Konfiguration, Locks und 66 Metadatapins, ohne das alte Image zu starten.
**14 gezielte Tests** bestanden. Der tatsächliche
[V2-Beleg](security/pr10-20261029/archive-integrity-original-receipt-recheck-v2.json)
weist ausdrücklich `ORIGINAL_RECEIPT_RECHECK_ONLY` aus: Der alte Restorebericht
wurde erneut verglichen. **1’385 gemeldete Dateien sind dabei kein neuer
Restore oder eine neue eigene SQL-/S3-Prüfung.** Eine anders datierte
Berichtskopie könnte das ebenfalls nicht beweisen.

[ADR-028](decisions/ADR-028-archive-integrity-and-historical-runtime.md) hält die
normative Ablösung als **offen** fest. Die erforderliche historische
Runtimeprüfung bleibt im Restore-/Releasescope. Weder der alte begrenzte
JSON-/Metadatenprüfer noch der neue statische Pfad beweist historische
numerische Modellinferenz oder Training. Alte Artefakte und Manifestverträge
bleiben unverändert.

Die [vollständige Legacy-Review](security/PR10_LEGACY_RECOVERY_REVIEW.md) und die
[frisch gebundene Vorlage v3](security/pr10-20261029/legacy-recovery-review-template-v3.json)
enthalten alle **48 Critical-/High-Paketzeilen / 12 unterschiedliche IDs**,
mit Digest, Ausführungspfad, Patches, Isolation, Restrisiko, Befristung und
Reviewtrigger. Die Critical-ID ist **GHSA-6q48-6c7w-9gw2**, laut
[Maintainer](https://github.com/certifi/python-certifi/security/advisories/GHSA-6q48-6c7w-9gw2)
ohne bekannte CVE. Die Policy akzeptiert kontrolliert echte CVE-/GHSA-IDs;
Pflichtfelder, Digestbezug, Reviewer und Ablauf bleiben Pflicht. Sämtliche
Vorlagen sind **DRAFT_NOT_APPROVED**, effektive Ausnahmen `[]`.

Ein nachgewiesener Runnerfehler wurde behoben: Ein CLI-Timeout garantierte
zuvor nicht das Ende des daemonseitigen Containers. Jetzt kennt der Runner
vor Start die vollständige Container-ID und entfernt im `finally` ausschließlich
den eigenen gelabelten Container; beide daemonseitigen Abwesenheitsprüfungen
müssen bestehen. **9 Runnerfälle** und ein
[echter begrenzter Timeoutversuch](security/pr10-20261029/legacy-timeout-cleanup.json)
bestanden. Der eingebettete historische Prüfcode ist bytegleich. Python-
Startuphooks und vollständige native Erreichbarkeit bleiben reviewpflichtig.

### Caddy: Routing, Privilegien und aktuelle v3-Grenze

[Import-/JWK-/Patchreview](security/PR10_CADDY_REVIEW.md), geprüft 29.10.2026:
Für **CVE-2026-116587 / GHSA-mgcc-cww5-fp2q** nennt das
[Maintainer-Advisory](https://github.com/go-jose/go-jose/security/advisories/GHSA-mgcc-cww5-fp2q)
weiterhin keinen v3-Fix. Das Entfernen allein des optionalen ACME-Servermoduls
beseitigt die für die interne CA eingebundene Smallstep-/JOSE-Kette nicht.
Kein ungeprüfter Kryptografie-Fork oder Majorersatz wurde eingebaut.

Nachgewiesene kleine Korrekturen: `/internal/*` wird jetzt durch eine exklusive
404-Route vor dem Frontendproxy gesperrt. Compose-Caddy und CA-Export laufen
explizit als UID 10001 auf Containerports 8080/8443; Standardorigin, Secure-Cookies
und privates S3-TLS bleiben erhalten. HTTP/3 ist im geprüften Profil abgeschaltet.
Die begrenzte Storageinitialisierung verweigert ein altes nichtleeres root-owned
CA-Ziel. **9 Regressionen**, tatsächliche
[Nonroot-/TLS-/Restartprobe](security/pr10-20261029/caddy-nonroot-canary.json)
und [Storageinitialisierung](security/pr10-20261029/caddy-storage-init.json)
bestanden. [Belegindex einschließlich früherer Fehlversuche](security/pr10-20261029/caddy-proof-index.json).

Der öffentliche Core konfiguriert keinen ACME-Server und keinen On-Demand-Issuer.
Das begrenzt den geprüften JWK-Eingang, beweist keine allgemeine Nichterreichbarkeit
und entfernt keinen Paketbefund. Der befristete Reviewentwurf bleibt unautorisiert.

## 3. Frischer vollständiger Scope

[PR10-Scope](../ops/releases/pr10-core-v1-scope.json),
[vollständiges Inventar](security/pr10-20261029/core-rc1/inventory.json):
**13 notwendige Dienste / 9 unterschiedliche Images**, alle exakt gescannt.
**13/13 Original-SBOMs formal gültig**;
[Schemaergebnis](security/pr10-20261029/core-rc1/sbom-validation.json).
[Ursprungsindex](security/pr10-20261029/core-rc1/scan-origins.json) dokumentiert
Scanaliase ausschließlich für identische Imagebytes.

| Dienst | Critical | High |
| --- | ---: | ---: |
| legacy-verifier | 1 | 47 |
| api / worker / scheduler | jeweils 0 | jeweils 0 |
| web / postgres / valkey / minio / prometheus / backup | jeweils 0 | jeweils 0 |
| caddy / ca-export / storage-init | jeweils 0 | jeweils 1 |

Über unterschiedliche Images verbleiben **1 Critical / 48 High-Paketzeilen**.
Die drei Caddy-Servicezeilen bezeichnen denselben High-Befund. Sämtliche
Medium-/Low-/Unknown-Befunde bleiben im Inventar sichtbar; Caddy hat im neuen
Datenbankstand **3 Medium**, zuvor im PR9-Scan 1 Medium.

Scanner **Trivy 0.76.0**, Windows-Executable-SHA
`51e50a34f8739424bc88282602d10945b25249ffdb51703fe3c9453c20217c42`.
Datenbank aktualisiert **29.10.2026 13:09:46.269823229 UTC**, SHA
`162d88bff697bee519561c90bb5766f2b9d27e3f0f0eb051b7a3d7bf1df42ff7`.
Originale Scan-/SBOM-/Config-/Imagehashes stehen im Inventar. Ein Paketanalysator
beweist keine vollständige beliebige native Exploitability.

Neuer Core-Backend-Digest: `c1e07fe0…`; separater normaler Produktionsbuild:
`a09316ca…`. Beide besitzen **0 Critical / 0 High / 42 Medium / 19 Low /
2 Unknown**, eigene 321er-Regression, native Probe und vollständigen Restore.
[Core-Build](security/pr10-20261029/backend-build.json),
[separater Build](security/pr10-20261029/standard-backend-build.json),
[separater Scan und SBOM](security/pr10-20261029/standard-production/inventory.json).
Keine Bitidentität zwischen den Builds wird behauptet. Numerische und
Supportpins bleiben erhalten. Herkunft und Assemblervertrag sind an PR8/PR9
gebunden; das ist keine neue vollständige unabhängige Supply-Chain-Zertifizierung.

## 4. Weitere tatsächlich geprüfte Grenzen

- [Dependency-Audit](security/pr10-20261029/dependency-audit.json): tatsächlicher
  Remoteaudit der unveränderten Git-Locks. Windows-CRLF-Unterschiede bei zwei
  Checkoutdateien sind mit beiden Bytehashes und identischem LF-Inhalt offengelegt;
  kein Audit anderer Pakete als Ersatz für neue Images.
- [Regressionsbeleg](security/pr10-20261029/regression-final.json): Ruff/Mypy,
  Frontend-Build, CSP-/Auth-Browserfälle, Migrationen und Negativfälle. Die
  [PR9-CSP-Attributgrenze](security/PR9_CSP_REVIEW.md) bleibt reviewpflichtig.
- [Tatsächlicher neuer Core](security/pr10-20261029/core-staging.json) und
  [Container-/Configbindung](security/pr10-20261029/core-config-proof.json):
  private TLS-Verifikation, falsche CA/Zugänge, Nonces, private Metriken,
  tatsächlicher Prometheus-Scrape und `LLM_UNAVAILABLE` ohne optionale ML-/LLM-Dienste.
- [Core-Restore](security/pr10-20261029/restore-core.json) und
  [separater Produktionsbuild-Restore](security/pr10-20261029/restore-standard-production.json):
  jeweils **1’387 tatsächlich geprüfte Dateihashes**, alle ursprünglichen
  Archivverträge, erforderlicher Legacycheck und verifizierte Containerbereinigung.
- [Finaler Source-Secretscan](security/pr10-20261029/source-security.json) bindet
  die abschließenden Arbeitsbytes; keine Rohmatches oder privaten Originale
  werden veröffentlicht.

## 5. Noch erforderliche tatsächliche Entscheidungen

**SECURITY_APPROVED=false.** Legacyvertrag normativ vertragstreu ablösen oder
alle betroffenen Findings durch eine autorisierte begrenzte Entscheidung zum
exakten Recoveryumfang prüfen. Caddyfix oder tatsächliche befristete
Securityentscheidung; weitere native/Unknown-/CSP-/TLS-/Netz-/Hostreviews.
Die Vorlagen sind vorbereitet, keine Unterschrift oder Zustimmung erfunden.

Zielhost, privates VPN/DNS, reale CA-/Clientprüfung, unabhängiger verschlüsselter
Recoverybetrieb und getrennte Operatorentscheidung bleiben zusätzlich erforderlich.
Der [neue lokale RC](../ops/releases/pr10-core-v1-rc1-manifest.json) bindet
Arbeitsbytes und Belege; er ist **keine** Produktionsfreigabe.
