# PR7 – PostgreSQL-Upgrade und Rückweg

Stand 26.10.2026. Zielkandidat bleibt PostgreSQL 17 mit pgvector 0.8.6.
**Keine produktive Major-Migration autorisiert.** Die PR5-/PR6-Restorebelege
beziehen sich auf ihre damaligen exakten Images, nicht auf einen neuen PR7-Stand.

## Vorher

Quell-/Ziel-Digests, `server_version`, libc (glibc/musl), Encoding,
`lc_collate`, `lc_ctype`, Collationprovider/-version und Extensions erfassen.
Eine Alpine/musl- und eine Debian/glibc-Sortierung sind kein austauschbarer
Vertrag. Bestehende Volumes niemals in das neue Major- oder libc-Image einhängen.

Schreibprozesse kontrolliert stoppen. Unveränderten Quellbestand und
Objektmirror separat sichern; DB-Dump, Bytehashes, Konfiguration und getrennte
Recovery-Schlüssel binden. PostgreSQL-Clientversion muss Quelle lesen und ein
für den Zielserver geeignetes logisches Dumpformat erzeugen können.

## Isolierter Upgrade

1. Neues Volume mit explizit geprüftem Locale/Encoding anlegen; mit separatem
   Benutzer und privaten Credentials logischen Dump restaurieren. Rollen und
   Extensionbereitstellung gehören zur geprüften Restorekonfiguration.
2. `ops/postgres/restore_contract.sql` mit `ON_ERROR_STOP=1` ausführen.
   Es prüft Major/pgvector, Numeric/JSONB, HNSW/GIN, UTC-Zeitstempel,
   Indexgültigkeit, Collationversionen und den PIT-Unveränderlichkeitstrigger.
   Temporäre Testschreibvorgänge werden zurückgerollt.
3. Eine Collationversionsabweichung blockiert die Abnahme. Betroffene Indizes
   nach Herstellerverfahren neu aufbauen und Constraints/Sortierverhalten
   prüfen; erst danach die gespeicherte Collationversion aktualisieren.
   `REFRESH COLLATION VERSION` allein repariert keinen Index.
4. Alembic head/drift und frische Migration separat prüfen; vollständige
   App-Abnahme und archivtreue Hash-/Golden-/Dokument-/UI-Receiptverträge
   mit dem endgültigen Anwendungsimage ausführen.

## Simulierter Cutover und Rollback

Zunächst nur den isolierten synthetischen Anwendungsendpoint umstellen und
Neustart/Login/Lese- und kontrollierte Schreibpfade prüfen. Quelle bleibt
unverändert erhalten. Rückweg vor neuen Zielschreibvorgängen: geprüfte alte
Konfiguration samt altem Image und ursprünglichem Volume wiederverwenden,
nicht das neue Volume durch ein Downgrade öffnen.

Nach neuen Zielschreibvorgängen ist ein einfaches Zurückschalten kein
verlustfreier Rollback. Änderungen inventarisieren, Wiederherstellungspunkt
und Verlustfenster explizit prüfen; gesonderte Operatorentscheidung nötig.
Kein automatischer Rückimport in das ältere Major und keine Quelllöschung.

Maßgebliche Herstelleranleitung: [PostgreSQL – Upgrading](https://www.postgresql.org/docs/17/upgrading.html),
[Collationverwaltung](https://www.postgresql.org/docs/17/collation.html).
Der neue PR7-Vertrag und Ablauf müssen noch gegen den endgültigen isolierten
Restore ausgeführt werden; diese Anleitung behauptet keinen solchen Erfolg.
