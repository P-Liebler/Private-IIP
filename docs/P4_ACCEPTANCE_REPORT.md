# P4 – Portfolio Accounting und V1-Abnahme

**Stand:** 2026-10-12. **Umfang:** normativer Masterplan P4. **Status:** `FUNCTIONAL — PRODUCTION GATE OPEN`; für eine ungeprüfte Zielinstallation **V1 NOT READY**.

## Baseline und Migrationen

Ausgangspunkt war `main` auf `9ecb5f50352af7a3311721aaef9610cd732d0a2e`. Die 48 bestehenden Tests sowie die Qualitätsprüfungen waren vor P4 erfolgreich. Änderungen liegen lokal zur Prüfung vor; Remote-CI wurde nicht ausgeführt, kein Push und kein Release erstellt.

`0006_portfolio` ergänzt `benchmarks`, `portfolios`, `portfolio_accounts`, `transactions`, `portfolio_action_applications`, `cash_balances`, `position_snapshots` und `portfolio_snapshots`. `0007_snapshot_provenance` ergänzt Wissenszeitpunkt und konkrete Eingabereferenzen für Snapshots. Bestehende Migrationen wurden nicht geändert. Das vorhandene Schema wurde erweitert; der vollständige Weg von `0001` bis `0007_snapshot_provenance` wurde in einer temporären Datenbank mit 21 erforderlichen Tabellen geprüft.

## Ledger, Accounting und Corporate Actions

Portfolios gehören einem Nutzer, Accounts einem Portfolio. Lesen und Schreiben prüfen diese Zugehörigkeit. Archivierung erhält die Daten. Korrekturen markieren die ursprüngliche Transaktion als voided und ergänzen einen verknüpften Ersatz; wirtschaftliche Daten bleiben erhalten. Audit-Ereignisse und UTC-Zeitpunkte dokumentieren die Änderungen. Locks auf dem Portfolio serialisieren Buchungen und Snapshot-Rebuilds.

Die gemeinsame Service-Schicht berechnet Cash, Positionen, Bewertung, Berichte und Performance. Sie ist von API, Celery und Tests nutzbar. Die Buchhaltung verwendet `Decimal`, 34 Stellen Arbeitspräzision und acht Nachkommastellen mit Half-even-Rundung an Buchungsgrenzen. Käufe einschließlich Gebühren und Steuern bilden den gewichteten Einstand je Account und Instrument. Verkäufe entfernen den proportionalen Einstand und ziehen Verkaufskosten vom Erlös ab. Zu große Verkäufe werden abgelehnt; negative Cash-Bestände bleiben erhalten. Auch beim Replay werden fehlende oder ungültige Ledgerwerte abgelehnt, statt zu null zu werden.

Splits und Reverse Splits verändern Stückzahl und Stückeinstand ohne künstlichen Gewinn. Canonical Actions werden ausdrücklich und idempotent angewendet. Eine manuelle Buchung und eine canonical Anwendung dürfen denselben Effekt nicht doppelt erzeugen. Frühere Splits müssen vor späteren Entitlements geklärt sein. Tickerwechsel und Delisting werden als geprüfte Anwendungen festgehalten; ein offener delisteter Bestand benötigt eine Klärung der Abwicklung.

Die Dividendenvorschau zeigt Quelle, Datum, Verhältnis beziehungsweise Bruttobetrag und Ledger-Bestand. Gebühren und Quellensteuer müssen vor der Anwendung ausdrücklich bestätigt werden, auch wenn sie null betragen. Der Audit-Eintrag unterscheidet diese Nutzerangaben von den canonical Quelldaten. Wiederholte Anwendungen mit abweichenden Kosten oder geänderten canonical Versionen verlangen Review und überschreiben den erhaltenen Effekt nicht. V1 bucht den wirtschaftlichen Effekt am Ex-Datum; eine automatische Abstimmung von Broker-Settlement und Receivables gehört nicht zu dieser Abnahme.

Eine passende manuelle Buchung kann nach ausdrücklicher Prüfung mit der Canonical Action verknüpft werden. Betrag/Verhältnis, Währung und bestätigte Kosten müssen übereinstimmen. Es entsteht kein zweiter Ledger-Effekt; die ursprüngliche Buchung bleibt unverändert erhalten. Mehrdeutige oder abweichende Kandidaten bleiben gesperrt.

## FX, Performance und Snapshots

Bewertungen verwenden die vorhandene P3 Engine für akzeptierte Kursversionen und CHF/EUR/USD-FX einschließlich Inversen, Kreuzkursen und begrenztem Carry. Native Werte bleiben bei fehlendem FX sichtbar; der Gesamtwert in Basiswährung wird null und `PARTIAL`. Kurse älter als sieben Kalendertage sperren die vollständige Bewertung. Ein Kurs vor einem Split oder einer gebuchten Dividende wird als `MISSING_EVENT_PRICE` behandelt, bis ein passender Kurs nach dem Ereignis verfügbar ist. Insbesondere wird ein Kurs vor dem Split nicht mit der Stückzahl danach multipliziert. Die Oberfläche zeigt Kurs- und FX-Datum sowie Alter.

Realisiertes P/L, Brutto-Erträge, Gebühren und Steuern verwenden FX am Buchungstag. Einstand und unrealisiertes P/L verwenden den FX der Bewertung und sind entsprechend benannt. Fehlender historischer FX lässt betroffene Analysen unverfügbar, ohne einen bekannten aktuellen Marktwert zu verändern.

- Absoluter Ertrag: Endwert minus Anfangswert minus externe Netto-Cashflows, jeweils mit datiertem FX.
- TWR: tägliche Faktoren `(Endwert − externer Flow am Tagesende) / vorheriger Schlusswert`, geometrisch verknüpft. Fehlende Bewertung oder undefiniertes Anfangskapital erzeugen keine Ersatzrendite.
- XIRR: Beiträge negativ, Entnahmen und Endwert positiv; 365,2425 Tage pro Jahr. Konventionelle Cashflows mit genau einem Vorzeichenwechsel werden im unterstützten Bereich gelöst; fehlende eindeutige Lösung bleibt null.
- CAGR: annualisierte verknüpfte TWR über die tatsächlichen Kalendertage.
- FX-Beitrag: vorherige native Cash- und Wertpapierexposition mal täglicher FX-Änderung. Vorgänge desselben Tages werden nicht als vorherige Exposition behandelt.

Performance bietet tägliche, wöchentliche und monatliche Punkte. Der Benchmark basiert auf einem echten Instrument, raw closes, expliziten Splits, nicht wiederangelegten Bruttodividenden und datiertem FX. Fehlende Daten ergeben `DATA_UNAVAILABLE`. Portfolio- und Benchmark-Renditen bleiben bei ungeprüfter Corporate-Action-Abdeckung sichtbar `PROVISIONAL`.

Snapshots sind abgeleitete Daten. Identische Eingaben verwenden denselben Snapshot; geänderte Kurs-, FX- oder Ledgerreferenzen ergeben einen neuen. Wissenszeitpunkt, Eingabereferenzen, historische Event-FX-Herkunft und Hash werden gespeichert. Unbekannte Herkunft älterer Snapshots bleibt null. `as_of` schließt spätere Korrekturen aus; ein Portfolio, das zu diesem Wissenszeitpunkt noch nicht existierte, wird nicht als historischer Nullwert ausgegeben.

## Import, APIs und Oberfläche

CSV wird als unveränderte Rohdatei mit SHA-256 gespeichert, bevor Zeilen ausgewertet werden. Vorschau und Commit sind getrennt. Die Zuordnung unterstützt Account, Typ, Handels-/Settlement-Datum, Instrument-ID oder Ticker/ISIN/FIGI, Menge, Preis, Betrag, Währung, Gebühren, Steuern, Broker-ID und Notiz. Unbekannte Spalten öffnen die Zuordnung; mehrdeutige oder widersprüchliche Instrumente bleiben gesperrt. Broker-ID plus Account ist der bevorzugte Duplikatschlüssel, sonst ein normalisierter Fingerprint. Commit prüft erneut und rollt einen fehlerhaften Batch vollständig zurück.

Neue geschützte Endpunkte umfassen Portfolio-CRUD, Account-Erstellung/Änderung/Archivierung, Transaktionen einschließlich Korrektur und Void, CSV-Vorschau/Commit, Corporate-Action-Vorschau/Anwendung, Bewertung, Holdings, Allokation, Performance, Benchmarks, Summary/Dashboard und Snapshots. Die API-Dokumentation enthält die vollständigen Verträge.

Dashboard und Portfolio-Liste zeigen echte Werte, Tages-/Gesamt-/YTD-Ertrag, Cash und Datenzustand. Summen werden mit Decimal je Basiswährung gebildet. Detailseiten enthalten Übersicht, Positionen, Performancechart, Allokationscharts, Brutto-/Netto-Erträge, Transaktionen und Datenqualität. Fehlende Daten bleiben ausdrücklich sichtbar. Login und Logout wechseln das Dokument nach der Session-Antwort, damit alte Serverlayouts nicht als aktuelle Anmeldung verwendet werden. Der Entwicklungsprozess synchronisiert geänderte Dependencies und erkennt Windows-Bind-Mount-Änderungen mittels Webpack/Polling.

## Tests und konkrete Szenarien

Das Golden Portfolio enthält zwei Käufe, Gebühren, einen Split, eine Dividende mit Quellensteuer und einen Teilverkauf: Cash USD 8'526, 30 Aktien, Einstand USD 1'653, Durchschnitt USD 55,10, realisiertes P/L USD 145, Marktwert USD 2'100 und unrealisiertes P/L USD 447. Der Wert beträgt USD 10'626 beziehungsweise CHF 9'563,40 bei FX 0,9. Separate vorab definierte Renditefälle prüfen Cashflow-neutrale TWR, XIRR, mehrere Einzahlungen, Entnahme und uneindeutige Fälle. FX-Attribution berücksichtigt auch die Gegenwirkung negativer Fremdwährungs-Cash-Bestände.

Der Integrationstest prüft Login, Portfolio/Account, Einlage und Kauf; fehlenden Kurs und fehlenden FX; CHF 10'180 nach Datenimport; fremden Nutzerzugriff; Snapshot-Wiederverwendung und Provenance; erhaltene Korrektur/Voids; Rohdatei vor CSV-Commit, Duplikate und atomaren Rollback; Split-/Dividenden-Reihenfolge, bestätigte Kosten und doppelte Anwendung; fehlenden Kurs nach Action; Teilverkauf; historische Kurs-/Action-Korrektur; Benchmark/TWR und eine EUR-Bewertung von EUR 660 mit USD-Position EUR 960. Ungültige gespeicherte Trades dürfen keinen Nullwert erzeugen.

Die beiden Browserfälle prüfen den vorhandenen Bewertungsfall und einen vollständigen neuen Ablauf mit Gebühren/Steuer, Allokation, fehlendem Kurs, Dividende mit bestätigter Quellensteuer und Split. Ihre Portfolios werden archiviert; Hilfsinstrumente deaktiviert. Alle Finanzdaten dieser Tests sind ausdrücklich synthetische lokale Fixtures. Tests rufen keine Live-Finanzprovider auf.

## Production Access, Monitoring und Recovery

Der separate Production Stack verwendet Caddy mit privater CA, HTTPS, Secure/HttpOnly-Cookies, Sicherheitsheadern und gesperrten öffentlichen Metrics. API, PostgreSQL, Valkey und MinIO besitzen keine Hostports. MinIO wird über den geprüften privaten TLS-Pfad angesprochen. Prometheus und Grafana binden localhost. Dashboard und sechs Alert-Regeln sind provisioniert; Requests, Latenz, Fehler, DB, Queue, Quarantäne, alte Kurse, Bewertungsfehler und Backups werden erfasst. Der tatsächliche VPN-/LAN-Zugang bleibt eine Konfiguration der Zielinstallation.

Backups enthalten einen PostgreSQL-Dump und sämtliche Rohobjekte mit Manifest, UTC-Zeit, tatsächlichem Datenbanknamen und SHA-256. Auch ein leerer Raw-Bucket ist ein gültiger Zustand. Der Zielpfad ist konfigurierbar; Retention hält sieben tägliche, vier wöchentliche und sechs monatliche Stände innerhalb dieses Pfads. Config, TOTP-Schlüssel und privates CA-Material gehören in eine getrennte verschlüsselte Sicherung. Für Windows liegt ein konkreter Installer für den täglichen Hostjob vor; er speichert keine Passwörter in Task-Argumenten und ersetzt keinen vorhandenen Task.

Der Restore startet einen separaten, zufällig benannten Compose Stack mit eigener PostgreSQL-/MinIO-Instanz und ohne Hostports. Manifestprüfsummen werden vorab geprüft. Danach werden Migration-Head, Benutzer, Transaktionen, Raw-Hash, wirklicher Login und vollständige Bewertung geprüft. Der isolierte Stack wird anschließend einschließlich seiner Testvolumes entfernt.

Der geprüfte Stand `backups/prod-test/sets/20261012T195206Z-31392` enthält Head `0007_snapshot_provenance` und zwei Raw-Objekte. Der isolierte Restore meldete **PASSED**; der Wert nach Wiederherstellung war exakt **CHF 10'180**, wie vor der Sicherung. Die vollständigen Artefakte bleiben lokal in dem von Git und Docker ignorierten Backup-Verzeichnis.

## Prüfbefehle

| Befehl | Ergebnis |
| --- | --- |
| `docker compose config --quiet` | PASS |
| `docker compose up -d --build` | PASS |
| `docker compose exec -T api alembic upgrade head` | Head `0007_snapshot_provenance` |
| `docker compose exec -T api alembic check` | Keine neue Schema-Abweichung |
| `docker compose exec -T api python -m scripts.verify_fresh_migration` | PASS, 21 Tabellen |
| `docker compose exec -T api pytest -q --tb=short` | 61 passed; eine upstream Starlette-Warnung |
| `docker compose exec -T api ruff check .` | PASS |
| `docker compose exec -T api ruff format --check .` | PASS |
| `docker compose exec -T api mypy app` | PASS |
| `docker compose exec -T web npm run lint` | PASS |
| `docker compose exec -T web npm run typecheck` | PASS |
| `docker compose exec -T web npm run build` | PASS, Next.js 16.3.8 |
| `npm run test:e2e` mit ausdrücklich gesetzten Fixture-Variablen | 2 passed |
| `npm audit --omit=dev` | 0 vulnerabilities |
| `python ops/backup.py --compose-file docker-compose.prod.yml --env-file backups/production-test.env --root backups/prod-test` | Tatsächlicher Dump und Raw-Mirror, PASS |
| `python ops/restore_verify.py backups/prod-test/sets/20261012T195206Z-31392 --root backups/prod-test --username restore_fa0d2ad37cfd --portfolio-id a8f70531-dc73-47b7-b648-d56131c8ec1a --raw-id a7d57f0c-e9e2-46f4-8550-d260b22abf3d --expected-value 10180` | Isolated restore PASSED; Testpasswort nur über Environment |
| `python ops/verify_production.py --env-file backups/production-test.env --ca-file backups/local-production-ca.crt --username restore_fa0d2ad37cfd --portfolio-id a8f70531-dc73-47b7-b648-d56131c8ec1a --expected-value 10180` | TLS-Kette/Hostname, Web/API, Header, Cookie, Wert, Metrics-Grenze, Prometheus und Grafana PASS |

Zusätzlich wurden Caddy-Konfiguration und Prometheus-Konfiguration/Regeln validiert. Celery- und MinIO-Smoke sowie API-Readiness wurden ausgeführt. Der Entwicklungsstack und alle zehn dauerhaften Dienste des lokalen Production Stacks erreichten `healthy`. Die lokale Testinstanz ist eine Acceptance-Umgebung, keine Abnahme eines unbekannten externen Hosts. Die Schlussprüfung mit dem aktuellen Code bestand: 61 Backend-Fälle und beide Browserfälle, einschließlich manueller Dividendenvorkerfassung und ausdrücklicher Verknüpfung ohne zweiten Effekt. Der letzte Backup-Satz wurde mit den aktuellen Services isoliert wiederhergestellt; Ergebnis PASSED. Der Windows-Installer wurde nur syntaktisch geprüft, ohne Registrierung eines Jobs.

## Verbleibende Grenzen und V1-Status

**V1 NOT READY für die noch nicht konfigurierte Zielinstallation.** Offen sind die Abnahme des tatsächlichen privaten Hostnamens/VPN-Bindings einschließlich Browser-CA-Vertrauen, ein unabhängiges geschütztes Backup-Ziel und die Aktivierung/Prüfung des täglichen Hostjobs. Die lokalen TLS-, Login-, Monitoring- und Restore-Nachweise ersetzen diese externen Bedingungen nicht. Der ausführbare Scheduling-Installer und die Prüfskripte liegen zur Umsetzung vor; es wurde kein Job gegen ungeprüfte Produktionsdaten installiert.

Reale fachliche Grenzen: Renditen bleiben bei ungeprüfter Action-Abdeckung vorläufig. Canonical Revisionen, gleiche Ex-Daten für Split und Dividende, Cash-in-lieu und Delisting-Abwicklung benötigen explizite Klärung. V1 verwendet wirtschaftliche Ex-Daten und Tagesende-Cashflows; Transfers gelten bis zu einer späteren Verknüpfung als externe Flows. XIRR ist bei nichtkonventionellen Flows oder außerhalb des unterstützten Bereichs unverfügbar.

Next.js und eslint-config-next wurden auf 16.3.8 aktualisiert. Die primäre [Next.js-Sicherheitsmeldung](https://github.com/vercel/next.js/security/advisories/GHSA-vcvr-r3jv-pc5j) und die [Meldung zur Image Optimization](https://github.com/vercel/next.js/security/advisories/GHSA-cjq9-62q9-8jv4) wurden am 2026-10-12 geprüft. Der Audit der Produktionsdependencies ist ohne Befund. Fünf Meldungen betreffen die Entwicklungswerkzeuge über `braces`; ein kompatibler Fix wurde im npm-Audit nicht angeboten. Die bestehende Starlette-Testwarnung bleibt ohne Testfehler. Keine Remote-CI-Aussage wird daraus abgeleitet.
