# PR7B – isolierte Storage-/PostgreSQL-Abnahme

27.10.2026. **ISOLATED_SYNTHETIC_ACCEPTANCE_VERIFIED / NO_PRODUCTION_APPROVAL**.

## Migration und Datenbank

Bevorzugter Kandidat bleibt SeaweedFS4.51, nach dem
[Vergleich mit MinIO/AIStor, Garage und Ceph](operations/PR7_STORAGE_DECISION.md).
Kein Produktionswechsel, kein PostgreSQL-Major-Upgrade im bestehenden Bestand.
Das eigene neue PostgreSQL17-Staging erhielt den konsistenten Quelldump;
UTC/Numeric/JSONB/Collation-/Index-/pgvector-/PIT-Verträge bestehen.

Das [allgemeine Migrationstool](operations/PR7_S3_MIGRATION.md) bestand den
vollständigen lokalen synthetischen Bestand:683 Originalobjekte/Versionseinträge,
323 DB-Referenzen, unveränderte Quelle, Prozessunterbrechung/Wiederaufnahme,
idempotente Wiederholung, Metadaten/Tags und vollständige SHA-Rereads.
Die vollständige Quelle war UNVERSIONED. Native Quellversionen/Löschmarker
wurden zusätzlich in einem separaten echten S3-Vertrag mit sechs Einträgen
geprüft. Archivnamespace, Manifest und Journal erhalten ursprüngliche
Identität/Verfügbarkeit; neue native Ziel-Version-IDs sind ausdrücklich anders.

Alle anfänglichen DB-Archivhashes stimmen überein. Raw-, Modell- und PDF-
Originale bestehen Quelle→Ziel→Quelle über die echte Appfactory. Vier leere
Remote-gRPC-Adminanfragen wurden mit16 abgelehnt; verweigerte PUT-/POST-Uploads
mit403. Native Versionierung/COMPLIANCE-Retention schützen die konkrete Version;
Originalbytes bleiben lesbar. MLflow3.17.2 besteht Auth-/Artefakt-/Bild-Roundtrip,
Jobs bleiben aus. Native Embeddings/RAG pinnen Ollama0.40.11 und verwerfen
Retrieval vor tatsächlicher lokaler Verfügbarkeit. [Netze und Probes](operations/PR7_SYNTHETIC_STAGING.md).

## Neuer Zielbackup und vollständiger Restore

Set 20261027T073831Z-54136 umfasst **1372 Objektdateien einschließlich expliziter
Archivkopien, acht Migrations-/Checkpointbelege und einen DB-Dump:1381 Hashes**.
Die Zahl ist keine Behauptung von1372 verschiedenen Finanzoriginalen.
Alle Dateien und alten P6/P7-/P8–P10-/PR1/PR2-Verträge sowie separate PR6-
Dokumentrückzugs-/UI-Beleghashes bestehen. Exakter alter Modellruntime zusätzlich
ohne Netzwerk/read-only geprüft. PostgreSQL17-/Seaweed-Restore und Cleanup bestehen.
Beleg: `backups/s7-v1/runtime/restore-status.json`.

Nach dem ursprünglichen Sourcecheckpoint kamen genau eine synthetische
Dokumentquelle und eine Kursversion hinzu. Der frühere Restore verweigerte
deshalb korrekt den alten globalen Collectionhash. Vergleich mit einem separat
wiederhergestellten eingefrorenen Quelldump: sämtliche ursprünglichen Zeilen
unverändert, keine entfernten Zeilen und keine Quellenfreigabeänderung.
Neuer Post-QA-Checkpoint samt überprüftem Delta liegt im Backup; alte Checkpoints
und alle anderen Hashverträge bleiben erhalten. Kein alter Hash wird umgeschrieben.

Der feste ursprüngliche Cutoff26.10.2026 15:18:05.987683 UTC ergibt exakt
**CHF10’180**. Für heute meldet derselbe alte Bestand korrekt **PARTIAL/STALE_PRICE**,
Gesamtwert `null`. Der Restore fordert beide Ergebnisse ausdrücklich an;
Freshness wird nicht gelockert. Ein eigenes frisches synthetisches Portfolio
besteht die aktuelle HTTPS-Bewertung mit CHF10’180 separat. Fehlgeschlagene
Versuche und der26.10.-Restore mit640 Objekten/641 Hashes bleiben historische Belege.

DB- und Store-Ausfall liefern503-Readiness. Nach jedem Neustart besteht die
aktuelle frische Goldenbewertung; Login mit falschem Passwort und widerrufener
Session werden401 abgelehnt. Optionale Modellabwesenheit bleibt nutzbar.
Alle Stagingdienste sind nach der Abschlussprobe physisch gestoppt.

## Grenzen

Der Dateimirror erhält aktuelle Keys und explizite Quellversionsarchive; er
behauptet keine identischen nativen Ziel-Version-IDs oder den Inhalt anderer
QA-Testbuckets. TLS endet am privaten Gateway; keine mTLS-Gesamtabnahme.
C: ist das autorisierte lokale QA-Laufwerk, kein unabhängiges Produktionsbackup.
Native Advisory-/Buildattestation, Operator-/Zielhost-/Client-CA-/Schlüssel- und
Backupzeitplanentscheid bleiben getrennt offen. Paketbefunde und konkrete
Authprobes ersetzen keine allgemeine Securityfreigabe.
