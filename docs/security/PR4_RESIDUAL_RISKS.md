# PR4 – verbleibende Risiken

Stand: 20.10.2026. **SECURITY_BLOCKED; keine genehmigten Ausnahmen.** Diese Bewertung ist keine Produktionsfreigabe. Scannerbefunde und technische Laufzeitbelege sind getrennt; ein privates Netz ersetzt keinen Patch.

| Priorität | Risiko | Erforderlicher Abschluss |
|---|---|---|
| P0 | MinIO: archivierter Upstream, offene Critical-/High-Paketbefunde; S3 verarbeitet unverzichtbare Raw-/Modell-/Dokumentbytes | Tragfähiger gepflegter Patchpfad oder separat geprüfter Speicherwechsel mit Operatorentscheidung; vollständige SDK-/TLS-/Backup-/Restore-/Migrationsabnahme |
| P0 | PostgreSQL-Image: trotz OS-Patches verbleibende Critical-/High-Befunde | Exakte Paket-/Codepfadbewertung oder kompatibler Patch; genehmigte Behandlung aller relevanten Critical-Befunde; kein blinder Majorwechsel |
| P1 | Backend/MLflow und Monitoring: verbleibende OS-/Go-Paketbefunde | Digest-genaue Behandlung und erneute Kompatibilitäts-/Security-Prüfung; keine numerischen Lockänderungen zur kosmetischen Befundreduktion |
| P1 | Ollama: Paketbefunde sowie unvollständige automatische Zuordnung nativer CUDA-/cuDNN-/GGML-/MLX-Komponenten | Hersteller-/Build-/Dateiversionsprüfung und dokumentierte Abdeckungsgrenzen; ohne Nachweis keine Nullbefund-Behauptung |
| P1 | Next.js-CSP erlaubt weiterhin `unsafe-inline` | Getrennte, tatsächlich funktionsgeprüfte Nonce-/Renderingstrategie; XSS-Restbewertung bis dahin offen |
| P0 Zielbetrieb | Tatsächlicher Host, VPN/Firewall/DNS, Client-CA-Trust, unabhängiges Backup/Recovery und Alarmzustellung fehlen | Echte Operatornachweise, unabhängig vom lokalen Security-Audit |

## Konkrete PostgreSQL-Paketprüfung

Der erste gepatchte Bookworm-Kandidat enthält PostgreSQL 17.11 und pgvector 0.8.6. Der unterstützte Paketlauf meldet unter anderem diese Critical-Paare; die vollständigen exakten Versionen und neuen DB-Befunde müssen aus dem endgültigen Inventar gelesen werden:

- `libsqlite3-0` / CVE-2025-7458: [Debian](https://security-tracker.debian.org/tracker/CVE-2025-7458) führt die geprüfte Bookworm-Version als betroffen. Die [SQLite-Einordnung](https://www.sqlite.org/cves.html) beschreibt Voraussetzungen wie fremdes SQL oder manipulierte Datenbanken. Diese Voraussetzungen sind zu prüfen und begründen allein keine Nichtbetroffenheit.
- `libxml2` / CVE-2026-6653: [Debian](https://security-tracker.debian.org/tracker/CVE-2026-6653) führt die geprüfte Bookworm-Version als betroffen. PostgreSQL kann XML-Funktionen bereitstellen; keine pauschale Behauptung eines unerreichbaren Codepfads.
- `zlib1g` / CVE-2023-45853: Der [Debian-Tracker](https://security-tracker.debian.org/tracker/CVE-2023-45853) unterscheidet das Quellpaket vom Bookworm-Binärpaket; der betroffene contrib/minizip-Code wird dort nicht gebaut. Diese Primärevidenz ist für genau dieses Paket relevant und als manuelle Prüfung festgehalten. Sie ist keine pauschale Ausnahme für alle zlib-/Go-/MinIO-Befunde. Der rohe Scannerbefund bleibt sichtbar und wird ohne formalen digestbezogenen Review nicht aus dem Release-Gate entfernt.
- `stdlib` in `/usr/local/bin/gosu` / CVE-2025-68121: Der tatsächliche Dateipfad wurde im Scan identifiziert. [Gosu](https://github.com/tianon/gosu/security) weist auf compilerbezogene Befunde ohne entsprechenden verlinkten Code hin. Ob der konkrete TLS-Pfad im geprüften Binary vorhanden/erreichbar ist, benötigt einen Build-/Binarynachweis; hier nicht automatisch als False Positive verworfen.

Technische Sichtung: Codex, 20.10.2026. **Operativer Security-Reviewer und Genehmigung: ausstehend.** Keine CVE wurde allein wegen fehlendem Patch oder fehlendem Hostport akzeptiert.

## Nachweisgrenzen

Ein vollständiger Image-Paketlauf umfasst unterstützte OS-/Sprachökosysteme, nicht jede beliebige statische native Library. Scanner-/DB-Stand, tatsächliche Image-/Config-Digests und SBOM-Hashes sind erforderlich. Der aktualisierte Scanner kann neue Befunde zeigen, obwohl die Software unverändert ist. CVE-Differenzen zwischen Baseline und Endbestand sind deshalb keine alleinige Exploit- oder Behebungsbehauptung.

Eigene Caddy-/PostgreSQL-Builds verlangen dauerhafte Wartung und erneute Scans. Gepinnte Basis-Digests und archivierte Endimages machen den geprüften Bestand identifizierbar; veränderliche Paketquellen garantieren keine bitidentische spätere Neuerstellung. Deployment darf die geprüften Images nicht neu bauen.

Quellenrechte, historische Datenverfügbarkeit, reale Modell-/Strategievalidierung und finanzielle Freigaben bleiben separat: `REAL_DATA_LIMITED`, `FORECASTS_SHADOW_ONLY`, `RECOMMENDATIONS_GATED`.
