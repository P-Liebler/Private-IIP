# PR4 – SBOM-Inventar

## Aktueller Nachweis vom 21.10.2026

Aktuelle zehn originale CycloneDX-SBOMs liegen unter pr4-20261021/packages; ihre Hashes und formale Schema-Pruefung sind im neuen Inventar gebunden. Alte SBOMs und RC-Nachweise bleiben historische Snapshots. Fehlgeschlagene oder manipulierte Originalscans bleiben SCAN_INCOMPLETE.

[Neue Abnahme und priorisierte Restarbeit](../PR4_ACCEPTANCE_20261021.md). Die folgenden Angaben vom 19./20.10. bleiben als historische Nachweise erhalten; sie sind nicht der aktuelle Sicherheitsstand.


Stand: 20.10.2026. Zehn unveränderte CycloneDX-1.7-SBOM-Dateien des geprüften Endbestands. Offline gegen die offiziellen, lokal versionierten Schemas validiert. Ein SBOM ist ein Paketverzeichnis, keine Security-Freigabe.

| Komponente | Image-/Index-Digest | SBOM und SHA-256 |
|---|---|---|
| caddy | `sha256:39e9211b2021e423f69240fdd9d52803bbe8dc9a595e20deb29583253fe511d4` | [caddy.cdx.json](pr4-release/caddy.cdx.json)<br>`a9a3743a44dd9f21fee8fc0a23407ea71092e1d29ca9f92a70b571408410b7f1` |
| postgres | `sha256:72b5b100d4271206baa9d3ca49c451766dcd163077d17264dd3c183720465bb2` | [postgres.cdx.json](pr4-release/postgres.cdx.json)<br>`48f9dbaed90dd7918ad1ded75a90c2a9d8fc6fced832c60f2b9be00a7e35f03b` |
| valkey | `sha256:081c2f5cb575efc901aa80ff9cdbd1ec6a301682fd35e1ebb4b0990a4a4a8507` | [valkey.cdx.json](pr4-release/valkey.cdx.json)<br>`df65d9b370bc88c8c3da9c53f3bf415eae3d7f324500142b645f3ea721c7adea` |
| minio | `sha256:69b55a1c1c5dc285ce04db96689f5b2102317fc77a50680a1874ca6efd1c87f9` | [minio.cdx.json](pr4-release/minio.cdx.json)<br>`e2b87d711c688506e1433b9baa3075199461639be4c02e86e34d19d8a9f3bdce` |
| backend | `sha256:c35ab504013cc24d66b65eb2bdf88b1a3f23dac91a0b5377536d932d1d6540bd` | [backend.cdx.json](pr4-release/backend.cdx.json)<br>`499f6d6e1a4ba3f57de7a0de26c12cd94c0385a57fbbb3e9792242bdc158d60f` |
| web | `sha256:4979e27f92f3bd0f85577f6857e44086ee4bf6aa67a8476507c494ee3d874166` | [web.cdx.json](pr4-release/web.cdx.json)<br>`f7e8f7c1ef8199b9729f3044a808353e5e994f8490fa35956fc1ca485487c24c` |
| prometheus | `sha256:efd719c99d83b060d9daefdcf00360461adf279f45ef5391f8d111892118753e` | [prometheus.cdx.json](pr4-release/prometheus.cdx.json)<br>`847e8e5f41fdc636036380850a1c6bbdbb309cca125cf26393c06097ae670888` |
| grafana | `sha256:41bbc1b5e04416f81891806076db2a2ff60a5d4da5f78d36a88b033a8c199185` | [grafana.cdx.json](pr4-release/grafana.cdx.json)<br>`da207762dfb60cf14e74edf750f009429e883d390e9b741c7fb50fab3bd06801` |
| mlflow | `sha256:bdf7904ce56c1836755c238247e526a82920a54caf146053822876d67e57ad66` | [mlflow.cdx.json](pr4-release/mlflow.cdx.json)<br>`944d59a7ea324cbea6d8ccc15b161ba6ea6720f3fe64b671c920a5e8edaa58c2` |
| ollama | `sha256:926d40fd6eeeebd346b5c358a63de2a10ec995371cd93dd22f1843200694b1a6` | [ollama.cdx.json](pr4-release/ollama.cdx.json)<br>`09a240ed1e7cefc43bdfcfb823f2251cc09f8eac8a7add2dec2adeae8b561343` |

Der getrennte Config-Digest, Architektur, Scannerbinary-Hash, DB-Metadaten und alle Befunde stehen im [Imageinventar](PR4_IMAGE_INVENTORY.json). Docker-Manifest-/Index-IDs und Image-Config-Digests werden nicht gleichgesetzt. Die [formale Validierung](pr4-release/sbom-validation.json) bindet dieselben originalen SBOM-Bytes; die Baseline bleibt in [pr4-baseline](pr4-baseline/inventory.json) separat erhalten.

Der erste abschließende Ollama-Dockerexport lief ins Zeitlimit und bleibt `SCAN_INCOMPLETE`. Ein separater vollständiger Registry-Paketlauf verwendete den unveränderten Registry-Digest, die zuvor exportverifizierte Config und dieselbe Plattform mit aktualisierter DB. Nur dieser abgeschlossene Lauf liefert das finale Ollama-SBOM; der fehlgeschlagene Export wurde nicht umetikettiert. Nicht beliebig unterstützte native Libraries bleiben manuell zu prüfen.

Die gemeinsame Backend-SBOM gilt für API, Worker, Scheduler und ML-Worker nur bei identischem Image-Digest. Caddy/CA-Export und MinIO/Backup teilen ebenfalls identische Imagebytes. Der [beobachtete Laufzeitbestand](PR4_RUNTIME_INVENTORY.json) verknüpft diese Rollen mit dem Audit.

Separate S3-Prototypprüfung, kein produktiver Bestand: [SeaweedFS-SBOM und Scan](pr4-s3-prototype/inventory.json). Kein automatischer Speicherwechsel.
