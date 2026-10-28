# PR8B – privates Core-Deployment

Stand: 27.10.2026. **KANDIDAT, NICHT FREIGEGEBEN.** Kein produktiver Cutover, keine Änderung an Originalvolumes. Zielhost weiterhin nicht verfügbar.

## Bestand und Funktionsgrenzen

Der neue Overlay `ops/docker-compose.core.yml` ergänzt `docker-compose.prod.yml`. Alle Images sind digestgebunden; sämtliche Build-Einträge werden entfernt. `ops/releases/pr8-core-v1-scope.json` unterscheidet Laufzeit, Recovery, ausgeschaltete Optionen und Migrationsquelle. Der unveränderte alte Produktions-Compose ist das Legacy-Profil, nicht automatisch der neue Release.

| Dienst | Core-Zustand / Zweck |
| --- | --- |
| Caddy, CA-Export, Web, API | HTTPS, interne CA, sichere Session und vorhandene Oberfläche; Nonce-CSP vom Web bleibt erhalten |
| PG17/pgvector | Eigenes neues Volume, exakt gepinnter Kandidat; niemals ein PG16-Datenverzeichnis mit PG17 öffnen |
| SeaweedFS 4.51 | Eigenes `core_seaweed_data`-Volume im internen Storage-Netz; nur S3 über CA-geprüften Proxy erreichbar |
| Valkey, Worker, Scheduler | Persistente Queue/Jobs und regelbasierte Meldungen; externe Collection und Forward SHADOW standardmäßig aus |
| Prometheus | Verpflichtende Grundüberwachung, keine Hostport-Freigabe |
| Backupclient, Storage-Init | Separater gepinnter MC-Client mit strikt geprüfter CA, UID10001 und Tmpfs-Konfiguration; Zielbackup und unabhängiger Restore bestanden. Der alte MinIO-Server ist ausschließlich Entwicklungs-/Migrationsquelle. Init führt ausschließlich CHOWN im neu angelegten Zielvolume aus. |
| Legacy-Modell-Verifier | Vollständiger Archivrestore benötigt das unveränderte alte Runtimeimage. Nur isolierte Read-only-Verifikation mit `network none`, niemals Application Runtime. Auch dieses Image wird gescannt und bleibt im erforderlichen Sicherheitsumfang. |
| MLflow, ML-Worker | Separates Profil `ml`; neue Trainings-/Trackingfunktionen ohne diese Dienste nicht verfügbar. Kein Modell darf dadurch in Produktion gelangen. |
| Ollama | Separates Profil `llm`; ohne Modellservice strukturierte Assistenten-Ausfallantwort, keine neue Embedding-/RAG-Modellabnahme. Portfolio, Ledger und Importe benötigen diesen Dienst nicht. |
| Grafana | Profil `monitoring-ui`; ausgeschaltete optionale Oberfläche, keine Voraussetzung für Grundmetriken. Bei Aktivierung eigene Befunde/Scan und geänderten Scope abnehmen. |

Nur Caddy veröffentlicht im Zielprofil VPN-gebundene Ports und besitzt das gesonderte Edge-Netz. App- und Storage-Netze sind intern. Es existiert keine Verbindung zum alten Storage-Netz und kein produktiver Provider-Egress. Ein freigegebener späterer Collector benötigt einen eigens geprüften Netzwerkpfad und einen aktualisierten Konfigurationsbeleg. Vorhandene Rechtegates bleiben zusätzlich wirksam. Lokales Staging nutzte ausschließlich die Loopbackbindung; dies bestätigt keine VPN-Erreichbarkeit des noch fehlenden Zielhosts.

## Installationsfolge für den späteren Operator

1. Ziel-OS, Docker/Compose-Unterstützung, privaten Hostnamen, VPN-Adresse und private DNS-Auflösung festlegen. Client-CA-Vertrauen auf Windows/Android tatsächlich testen. Lokal belegte TLS-Prüfung ersetzt diesen Schritt nicht.
2. In einer geschützten lokalen Environmentdatei die bisherigen Produktionsvariablen setzen; zusätzlich `CORE_S3_CONFIG` als absoluten privaten Dateipfad. Unterschiedliche starke Secrets, TOTP-Schlüssel und Wiederherstellungsweg festlegen. Keine Secrets in Befehlsargumenten, Logs oder Git.
3. Neue eigene Projekt-/Speicherorte und ein tatsächlich unabhängiges geschütztes Backupziel bestimmen. Rechte am S3-Identitätenfile begrenzen. App-Identität und Administrationsidentität trennen; native Admin-/Volume-/Filer-/gRPC-Listener bleiben privat. Retention/WORM nicht allein aus Versionierung ableiten.
4. Exakte Images bereitstellen; fehlende private Kandidaten nicht still aus Tags neu bauen. Bei Architektur-/Buildwechsel neue Scans/SBOMs und Kompatibilitätsnachweise erstellen.
5. Read-only Vorprüfung ausführen:

```powershell
python ops/core_preflight.py --env-file C:/privat/core.env --mode PRODUCTION --inventory docs/security/pr8-20261027/core-rc3/inventory.json --output backups/core-preflight-NEUER-ZEITPUNKT.json
```

Sie prüft Konfiguration, vollständigen Serviceumfang einschließlich Recovery, Digests, lokale Imageverfügbarkeit, S3-Identität, mindestens 8 GiB Docker-RAM und 5 GiB freie Backupkapazität. Das ist eine Untergrenze für den Prüflauf, keine Kapazitätsplanung für ein wachsendes Archiv. DNS/VPN/OS-CA und unabhängige Backupdisk werden ausdrücklich nicht als abgenommen ausgegeben. Es wird nichts gestartet.

Der tatsächliche letzte lokale [Preflight](security/pr8-20261027/core-preflight-v2.json) führte nichts aus und meldet ausschließlich den Konfigurationsfehler `BACKUP_FREE_SPACE_BELOW_5_GIB`: **3’915’988’992 freie Bytes** am geprüften Backupziel. Digest-/Scopezuordnung und übrige geprüfte Konfigurationsbedingungen bestanden. `SECURITY_BLOCKED`, `TARGET_HOST_NOT_VERIFIED` und `NOT_APPROVED` bleiben davon unabhängig bestehen. Auf dem vom Nutzer vorgegebenen C:-Laufwerk ausreichend Platz bereitstellen und dieselbe read-only Prüfung erneut ausführen; keine fremden Daten oder Volumes automatisch löschen.

6. Separate Security-, Host- und Operatorentscheidung mit Beleg, Person, Zeitpunkt und exaktem Manifest prüfen. Solange eines fehlt, endet die Installationsfolge hier. Der ausgegebene Plan ist keine Ausführungsfreigabe. Das bisherige `ops/deploy.py` bedient den Legacy-Vertrag und darf nicht als Core-Installer benutzt werden.
7. Erst nach tatsächlicher Freigabe: neues leeres Storagevolume initialisieren; PG17/Store/Queue/Caddy/CA starten; geprüften SQL-Dump und S3-Vertrag migrieren oder eine ausdrücklich neue leere Installation initialisieren; Alembic aus dem gepinnten API-Image ausführen. Anschließend explizit nur die Core-Laufzeitdienste mit `--no-build --pull never` starten. Keine pauschale Aktivierung aller optionalen Profile.
8. Login/TOTP, Quellen-/Modellgates, Ledger, Markt-/FX-Freshness, Authentifizierung des Storage, Monitoring, Neustart und Diensteausfälle prüfen. Fehlende Modelle bleiben sichtbar unavailable.
9. Zielbackup, isolierten Restore, unabhängigen Backupzeitplan, Schlüssel-Recovery und tatsächliche Alarmzustellung nachweisen. Erst dann echte private Originale aufnehmen.

## Cutover und Rollback

Die bestehenden Werkzeuge `s3_migrate.py`, `export_s3_references.py` und `restore_verify.py` bleiben maßgeblich. Vor Cutover Schreibzugriffe quieszen, zeitgleichen SQL-/Objekt-/Referenzcheckpoint sichern, Versionen/Delete Markers/Metadaten erfassen, Zielinventar lesen, Kopierbelege prüfen und vollständig vom Ziel restaurieren. Ursprüngliche Version-IDs bleiben im Migrationsarchiv; neu vergebene native Ziel-IDs sind keine identischen IDs.

Cutover benötigt eine eigene ausdrückliche Operatorfreigabe. Beim Rollback dürfen seit Cutover entstandene neue Buchungen/Originale nicht verschwinden: neue Writes stoppen und sichern, Delta klären, erst dann freigegebenen vollständigen Stand wiederherstellen. Kein automatisches Umschalten auf ein altes Store-/DB-Volume. Bei ungeklärtem Delta im Wartungszustand bleiben.

## Tatsächlicher lokaler Nachweis

Core-HTTPS mit strikter eigener CA, Login-/Sessionprüfung, synthetischer CHF-10’180-Bewertung, tatsächlichem Prometheus-Scrape und strukturierter Assistentenantwort ohne Ollama bestanden. MLflow, ML-Worker, Ollama und Grafana waren ausgeschaltet. Der vollständige neue Clientbackup-/Restorevertrag besteht mit **1383 Dateihashes**, PG17, SeaweedFS 4.51 und unveränderten archivierten Modell-/P6-Verträgen; Restore-Cleanup erfolgreich. [Core-Abnahmebericht](PR8E_CORE_ACCEPTANCE_REPORT.md).

Der manifestgebundene lokale Kandidat wird unter `ops/releases/pr8-core-v1-rc3-manifest.json` dokumentiert. Sein Status ist **LOCAL_SYNTHETIC_VERIFIED / NOT_RELEASED**; Scope/Images/Scan-/Konfigurationsbelege erteilen keine Security-, Host- oder Operatorfreigabe. Das Manifest ist keine automatische Ausführungsfreigabe.

Die PR7-Verträge und [Storageentscheidung](operations/PR7_STORAGE_DECISION.md) bleiben historische Evidenz. Der Zielhost, unabhängige Backupzeitplan, Schlüssel-Recovery und tatsächliche Alarmzustellung bleiben zur Abnahme offen.
