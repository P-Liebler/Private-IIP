# Monitoring und Alarmbehandlung

Vorhandene [Architektur](../architecture/monitoring.md), Prometheus-Regeln und Grafana bleiben die einzige Monitoringstrecke. `/internal/metrics` ist nur intern erreichbar; Caddy liefert 404. Prometheus/Grafana sind hostlokal. Operatoren dürfen `/system/status` nur über die explizite Operations-Allowlist lesen; normale Konten erhalten 403. Die Seite zeigt keine Zielpfade, Credentials, Prompt-/Dokument-/Portfolioinhalte.

Signale: API/DB/Valkey/MinIO, Queue, antwortende Celery-Worker, zuletzt abgeschlossener Intelligence-Dispatch, Backupalter/-fehler, Restoreergebnis/-alter, freier Backup-Dateisystemplatz, Collector-/Freshness-/ML-/Abstention-Metriken. Control-Ping beweist nur Worker-Erreichbarkeit; der Dispatch-Zeitstempel beweist tatsächlich bearbeitete geplante Arbeit. Ein veralteter Dispatch kann Beat, Defaultworker, DB oder Queue betreffen und muss anhand der Servicezustände untersucht werden. Das ist keine vollständige unabhängige Beat-Prozessmessung.

Auf API-/DB-/MinIO-Ausfall zuerst Core-Health und geschützte Logs mit Request-ID prüfen. Raw-Integritätsfehler sperren betroffene Verarbeitung; kein Fallback mit erfundenen Daten. Bei altem/fehlgeschlagenem Backup nicht nur den Prometheus-Alarm quittieren: Tagesjob unter seiner wirklichen Identität, Mount und Manifest prüfen; anschließend Restore ausführen. Restore älter als 31 Tage bleibt Warnung; Backup älter als 26 Stunden kritisch. Optionale MLflow-/Ollama-Ausfälle dürfen Kernberechnungen nicht blockieren.

## Zustellung

Aktuell ist **ALERT_DELIVERY_NOT_VERIFIED**. Provisionierte Regeln und ein Grafana-Panel beweisen keine beim Betreiber angekommene Meldung. Operator benennt einen kostenlosen realen Weg: beaufsichtigtes Dashboard mit festem Prüfintervall oder selbst betriebene Email-/lokale Integration. Authdaten geschützt konfigurieren; für aktive Nachrichten ist ausdrückliche Autorisierung nötig. Keine Nachricht wurde im Auftrag an Dritte gesendet.

Kontrolliert eine Testwarnung auslösen, Berechnung/Firing-Zeit, Empfängeransicht/Empfang, Quittierung und Ende protokollieren. Danach erst Zustellgate schließen. CPU/RAM/Hostdisk mit `docker stats --no-stream`, Host-Taskmanager/Performance Monitor beziehungsweise Linux-Monitoring prüfen; Containerwerte allein beweisen keine unabhängige NAS-Kapazität. Der lokale PR3-Test protokolliert tatsächliche Werte; Zielhost-Ressourcen bleiben offen.

Produktionscontainer verwenden JSON-Docker-Logs mit maximal fünf Dateien à 10 MiB. App-Logs sind strukturiert mit Request-ID; keine HTTP-Provider-URL-Logs. Docker-Logging ist keine sichere Langzeit-Auditablage: Auditdatensätze liegen in PostgreSQL. Private Inhalte, Tokens und Secrets nicht in frei formulierte Operatorlogs kopieren.
