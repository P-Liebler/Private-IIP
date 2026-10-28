# PR8A – Release-Security

Stand: 27.10.2026. **SECURITY_BLOCKED / NOT_APPROVED**. Keine Ausnahme erteilt.

## Tatsächlicher Remote-Endzustand

Commit und `origin/main`: `f848dc55afd2cbafeaea5a5a08f0840d27585ca7`.
Der ausdrücklich angeforderte [GitHub-Lauf 40475316877](https://github.com/P-Liebler/Private-IIP/actions/runs/40475316877) ist beendet: **Verify success, Security failure**. Der erneute Connectorabruf ist in [remote-ci.json](security/pr8-20261027/remote-ci.json) erhalten.

Scannerinstallation, frische DB, Cache, Offline-Verträge, Dependency-Audits, neue API-/Web-Scans und deren SBOMs waren erfolgreich. Der historische PR4-Critical-Gate scheiterte; der Status-Step meldete zusätzlich `IMAGE_VULNERABLE`. `full_inventory=false`, vollständiger Operator-Audit übersprungen. Erfolgreicher Download bedeutet somit weder saubere Images noch Releasefreigabe. Die PR8-Arbeitsänderungen wurden nicht gepusht; dafür existiert keine neue Remote-CI.

## Historie und aktiver Umfang

PR4-Inventar und Befunde bleiben unverändert. Der neue historische Reporter speichert Status und SHA-256 des Originals als `HISTORICAL_ONLY` mit `NOT_APPROVED`; er bewertet keine heutigen Images. [Historischer PR4-Beleg](security/pr8-20261027/pr4-historical-policy.json).

Der aktive Vertrag ist [pr8-core-v1-scope.json](../ops/releases/pr8-core-v1-scope.json). Er bindet **13 notwendige Services / 9 unterschiedliche Images** einschließlich Backupclient und isoliert ausgeführtem Legacy-Modell-Verifier. Ausgeschaltete ML-/LLM-/Grafana-Dienste und die ausschließlich als Migrationsquelle erhaltene alte Serverinstanz sind getrennt bezeichnet. Aktivierung einer Option ohne passenden Scope/Scan führt zu `SCAN_INCOMPLETE`.

`release_scope.py` prüft Servicevollständigkeit, Recovery, exakte Referenzen und Digests sowie die tatsächliche Compose-Konfiguration ohne Builds. Die bisherige High-/Critical-Policy bleibt wirksam. Der normale CI-Paketgate wurde von Critical-only auf High **und** Critical verschärft. Historische Befunde sind weiterhin sichtbar, werden aber nicht als aktueller Scan ausgegeben. Der CI-Build-Kompatibilitätsbestand und der neue Core-Releasebestand sind unterschiedliche Prüfbereiche.

## Aktueller exakter Kandidatenbestand

[Core-RC3-Inventar](security/pr8-20261027/core-rc3/inventory.json) und [13 formal validierte SBOMs](security/pr8-20261027/core-rc3/sbom-validation.json) binden den endgültigen lokalen Core-Kandidaten. RC1 und RC2 bleiben separat erhalten. RC3 enthält das neue Web mit Nonce-CSP, den unveränderten erforderlichen Archiv-Verifier und den vollständig als Backup-/Restorewerkzeug geprüften separaten MC-Client. Unveränderte Images verwenden ihre exakten PR8-Scanoriginale derselben validierten DB; es wird kein erneuter Build behauptet.

| Image / Verwendung | Critical | High | Entscheidung |
| --- | ---: | ---: | --- |
| Backend; API/Worker/Scheduler | 0 | 44 | Offen; ein gemeinsames Image, nicht 132 verschiedene Befunde |
| Separater MC-Client; Backup/Restore | 0 | 0 | Technisch abgenommen; zusätzlich 0 Medium und 1 Unknown, keine pauschale Securityfreigabe |
| Unveränderter historischer Modell-Verifier | 1 | 47 | Erforderliche isolierte Archivprüfung; kein live eingesetztes API-Image, trotzdem im Recovery-Scope |
| Web mit Nonce-CSP | 0 | 0 | Paketprüfung bestanden; keine pauschale Securityfreigabe |
| PG17, Valkey, SeaweedFS, Caddy/CA-Export/Init, Prometheus | 0 | 0 | Paketprüfung bestanden; übrige Schweregrade und manuelle Gates im Inventar erhalten |

Scanner: checksumgeprüfter Trivy 0.76.0. DB-Akquisition/Validierung: `backups/pr8-db-acquisition.json`; DB-Stand **27.10.2026 07:13:33 UTC**, identischer DB-Hash ist pro Scan gebunden. Originale Scannerantworten liegen privat unter `backups/pr8-core-scans-v1`, `pr8-web-nonce-scan`, `pr8-legacy-verifier-scan` und beim separaten Clientscan. Der RC3-Nachweis führt ausschließlich diese exakten Originale zusammen. Paket-/SBOM-Originale und alte Versuche wurden nicht überschrieben.

## Konkrete verbleibende Befunde

Die 44 Backend-High-Zeilen betreffen 17 installierte Binärpakete aus util-linux, acl, ncurses, systemd und perl. Derselbe Quellpaketbefund erscheint in mehreren Binärpaketen; Zeilen sind keine unabhängigen CVEs. Installierte/feste Version, Paketpfad, Digest und Advisory stehen für jede Zeile im Inventar.

Am 27.10. geprüft: [Debian util-linux CVE-2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642) führt Trixie `2.41.5-0+deb13u1` als betroffen, Unstable als behoben. [Debian acl CVE-2026-54369](https://security-tracker.debian.org/tracker/CVE-2026-54369) führt Trixie `2.3.2-2` als betroffen und verweist auf die neue ABI in 2.4.0. Ein Wechsel auf Sid oder eigenmächtiges Entfernen fundamentaler Laufzeitbibliotheken ist kein validierter Patch. Numerische Modellpins und alte Runtime-Manifeste bleiben unverändert.

API/Worker laufen unprivilegiert, mit `cap_drop: ALL`, Read-only-Root und ohne Host-Dateisystem-/Docker-Socket-Zugang. Im vorgesehenen Container gibt es keinen privilegierten mount-/systemd-Dienst. Das begrenzt konkrete Angriffswege, beseitigt die Paketbefunde jedoch nicht. App-, native Bibliotheks- und Host-Reachability sowie verbleibende ncurses/perl/systemd-Advisories benötigen weiterhin Review; keine automatische Nichtbetroffenheitsbehauptung.

Der alte Modell-Verifier enthält unter anderem **certifi 2026.7.22 / GHSA-6q48-6c7w-9gw2**, Fix laut Scan **2026.10.18**. Seine Netzverbindung ist technisch vollständig ausgeschaltet; dessen Originalversion zu patchen würde den archivierten Dependency-Vertrag verändern. Dies erfordert einen belegten, ausdrücklich genehmigten und befristeten Ausnahmeentscheid oder einen separat validierten kompatiblen Archivprüfweg. Der tatsächliche Critical bleibt sichtbar.

Der alte MinIO-Server mit neun Criticals und 125 Highs bleibt ausschließlich als Entwicklungs-/Migrationsquelle dokumentiert. Das Core-Profil benötigt sein Gesamtimage weder im laufenden Betrieb noch für Backup/Restore. Der Ersatz ist exakt `private-iip/mc@sha256:a6648014767c128e3bbc04bae0d731c1426413bfa4a64d9e451085ea872eda0f`: archivierter offizieller MC-Commit `77f82e18b5401a65958f1619df6ebb994634bd88`, gebaut mit Go 1.27.3 und sechs gezielten Dependency-Fixgruppen gemäß `ops/mc/Dockerfile.pr8`. Der Scan meldet 0 Critical/High/Medium und 1 Unknown. Dies ist keine Behauptung einer vollständig modernisierten Upstream-Implementierung oder reproduzierbaren Buildattestation.

Der Client lief als UID10001 mit eigener Tmpfs-Konfiguration, strikt geprüfter CA und Read-only-Mount der öffentlichen CA. Fehlende verpflichtende CA wurde abgewiesen. Tatsächliches Zielbackup und anschließender unabhängiger Restore mit **1383 geprüften Dateihashes** bestanden; [technischer Nachweis](PR8E_CORE_ACCEPTANCE_REPORT.md). Die unveränderten Altbefunde werden durch diesen Ersatz nicht als behoben umgedeutet. Der weiterhin erforderliche historische Modell-Verifier bleibt ein eigenständiger Critical-Blocker.

## Native Pfade, Herkunft und Browserpolicy

Die [PR7-Upstreamprüfung](security/PR7_UPSTREAM_ADVISORY_REVIEW.md) und negativen S3-/gRPC-/Policyprobes bleiben zum identischen Seaweed-Digest relevant. Das offizielle 4.51-Tag und die im Image gemeldete Revision unterscheiden sich; der dokumentierte Quellabgleich ist keine reproduzierbare Buildattestation. Keine willkürliche Native-Code-/GPU-Sicherheitsbehauptung. Storage-Listener bleiben im separaten Netz; nur der S3-Proxy ist aus dem Appnetz erreichbar.

Der neue Web-Kandidat erzeugt pro Antwort einen frischen Skript-Nonce nach dem [Next.js-Vertrag](https://nextjs.org/docs/app/guides/content-security-policy). Clientseitig mitgelieferte Nonces werden ersetzt, Antworten sind `private, no-store`, Produktionsskripte erlauben weder `unsafe-inline` noch `unsafe-eval`. Core-Caddy erhält diese Antwortpolicy. Das alte Caddy-Profil bleibt als Historie unverändert. Der vollständige Browserlauf besteht mit **30/30**; der tatsächliche Parser-Injektionstest und sein anfänglich ungeeigneter DevTools-Versuch werden im Core-Abnahmebericht getrennt ausgewiesen.

**Styles erlauben weiterhin `unsafe-inline`**, weil Radix/Charts Styleattribute verwenden. Das ist kein geschlossener vollständiger CSP-Gate. Die endgültige Styles-/Expositionsentscheidung, Buildzuordnung, native Grenzen, alle relevanten Paketbefunde sowie unabhängige Securityreview bleiben offen.

Eine Ausnahme benötigt weiterhin den bestehenden vollständigen Vertrag: CVE, Komponente, exakter Digest, technische Begründung, Reachabilitybeleg, Maßnahmen, benannter Reviewer, tatsächliche Freigabereferenz, Beginn, Ablauf und Neubewertungstrigger. Hier wurde kein Feld als Operatorfreigabe erfunden. **Private Core V1 bleibt gesperrt.**
