# Operator-Abnahmeprotokoll

## Offene PR5-Betreiberabnahme (22.10.2026)

- [ ] Sicherheitsreview der finalen Runtime-/Storage-Digests, High-/native-/CSP-Befunde; keine implizite Risikoakzeptanz aus lokalen Tests.
- [ ] PostgreSQL-17-Image-/libc-/Collationentscheidung und Object-Store-Migration einschließlich MLflow, Retention und realer Rückschaltung separat freigegeben.
- [ ] Instrumentbezogene Datenrechte einschließlich automatischem Abruf, Archivierung, Quellenangabe und täglicher Kurs-/FX-/Action-Coverage dokumentiert; regelmäßige Sammlung erst danach ausdrücklich aktivieren.
- [ ] Echter Pilot mit separat bereitgestellten Belegen, Mengen/Cash/FX/Brokerwert und geklärten Abweichungen nach [Pilotprotokoll](../user/REAL_PORTFOLIO_PILOT.md).
- [ ] Zielhost/VPN, Client-CA, unabhängige zeitgesteuerte Backups, Schlüssel-Recovery, Neustart und Alarmempfang tatsächlich nachgewiesen.
- [ ] Neue Remote-CI und finales unveränderliches Manifest geprüft; gesonderte Security-/Zielhost-/Operatorfreigabe vor Produktivstart mit Digest-Images und `--no-build`.

[PR5-Nachweise](../PR5_ACCEPTANCE_REPORT.md). Diese offenen Punkte sind keine Aufforderung, Quellengates oder Finanzvalidierung zu umgehen. Die folgende PR4-Checkliste bleibt historischer Kontext.

## Aktueller Nachweis vom 21.10.2026

[ ] Gepatchte Backend-TLS-Runtime mit strengem Legacy-Modellvertrag abgenommen.

[ ] MinIO-Wartungs-/Migrationsentscheidung und PostgreSQL-Criticals behandelt.

[ ] Neue High-/native-/CSP-Reviews, tatsaechlicher Remote-CI-Pass, frische Digests/SBOMs und neuer RC geprueft.

[ ] Zielhost, VPN/CA, unabhaengige Backups, Recovery, Alarmempfang und Hostneustart separat nachgewiesen. Lokaler RC PR4-LOCAL-20261021-01 ist gesperrt.

[Neue Abnahme und priorisierte Restarbeit](../PR4_ACCEPTANCE_20261021.md). Die folgenden Angaben vom 19./20.10. bleiben als historische Nachweise erhalten; sie sind nicht der aktuelle Sicherheitsstand.


Stand 19.10.2026: **Zielhost noch nicht verfügbar; lokal vorbereiten**. Dieses Dokument ist ein Evidenzprotokoll, kein UI-Schalter und keine Quellen-/Modellfreigabe.

Jeder Nachweis braucht Verantwortlichen, UTC-Zeit, Host-/Clientkennung ohne Secrets, Code-/Image-/Schema-Version, reproduzierbare Schritte, tatsächliches Ergebnis, geschützten Artefaktverweis und verbleibende Einschränkungen. Bei unbekanntem Ergebnis bleibt NOT_VERIFIED; keine leeren Häkchen als Freigabe interpretieren.

| Gate | Aktueller Status | Erforderlicher realer Nachweis |
| --- | --- | --- |
| Zielhost | NOT_VERIFIED | OS, Hardware, Docker/Compose, Dienste, Ressourcen, Uhrzeitsync, unabhängige Staging-/Produktionsvolumes |
| VPN/DNS | NOT_VERIFIED | Privatname, richtige Bindings; positive Windows-/Android-VPN- und negative Außen-/LAN-/IPv6-Tests |
| Client-TLS | NOT_VERIFIED | Beide Clients vertrauen öffentlicher CA, Fingerprints/SAN/Gültigkeit geprüft, keine Browserwarnung |
| Auth | NOT_VERIFIED_ON_TARGET | Login/TOTP/Rate Limit/Sessionablauf/Logout/ungültiger Session-/Fremdzugriff |
| Unabhängiges Backup | NOT_VERIFIED | Tatsächliches getrenntes Ziel, Verschlüsselung, Rechte, Offline-/Retentionnachweis, erfolgreicher Dump+Mirror |
| Tagesjob | NOT_VERIFIED | Installierter Job, echter Identitäts-/NASzugriff, verpasster Lauf, Fehler, Ergebnis und Wiederanlauf |
| Restore | NOT_VERIFIED_ON_TARGET | Neues isoliertes Projekt, alte genaue Hashes, Golden CHF 10'180, Dauer und Cleanup |
| Schlüssel-Recovery | NOT_VERIFIED | Getrennte verschlüsselte Sicherung, TOTP- und CA-/Client-/MinIO-Kontinuität; ausdrückliche Freigabe für echte Secrets |
| Alarmzustellung | NOT_VERIFIED | Gewählter Kanal, ausgelöste Warnung, wirklicher Empfang/Quittierung |
| Hostneustart | NOT_VERIFIED | Separat autorisierter Host-/Dockerstart, Sessions/Daten/Jobs/Backup/Monitoring erhalten |
| Image-/Dependencyreview | NOT_VERIFIED_FOR_TARGET | Aktuelle Scanbefunde aller verwendeten Digests und dokumentierte Maßnahmen/Restbefunde |

Core-Freigabe erst nach allen Pflichtnachweisen. Unabhängig davon bleiben bis zu tatsächlicher neuer finanzieller Evidenz **REAL_DATA_LIMITED**, **FORECASTS_SHADOW_ONLY**, **RECOMMENDATIONS_GATED**. Quellen-/ML-/Strategieentscheidungen nur über ihre bestehenden geprüften Verträge, keine automatische Promotion aus PR3.
## PR4 – zusätzliche Release-Gates

- [ ] Vollständiges, frisches Inventar aller tatsächlich bereitgestellten Images, einschliesslich optionaler Dienste und Aliase; Digests stimmen mit dem RC-Manifest überein.
- [ ] CycloneDX-Schema- und Bytehashprüfung bestanden; Scanner-/DB-Version und native Abdeckungsgrenzen dokumentiert.
- [ ] Critical-/High-Befunde konkret behandelt; keine automatische Ausnahme wegen fehlendem Patch. Genehmigte Ausnahmen sind CVE-, Komponenten- und Digest-genau, begründet und befristet.
- [ ] Unveränderte alte P6-/P7-/Historienverträge, numerische Locks, vollständige Regression und isolierter Restore mit dem endgültigen Imagebestand nachgewiesen.
- [ ] Caddy-CA unverändert oder separat genehmigt migriert; echte Client-Trust-, VPN-/Firewall-, DNS-, Backup-/Key-Recovery- und Alarmnachweise liegen vor.
- [ ] Operatorprüfung erzeugt einen neuen unveränderlichen Freigabenachweis; das lokale blockierte PR4-Manifest ist keine Produktionsfreigabe.
- [ ] Keine ungeprüfte S3-/Datenbankmigration, Quellenfreigabe oder Modell-/Strategiepromotion aus PR4 ableiten.

Diese Punkte sind Anforderungen, keine vorweggenommenen Operatornachweise. Der reale Zielhost bleibt `TARGET_HOST_NOT_VERIFIED`.
