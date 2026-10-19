# PR3 – Private Deployment und Abnahme

Stand 19.10.2026. **Lokale PR3-Vorbereitung und technische Tests abgeschlossen; keine Produktionsfreigabe.** Der Nutzer hat bestätigt, dass noch kein Zielhost verfügbar ist. Image-Sicherheitsbefunde und reale Betriebsnachweise bleiben offen.

Ausgangscommit `c8457351786d2023b5d4426751a33e46f62961f4`, origin/main identisch, PR2-CI 39214727791 tatsächlich erfolgreich. Kein Push/Release oder neue Remote-CI für diese lokalen Änderungen.

| Entscheidung | Aktueller Status |
| --- | --- |
| PR3A TECHNICAL STATUS | IMPLEMENTED / LOCALLY_TESTED / SECURITY_REVIEW_BLOCKED |
| PR3B TECHNICAL STATUS | LOCALLY_TESTED / LOCAL_RECOVERY_ACCEPTED / OPERATOR_GATES_OPEN |
| PR3C TECHNICAL STATUS | LOCAL_ACCEPTANCE_PASSED / TARGET_BLOCKED_NO_HOST |
| TARGET_HOST_VERIFIED | false |
| VPN_ACCESS_VERIFIED | false |
| TLS_CLIENT_TRUST_VERIFIED | false |
| INDEPENDENT_BACKUP_VERIFIED | false |
| DAILY_BACKUP_SCHEDULE_VERIFIED | false |
| SECRET_RECOVERY_VERIFIED | false |
| MONITORING_ALERT_DELIVERY_VERIFIED | false |
| PRIVATE_CORE_DEPLOYMENT_STATUS | PRIVATE_CORE_DEPLOYMENT_NOT_VERIFIED |
| REAL_DATA_STATUS | REAL_DATA_LIMITED |
| FORECAST_VALIDATION_STATUS | FORECASTS_SHADOW_ONLY |
| RECOMMENDATION_VALIDATION_STATUS | RECOMMENDATIONS_GATED |

## Prüfprotokoll

| Prüfung | Ergebnis |
| --- | --- |
| Ausgangsregression | 257 bestanden, 187,27 s |
| Neue vollständige Backendregression | 264 bestanden; endgültiger Lauf 120,33 s, bekannte Starlette-Deprecation |
| Host-/Betriebsgoldens | Zwölf bestanden, 1,02 s |
| Status-Folgeprüfung | Sieben gezielte Backendfälle nach Trennung des letzten Backupversuchs und letzten Erfolgs bestanden |
| Status-Browsernachprüfung | Neu gebauter Standalone-Client, ein Fall bestanden in 9,1 s einschließlich Anzeige des letzten erfolgreichen Backups |
| Ruff / Format / Mypy | Bestanden; 285 Backenddateien, 197 App-Dateien |
| Frontend | Lint, Typecheck und Standalone-Build bestanden |
| Browsergesamtprüfung | 21 bestanden, 2,2 Minuten; alle bisherigen 20 Fälle erhalten |
| HTTPS-/CSP-Browser-Smoke | Lokales Caddy-Frontend: Login/Dashboard/Portfolio/Instrument/Logout, null JS-/CSP-Fehler; temporärer Leaf-SPKI-Pin ist kein Client-OS-Trustnachweis |
| Compose / Settings / Preflight | Local und Staging gestartet; sichere Konfiguration positiv, ungültige Vorlage negativ geprüft; DRY_RUN führt keine Änderung aus |
| Alembic | Kein Drift, frische Migration 0019_validation mit 76 Tabellen; keine neue Migration |
| Monitoring | Prometheus/Grafana-Endpunktprobe und 14 Prometheusregeln geprüft; reale Alarmzustellung offen |
| Faults / Start | Scheduler/Worker/MinIO/PG/Valkey/API-Recovery bestanden; voller Container-Prozessstart 96,382 s, kein Hostreboot |
| Backup / Restore | Neues Backup 320 Rohobjekte / 2.914.753 Bytes; isolierter Restore 104,332 s bestanden; Golden exakt CHF 10'180 |
| Dependencyreview | Python Core/Assistant, MLflow-Lock und npm-Production ohne bekannte Meldungen; konkrete Image-High/Critical-Befunde offen |
| CI | Ausgangs-PR2-Workflow tatsächlich erfolgreich; kein Push und keine neue Remote-CI für PR3 |

Die temporären großen Imagearchive und ausschließlich dafür angelegten gestoppten Hilfscontainer wurden nach Zielprüfung entfernt; JSON-Scanbefunde und Nachweise bleiben erhalten. Das Sicherheitsinventar erfasst die tatsächlich gescannten Digests; spätere Code-Layer-Rebuilds und die nur teilweise geprüfte Ollama-CUDA-/Libraryfläche sind kein ungeprüfter Sicherheits-Pass. [CVE-/Paketinventar](security/PR3_IMAGE_AUDIT.json).

Neu: Produktionspreflight, gesonderte Operations-Allowlist und Statusseite, Settings-/Container-/Headerhärtung, Backup-/Restore-Lock und Fehlerstatus, Manifestgröße/letzter Erfolg, zusätzliche Monitoringregeln, Linux-Scheduler-Vorlagen, sicherer DRY_RUN-Deploymentwrapper, synthetischer Key-Drill und zehn Betriebsanleitungen. Keine Migration oder numerische/Assistant-Dependencyänderung. Alte Modellmanifeste, Rohdaten und Prognosen bleiben erhalten. Finanzautomatik aus, keine Quelle oder Modell-/Strategiepromotion und kein Trading.

## Exakte Wiederherstellung und Datenbefund

Backup `backups/pr3-acceptance/sets/20261019T103107Z-64300`, nach Stopp der Schreibprozesse. Manifest erfolgreich, 16,311 s. Isolierter Restore am 19.10.2026 **10:32:03–10:33:48 UTC**, eigene Container/Netze/Volumes danach entfernt. `backups/pr3-checkpoint.json` und `pr3-acceptance/runtime/restore-status.json` dokumentieren den überprüften Stand.

| Archiv | Geprüfter Stand |
| --- | --- |
| P6 | Dataset a4c9d4ff-07de-44d0-a89b-53e843648994; unverändert dd5cd6ef97b9248eb148725797470069b9b33635df15f8506d61bf99761ea538 |
| P7-Modell | 678d4cd7-776b-4183-bbb6-18a0b4a0b506; unverändert 9706d2dc2631d0cfde24ddaad3ccd4f41b686351cd5b82ecd5e0a96fc18f5c94; strenger Dependency-/MLflow-Check |
| Prognosen | 32 erhaltene Archiveinträge, null Outcomes; Hash 23ac107478b82420a01eeb486b394391bd9f5a14b3071b022434f0479991bf30 |
| P8 | 48 Risiko-, 24 Szenario-, 24 What-if-Records; Hash 9d4c489aff6706ae660fc367fbb7e02d1e487ba408ebdf7ac86d935d88ceaefc |
| P9 | 13 Recommendations, zwölf Profile; Hash 16b078ce35aaca621b58c34c95f1e8462ff8259a788c710ceb8a765510a9f85a |
| P10 | Zwei Dokumente/Chunks/Embeddings, sechs Nachrichten, 15 Alert-Evaluationen, drei Briefs, elf Optimizer-Runs; Hash 04a7f5b5cade1a6d0cb90f22a2f66c22f6f310be9e172c99273b803f70152c93 |
| PR1 / Quellenbetrieb | 20 Quellen, 13 Rechtebelege, sieben Jobs; Hash 9413dc4a347c9ef3df38a6e9c093a484c2d755001f54a5281a1c87a239ae0dd4 |
| PR2 | 13 append-only Belege; Hash 9d56663b6557c5eb84ea1490fbcc63ca0ea62a9d9d13dc11698515c1fb66afe3 |
| Portfolio | Privater Login und vollständiger Wert exakt CHF 10'180 |

Alle genannten finanziellen Testdaten sind ausdrücklich technische synthetische Fixtures, keine echte Markt-/OOS-Evidenz. Bestehende Archive wurden nicht umgeschrieben. Keine reife reale Outcome-Serie, keine real validierten Modelle oder Strategien. Externe Source-Gates bleiben unverändert: insbesondere SEC/ECB/SNB/OpenFIGI/Alpha/IR UNKNOWN und deaktiviert; Yahoo bleibt gesperrt. MANUAL_CSV behält ausschließlich seinen bisherigen Upload-Scope. Sync-/Macro-/Coverage-Tabellen im Checkpoint sind weiterhin leer und kein Beleg realer Historie.

## Repository und verbleibende Handlungen

Endstand: derselbe HEAD `c8457351786d2023b5d4426751a33e46f62961f4` plus lokale uncommitted PR3-Änderungen. Neue Dateien sind die vier PR3-Berichte, zehn Betriebsanleitungen, ADR-026/CVE-Inventar, Preflight/Deployment-/Fault-/Browser-/Redaktions-/Auditwerkzeuge, Hostgoldens/systemd-Vorlagen, Statusseite, Backendgoldens und synthetischer Key-Drill. Geändert sind bestehende gemeinsame Settings, Status-/Metrik-/Loggingpfade, Compose/Caddy/Monitoring/Backup/Restore, CI und dokumentierte Navigation. Numerische/Assistant-/MLflow-/npm-Locks unverändert; 212 Masterplan-Hauptabschnitte erhalten.

Keine offene reproduzierte Funktionsregression nach den abschließenden lokalen Prüfungen. Reproduzierte Einschränkungen: Image-Sicherheitsbefunde, begrenzte Ollama-Imageabdeckung, fehlender realer Host/VPN/Client-Trust, unabhängiger Backupmount und Tagesjob, echte Secret-/CA-Recovery und tatsächliche Alarmzustellung. RPO/RTO sind vorgeschlagene, nicht vom Operator bestätigte Ziele. Hardware-/RAG-/LLM-Leistungswerte dürfen aus den kleinen synthetischen Tests nicht auf ein zukünftiges produktives Portfolio übertragen werden.

Der lokale normale Betrieb ist wiederhergestellt; konfigurierte Healthchecks sind grün. Am laufenden API-Prozess geprüft: **APP_ENV=local, ASSISTANT_TEST_MODE=false, DATA_COLLECTION_ENABLED=false, FORWARD_SHADOW_ENABLED=false, Operations-Allowlist wieder leer**. Die vorübergehende Browser-Testfreigabe ist zurückgesetzt. JSON-Ausgabe von API und Celery wurde am laufenden Prozess geprüft. Keine Produktionsfreigabe, kein Trading, keine automatische Quelle oder Promotion.

Details: [PR3A](PR3A_DEPLOYMENT_SECURITY_REPORT.md), [PR3B](PR3B_OPERATIONAL_RELIABILITY_REPORT.md), [PR3C](PR3C_FINAL_ACCEPTANCE_REPORT.md), [Installation](operations/DEPLOYMENT_GUIDE.md), [Operatornachweise](operations/OPERATOR_ACCEPTANCE_CHECKLIST.md).
