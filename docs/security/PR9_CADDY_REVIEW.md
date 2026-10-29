# PR9 – Caddy: verbleibender Paketbefund

Prüfung: **28.10.2026**. **DRAFT_NOT_APPROVED / SECURITY_BLOCKED**.

## Exakter Umfang und tatsächlich behobene Befunde

Finaler Kandidat: `private-iip/caddy@sha256:6416b8c2e10d8d62b131dbf3755c01069d7b3dcdb7af720b76c8aeed8bc9dcaf`, verwendet von Caddy, CA-Export und einmaligem Storage-Init. Die drei Dienste verwenden dieselben Imagebytes; ihre Befunde sind keine drei unabhängigen Schwachstellen.

Der [frische vollständige Scan](pr9-20261028/core-rc1/inventory.json) mit Trivy 0.76.0 und Datenbank vom 28.10.2026 meldet **0 Critical, 1 High, 1 Medium und 1 Unknown**. Unterstützte Paketanalysatoren beweisen keine vollständige native Exploitabilityprüfung. Niedrigere oder unbekannte Schweregrade bleiben sichtbar und reviewpflichtig.

[Dockerfile.pr9](../../ops/caddy/Dockerfile.pr9) baut aus dem exakten offiziellen Caddy-v2.11.7-Commit `72dd0fb067f6d7826c7f79907670ba4a713bfe37` mit geprüften Archivbytes und gepinntem Go-Builder. Es aktualisiert `go-jose/v4` auf **4.1.6** und `golang.org/x/net` auf **0.62.0**. Beide zuvor behebbaren High-Paketpfade sind im finalen Scan geschlossen. Go-Modulmanifest, Summen, Lizenz und Sourcecommit liegen im Image. Die unveränderte Runtimebasis ist der archivierte Caddy-Digest `3c8c26…`; dies ist ein separat gebautes lokales Image, keine Behauptung identischer offizieller Binarybytes. [Quellbeleg](pr9-20261028/go-source-review.json).

## Verbleibendes High: tatsächliche Entscheidung erforderlich

| Feld | Befund / Reviewstand |
| --- | --- |
| ID | **CVE-2026-116587 / GHSA-mgcc-cww5-fp2q** |
| Paket / Binary | `github.com/go-jose/go-jose/v3` **v3.0.5**, `/usr/bin/caddy` |
| Fixstand | Für v3 nennt das [Maintainer-Advisory](https://github.com/go-jose/go-jose/security/advisories/GHSA-mgcc-cww5-fp2q) keinen gepatchten Release. Der v4-Fix ersetzt die separate v3-Abhängigkeit nicht. |
| Angriffspfad | Präparierte RSA-JWK kann unter Go ab 1.24 übermäßig CPU beanspruchen. Paketpräsenz belegt noch keinen erreichbaren externen JWK-Eingang im konkreten Coreprofil. Nichterreichbarkeit ist ebenfalls **nicht bewiesen**. |
| Coreexposition | Caddy verarbeitet private TLS-/HTTP-Anfragen am VPN-Bind und interne S3-TLS-Anfragen; interne CA ist aktiv. Kein öffentlicher Zielhost wurde geprüft. CA-Export/Storage-Init führen Shellhilfen aus, keine Caddyserver-Binary; sie bleiben dennoch im vollständigen Imageinventar. |
| Vorhandene Grenzen | Digestpin, read-only Root, reduzierte Fähigkeiten, begrenzte Ressourcen, private Netze, kein Docker-Socket. Diese Grenzen sind kein Patch und keine automatische Ausnahme. |
| Nächste technische Maßnahme | Unterstützten v3-Fix bzw. vollständige Upstream-Abhängigkeitsmigration verfolgen; dann neue Binary, neuer vollständiger Scan, TLS-/S3-/Browser-/Core-/Restoreabnahme. Keine ungeprüfte Modulmajor-Substitution. |
| Benötigter Review | Autorisierte Person muss konkrete JWK-Eingänge, interne CA/ACME-Abhängigkeiten, DoS-Exposition, Ressourcen-/Neustartverhalten und sämtliche verbleibenden nativen/Unknown-Funde beurteilen. |
| Dauer / Re-Review | Keine Laufzeitfreigabe erteilt. Falls eine Ausnahme vorgeschlagen wird: konkretes Enddatum, maximaler Zweckumfang, Reviewer und Genehmigungsreferenz vor Start ergänzen; bei neuem Fix, Konfigurations-/Netz-/Binarywechsel oder neuem Advisory sofort erneut prüfen. |
| Entscheidung | Reviewer, Freigabe und Gültigkeitszeitraum **fehlen**. `SECURITY_BLOCKED` bleibt bestehen. |

Ein laufender lokaler synthetischer Test ist keine Produktionsausnahme. Der unabhängige [Legacy-Recoveryblocker](PR9_LEGACY_VERIFIER_REVIEW.md) bleibt zusätzlich erhalten.
