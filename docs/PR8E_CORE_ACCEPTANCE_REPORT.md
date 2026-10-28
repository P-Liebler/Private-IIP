# PR8E – technische Core-Abnahme

Stand: 27.10.2026. **LOCAL_SYNTHETIC_VERIFIED / NOT_RELEASED.** Die unabhängig lösbaren lokalen Core-Verträge sind geprüft. Security-, Host-, Quellen- und Operatorfreigabe sowie die reale Portfolioabnahme bleiben getrennt offen.

## Regression

| Prüfung | Tatsächliches Ergebnis / Beleg |
| --- | --- |
| Backend | 306/306 bestanden, `backups/pr8-backend-v2.txt`. Erster Lauf 303/306: globale Research-Pagination in einem Fixture falsch angenommen; Folgefehler durch nicht entsorgten Test-Eventloop. Eindeutiger Fixturefilter, sechs betroffene Fälle und danach vollständiger Lauf erfolgreich. |
| Host-/Securityverträge | **82/82 bestanden**, `backups/pr8-host-final-v3.txt`; Scope, fehlende/abweichende Services, Recovery, DB-Freshness, Holdings-Planung und Client-CLI. Das Manifest weist fehlende oder vom Scope abweichende Restore-Images einschließlich S3-Client und isoliertem Archiv-Verifier ab. Der abschließende erwartete Policyzustand bleibt `SECURITY_BLOCKED`. |
| Frontend | Lint, Typecheck und Standalone-Production-Build erfolgreich; `backups/pr8-frontend-*.txt`. |
| Browser | **30/30**, `backups/pr8-browser-v2.txt` und `pr8-browser-v2-status.json`; `normal_mode_restored=true`. Vorheriger 29/30-Lauf erhalten. Der neue CSP-Fall prüft tatsächliche Parser-Injektion; privilegierte DevTools-Ausführung war kein geeigneter erster Test. |
| Core-HTTPS | Eigene CA strikt geprüft, Secure/HttpOnly-Cookie, falsches Passwort und widerrufene Sitzung abgewiesen, aktuelle synthetische CHF-10’180-Bewertung, interner Metrikpfad extern gesperrt, Skript-Nonce vorhanden. `backups/pr8-core-stage-v1/https-core-v4.json`. Kein Windows-/Android-CA-Abnahmenachweis. |
| Optionale Dienste aus | Core-API/Web/Store/PG/Queue/Worker/Scheduler/Prometheus waren gesund, MLflow/Ollama/ML-Worker/Grafana nicht gestartet. Ohne Ollama archivierte strukturierte `LLM_UNAVAILABLE`-Antwort mit abgeschlossenem Stream. |
| Holdings-Update | Tatsächlich vorhandene synthetische lokale Fixture-Holdings über API gelesen; erlaubte Jobarten vorbereitet, fehlende Operator-/Source-Freigaben nicht umgangen. `holdings-refresh-blocked.json`. Kein echter Providerabruf. |
| S3-Vertrag | Neuer eigener Lauf `backups/pr8-s3-contract-v1/status.json`: PASS und gestoppt. Beide Stores exakt SeaweedFS 4.51; aktuelles API-Image und Caddy. Strikte CA, Metadaten/Hashes/Range, falsche Credentials, Multipart-Unterbrechung und neuer Resume-Prozess, Spiegelung/Restore sowie tatsächliche Storagefactory. Prüf-SDK separat im bestehenden MLflow-Image, kein aktiver Core-Dienst. |
| Monitoring | `backups/pr8-core-stage-v1/mc-backup-v4-status.json` bestätigt tatsächlichen Prometheus-API-Scrape UP. Erster Versuch prüfte zu früh vor dem ersten Scrape; neuer Probe wartet begrenzt. Alarmzustellung/Zielzeitplan separat offen. |
| Images | [Core-RC3](security/pr8-20261027/core-rc3/inventory.json), **13 Services / 9 unterschiedliche Images**, [13 formal validierte SBOMs](security/pr8-20261027/core-rc3/sbom-validation.json). Separater MC-Client im tatsächlichen Recovery-Scope: 0 Critical/High/Medium, 1 Unknown. Backend-Highs und alter Modell-Verifier bleiben Blocker. |
| Zielbackup | Gepinnter neuer MC-Client, striktes TLS-Stat, fehlende verpflichtende CA abgewiesen; tatsächliches Backup **20261027T151640Z-52760**. `backups/pr8-core-stage-v1/mc-backup-v4-status.json`: `passed=true`, `stopped=true`. |
| Isolierter Restore | **1383 Dateihashes**, `backups/s8-v1/runtime/restore-status.json`: `success=true`, `cleanup_success=true`; PG17, SeaweedFS 4.51, Backend-RC6 und separater MC-Client. Alte Raw-/P6-/Modell-/Intelligence-/UI-/Entfernungsverträge erhalten. Archivierter Modell-Verifier nur mit `network none` und Read-only-Mounts. |
| Read-only Preflight | [Letzter Bericht](security/pr8-20261027/core-preflight-v2.json): nichts ausgeführt. Einziger Konfigurationsfehler `BACKUP_FREE_SPACE_BELOW_5_GIB` bei 3’915’988’992 freien Bytes; getrennt `SECURITY_BLOCKED`, `TARGET_HOST_NOT_VERIFIED`, `NOT_APPROVED`. |

Die Browserfälle verwenden synthetische eigene Accounts und die echte lokale API. Transaktions-/Mehrinstrument-Kurs-/FX-Import, Korrektur/Wiederholung, Ledger, Abgleich, Datenqualitätsfehler und Retry bleiben nachvollziehbar. Reale Brokerdaten und eine unabhängige Anfängerperson fehlen.

[Maschinenlesbare Prüfergebnisse](security/pr8-20261027/test-results.json) binden die privaten Originalprotokolle per SHA-256. Die abschließende normale Instanz hat `ASSISTANT_TEST_MODE=false`, keine Data-/ML-Operatorrollen und deaktivierte externe Quellen; der bestehende freigegebene manuelle CSV-Pfad bleibt erhalten. Tatsächlich gezählt wurden **79 gemappte Anwendungstabellen plus `alembic_version` = 80 Tabellen**, bei unverändertem Alembic-Head `0021_ui_requests`. Die im Auftrag genannten 78 sind damit kein bestätigter aktueller Zählwert. Alle Modelltabellen sind vorhanden, keine zusätzlichen Tabellen; PR8 ändert weder Modelle noch Migrationen.

## Archiv und operativer Fortschritt

Die erste Prüfung stoppte an einer Intelligence-Hashabweichung. Gegen eine neu restaurierte Frozen-DB wurde anschließend jede vorhandene Zeile verglichen: **42 Alert-Regeln änderten ausschließlich den monotonen operativen `last_checked_at`-Zeitstempel**. Regelversionen und sämtliche sonstigen alten Inhalte blieben unverändert; keine alten Rows wurden entfernt. `intelligence-append-delta-v2.json` hält die engen geprüften Unterschiede fest. Der alte Checkpoint bleibt unverändert.

Der eigene neue Testaccount ergänzte genau eine Preis- und eine FX-Version. Der bestehende Collection-Delta-Verifier prüfte erneut alle elf Tabellen gegen den Frozen-Dump; keine sonstige Änderung oder Löschung. `collection-append-delta.json` und ein neuer Post-Fixture-Checkpoint ergänzen den alten Stand. Dies ist kein stilles Umschreiben eines alten globalen Hashvertrags.

Der abschließende Restore bestätigt die ursprüngliche Goldenbewertung **CHF 10’180** ausschließlich zum dokumentierten **26.10.2026 15:18:05.987683 UTC**. Derselbe Restore prüft für heute ausdrücklich `STALE_PRICE` und einen fehlenden Gesamtwert statt einer Vollbewertung. Der neue eigene Fixture-Account dient separat der aktuellen HTTPS-Bewertung. Kein alter Kurs wurde künstlich aktualisiert.

## Konfigurationskorrekturen aus den Läufen

- Ausschließlich interne Netze veröffentlichten in der lokalen Docker-Umgebung keine Hostports. Der Proxy erhielt ein eigenes neues Edge-Netz; App und Storage bleiben intern. Ein Host-/VPN-Gate wird dadurch nicht ersetzt.
- CA-Mount unter dem MC-Konfigurationsverzeichnis erzeugte root-eigene Elternverzeichnisse und blockierte UID10001. Der separate Client kopiert nur die öffentliche CA aus einem Read-only-Mount in sein eigenes Tmpfs. Fehlende verpflichtende CA führt zu Abbruch; TLS-Prüfung wird nicht abgeschaltet.
- Aktive Digestreferenzen werden in Compose und Scope identisch verwendet, einschließlich Backup und historischem Verifier. Frühere fehlerhafte Vorprüfungen bleiben als Versuche erhalten.

## Reproduzierbarer Kandidat und verbleibende Abnahme

Der endgültige lokale Kandidat wird durch `ops/releases/pr8-core-v1-rc3-manifest.json`, den [Scope](../ops/releases/pr8-core-v1-scope.json), das RC3-Inventar und die zugehörigen Scan-/SBOM-Belege gebunden. Vorherige fehlgeschlagene Versuche und deren Originalberichte bleiben erhalten. Es wurden weder historische Modellpins aufgeweicht noch alte Checkpoints durch heutige Inhalte ersetzt.

Der [Source-Scan-Beleg](security/pr8-20261027/source-security-receipt.json) ist ein eigener generierter Nachweis. Der Scan umfasst Git-sichtbare Quellbytes einschließlich uncommitteter Änderungen; ignorierte private Operator-/Backupdaten und danach erzeugte Belege sind nicht Bestandteil dieses Scans. Das abschließende Manifest bindet auch diese generierten öffentlichen Belege.

Ein anderer Build, geänderter Scope oder aktiviertes optionales Profil benötigt eigene passende Nachweise. Lokaler Testabschluss ersetzt keinen neuen Remote-CI-Lauf; die Arbeitsänderungen wurden nicht gepusht. [Konkrete verbleibende Operatoraktionen](PR8_ACCEPTANCE_REPORT.md) betreffen die Sicherheitsentscheidung, freien Speicher, Zielhost/VPN/CA, unabhängige Backups/Schlüssel-Recovery, Quellenrechte, Originale und eine unabhängige Testperson. Forecasts und Empfehlungen bleiben unvalidiert und gesperrt.
