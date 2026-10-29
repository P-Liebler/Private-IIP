# PR9A – Security-Blocker und vollständiger Core-Scope

Stand **29.10.2026**: **LOCAL_SYNTHETIC_VERIFIED / SECURITY_BLOCKED / NOT_APPROVED**. Lokale technische Arbeiten abgeschlossen; keine Produktivinstallation, Quellenaktivierung, Modellpromotion oder Veröffentlichung.

## Tatsächlicher Remotezustand und CI-Korrektur

HEAD und zuletzt geprüftes `origin/main`: **b78b27652fad9e22ebb7578a35a85a44ef20c25e**. Der [reale Lauf 40642782341](https://github.com/P-Liebler/Private-IIP/actions/runs/40642782341) meldet Verify **success**, Security **failure**. Scanner/DB, Offlineverträge, Source-/Dependency-Audit, API-/Web-Scans und historische PR4-Berichterstellung waren erfolgreich; das High-/Critical-Paketgate scheiterte. Vollständiger Operatoraudit war übersprungen. [Originaler Remoteindex](security/pr9-20261028/remote-ci.json). PR9 wurde weder gepusht noch remote geprüft.

Der normale Backend-Produktionsbuild verwendet jetzt denselben gemessenen Runtime-Assembler wie der lokale Core-Kandidat. Sein eigener tatsächlicher frischer Build/Scan hat **0 High / 0 Critical**, separate vollständige 306er-Regression und Restore bestanden. Er ist **nicht bitidentisch** zum aus archivierten PR8-Wheelbytes aufgebauten Core-Digest. [Eigener Scan/SBOM](security/pr9-20261028/standard-production/inventory.json), [separater Restore](security/pr9-20261028/restore-standard-production.json). Historische numerische Pins und Modellmanifeste wurden nicht geändert.

Die automatische API-/Web-Prüfung meldet ohne vollständigen Auftrag `NOT_REQUESTED_NOT_VERIFIED` für den Core-Releaseumfang. High **und** Critical bleiben im Paketgate. `--package-only` ist kein Releaseapproval. Der finale Releasevaluator wurde nicht gelockert. Der vollständige Operatorpfad verlangt alle 13 exakten Core-/Recovery-Servicepins, tatsächliche lokale Image-IDs und aufgelöste ausgewählte Compose-Konfiguration; kein Build/Pull/Substitut fehlender privater Images. Ein frischer Runner benötigt einen autorisierten Übertragungsweg für diese exakten Bytes. Fehlende/fehlerhafte Scans bleiben `SCAN_INCOMPLETE`.

Die CI-Proofdatei bindet Scope, Pins, den Hash des aufgelösten Configs und die fünf öffentlichen Configdateihashes. Secrets aus aufgelöstem Compose werden nicht publiziert. `CI_GENERATED_CONFIG_ONLY_NOT_TARGET` bleibt explizit. Falsche, fehlende, nichthexadezimale oder veränderte Configproofs, ausgelassene Recovery-Images sowie alte/zukünftige DB-Zeitpunkte werden abgewiesen. Historische PR4-Ergebnisse bleiben getrennt. Zehn neue plus zwei bestehende gezielte CI-Fälle und die gesamte **155er-Hostsuite** bestehen. Ein neuer tatsächlicher Remote-Lauf bleibt nach später autorisiertem Push erforderlich.

## Runtime und tatsächlich behobene Paketpfade

[Detaillierter Runtime-Review](PR9A_BACKEND_RUNTIME_REVIEW.md) dokumentiert die ursprünglichen **44 High-Zeilen / 17 Binärpakete / acht CVEs**, Versionen, Debian-Primärquellen und Verwendungspfade. Der versionierte nichtinteraktive Core lässt genau fünf optionale TUI-/GUI-/native UUID-Erweiterungen weg; Quellhashes sind dokumentiert. Die 66 Core-/Supportdistributionen und numerischen Versionen bleiben unverändert. Alle verbleibenden ELF-Abhängigkeiten, NSS, Locale, CA und Zeitzonen sind gemessen; verbliebene Paketidentitäten bleiben sichtbar. Keine Sid-Mischung oder Scannerunterdrückung.

Der endgültige Core-Backend-Digest `5a925e0e…` besteht Offline-Nativ-/Lock-/NSS-/TLS-/Argon2-/Numerikprobe, vollständige **306 Backendtests**, Fresh Migration/Schema Drift sowie den neuen vollständigen Restore. **0 Critical / 0 High / 42 Medium / 19 Low / 2 Unknown**. Niedrigere oder unbekannte Schweregrade bleiben reviewpflichtig.

SeaweedFS wurde aus dem tatsächlichen offiziellen 4.51-Tagcommit gebaut und `go-jose/v4` auf 4.1.6 gepatcht: **0 High / 0 Critical**. Caddy wurde aus v2.11.7-Source mit `go-jose/v4` 4.1.6 und `x/net` 0.62.0 gebaut. Die dadurch behebbaren High-Pfade sind geschlossen; ein separater v3-Befund bleibt. [Quellidentitäten](security/pr9-20261028/go-source-review.json), [Seaweed-Build](security/pr9-20261028/seaweed-build.json), [Caddy-Build](security/pr9-20261028/caddy-build.json). Die bestehenden OS-/Store-Majors wurden nicht automatisch migriert.

## Frischer endgültiger Scope

[Inventar](security/pr9-20261028/core-rc1/inventory.json): **13 notwendige Dienste, neun verschiedene Images, 13 formal gültige Original-SBOMs**. [Formale Validierung](security/pr9-20261028/core-rc1/sbom-validation.json). Gleiche Imagebytes dürfen denselben exakten Scan verwenden; [Ursprungsindex](security/pr9-20261028/core-rc1/scan-origins.json) dokumentiert die Aliase, unveränderte SBOM-/Scanbytes und Originalrecordhashes.

| Dienst | Critical | High |
| --- | --- | --- |
| `legacy-verifier` | 1 | 47 |
| `api` | 0 | 0 |
| `worker` | 0 | 0 |
| `scheduler` | 0 | 0 |
| `web` | 0 | 0 |
| `postgres` | 0 | 0 |
| `valkey` | 0 | 0 |
| `minio` | 0 | 0 |
| `caddy` | 0 | 1 |
| `ca-export` | 0 | 1 |
| `prometheus` | 0 | 0 |
| `backup` | 0 | 0 |
| `storage-init` | 0 | 1 |

Trivy **0.76.0**, Executable-SHA `51e50a34…`; DB **28.10.2026 07:10:42.861393948 UTC**, DB-SHA `2c8f4b04…`. Exakte vollständige Hashes, Scan-/Config-/Archive-/SBOMbindungen und sämtliche Medium-/Low-/Unknown-Zeilen stehen im Inventar. Über unterschiedliche Imagebytes summiert verbleiben **1 Critical und 48 High-Paketzeilen**. Die drei Caddy-Serviceeinträge sind derselbe eine High-Paketbefund, keine drei unabhängigen CVEs. Keine Aussage vollständiger beliebiger nativer Exploitability aus Paketanalysatoren.

## Tatsächlich offene Securityentscheidungen

1. [Legacy-Verifier](security/PR9_LEGACY_VERIFIER_REVIEW.md): erforderlicher unveränderter Recovery-Digest `acb9d202…`, **1 Critical / 47 High**. Das certifi-Maintainer-Advisory `GHSA-6q48-6c7w-9gw2` nennt keine bekannte CVE-ID. Ein begrenzter digestbezogener Ausnahmevorschlag ist **DRAFT_NOT_APPROVED**; Reviewer, Approvalreferenz und tatsächliches Zeitfenster fehlen. Der [finale statische Vorprüfer](security/pr9-20261028/static-archive-metadata-final.json) prüft Archivbytes und 66 Metadatapins ohne Start des alten Images. Er ersetzt weder den bisherigen isolierten dynamischen Vertragscheck noch beweist er vollständige historische ML-Inferenzreproduzierbarkeit. Das alte Image bleibt im Recovery-Scope.
2. [Caddy](security/PR9_CADDY_REVIEW.md): **CVE-2026-116587**, `go-jose/v3` 3.0.5 ohne veröffentlichten v3-Fix. Konkrete JWK-Erreichbarkeit, interne CA und DoS-Exposition benötigen berechtigten Review. Keine ungeprüfte Kryptografie-/Modulmajor-Substitution und keine fingierte Ausnahme.
3. [CSP](security/PR9_CSP_REVIEW.md): Nonces schützen nun zusätzlich Styleelemente; nur dynamische Styleattribute behalten `style-src-attr 'unsafe-inline'`. Finale 31 Browserfälle einschließlich echter Radix-Stylesheetnonce bestehen. Attributinjektion und tatsächliche Zielclient-Kompatibilität bleiben getrennt reviewpflichtig.
4. Native Restgrenzen, Unknown-/niedrigere Funde, Zielhost-, Wartungs- und Netzexposition benötigen vollständigen menschlichen Review. Paketnullbefunde erteilen keine Freigabe.

## Weitere tatsächlich ausgeführte Grenzen

Frische Python-Core-/Support- und getrennte MLflow-Dependency-Audits sowie NPM-Produktionsaudit ohne bekannte Findings; Locks bytegleich. [Auditbeleg](security/pr9-20261028/dependency-audit.json). Source-Secretscan bindet die finalen Arbeitsbytes; [sicherer Ergebnisindex](security/pr9-20261028/source-security.json) enthält keine Matches. [Regressionsbelege](security/pr9-20261028/regression-final.json).

Der finale Core lief ohne MLflow, ML-Worker, Ollama und Grafana. Authentifiziertes HTTPS, falsche CA/Zugänge, Nonces, private Metriken, tatsächlicher Prometheus-Scrape, S3-Backup und strukturierter `LLM_UNAVAILABLE`-Fallback sind geprüft. [Core-Beleg](security/pr9-20261028/core-staging.json), [tatsächliche Container-/Configbindung](security/pr9-20261028/core-config-proof.json). Alle isolierten Projekte wurden gestoppt bzw. Restoreprojekte aufgeräumt. Keine realen Finanzproviderabrufe.

**PR9A ist nicht sicherheitsfreigegeben.** Die verbleibenden realen Reviews, der fehlende Zielhost und getrennte Operatorentscheidung sperren den Release. [Gesamtstatus](PR9_ACCEPTANCE_REPORT.md).
