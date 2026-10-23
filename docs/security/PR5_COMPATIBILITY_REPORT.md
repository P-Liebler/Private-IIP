# PR5 – Sicherheits- und Laufzeitkompatibilität

Stand: 22.10.2026. Technische Prüfungen sind keine Sicherheitsfreigabe.

| Vertrag | Tatsächlich geprüfter Umfang |
| --- | --- |
| Gepatchter Core | certifi2026.10.19, pypdf6.21.1; numerische Pins unverändert; API/Celery-Startguards, neues Runtime-/Parsermanifest; pip check im Build |
| Historisches Modell | Originalhash `9706d2dc2631d0cfde24ddaad3ccd4f41b686351cd5b82ecd5e0a96fc18f5c94`; normaler Dependency-Gate verweigert alten Vertrag, getrenntes exaktes Archivimage prüft ohne Netzwerk |
| TLS/HTTP/S3 | Tatsächliches httpx und MinIO-SDK aus finalem Coreimage gegen eigenen privaten TLS-Server; gültige CA akzeptiert, fremder Trust abgewiesen, authentifizierte Objektbytes/Hash stimmen. Keine TLS-Verifikation deaktiviert |
| S3-Übertragung | boto3, Range, Streaming, Multipart-Abbruch nach bestätigtem Part und Wiederaufnahme in neuem Prozess; Metadaten/SHA-256, lokaler Mirror und frischer Restorebucket; eigene synthetische Volumes |
| Datenbank | Isolierter logischer Restore PG17.11/pgvector0.8.6; JSONB, numeric(28,8), Vektordistanz, HNSW/GIN-Indizes, abgewiesene PIT-Updates in zurückgerollter Transaktion |
| Historie | Originaler P6-Hash und P7-Artefakt unverändert; aktuelle P8/P9/P10/PR1/PR2-Checkpointverträge; Golden CHF10'180. Keine alten Modell-/Manifestbytes umgeschrieben |
| Anwendung | Vollständige lokale Backend-/Host-/Browserregression sowie Standalone-Build. Konkrete letzte Laufzeiten und Restorehashes stehen im [Abnahmebericht](../PR5_ACCEPTANCE_REPORT.md) |

PostgreSQL meldet im synthetischen Restore `en_US.utf8` für LC_COLLATE/LC_CTYPE. Gleicher Name unter musl und glibc beweist keine gleiche Sortierung. Ein produktiver Basiswechsel braucht logischen Dump/Restore, Reindex-/Kollationsreview und eigene Abnahme mit tatsächlichen Daten. Originalvolumes bleiben erhalten.

Zusätzlich zur unverändert lesbaren Quelle schaltet die tatsächliche App-Storagefactory in einem eigenen Testprozess von synthetischer Quelle zu Ziel und zurück. Nach jedem Wechsel werden Raw-, Modell- und Dokumentbytes über TLS erneut gelesen und gehasht; Settings-/Storage-Caches werden neu aufgebaut. Kein produktiver App-Cutover. Version-IDs, Object-Lock/Retention, Multiuser-Isolation, reale Langzeitkapazität und produktive Rückschaltung sind nicht als bestanden ausgewiesen. Ein erfolgreicher synthetischer App-Restore ist keine Erlaubnis zur produktiven Migration.
