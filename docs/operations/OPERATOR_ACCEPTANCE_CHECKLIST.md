# Operator-Abnahmeprotokoll

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
