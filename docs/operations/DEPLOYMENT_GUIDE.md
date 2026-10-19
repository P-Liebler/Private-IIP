# Private Installation

Stand 19.10.2026. Der Operator hat bestätigt: **kein Zielhost verfügbar; lokal vorbereiten**. Windows Docker Desktop ist die lokale Prüfumgebung. Linux/systemd ist eine bereitgestellte Vorlage, kein getesteter Zielbetrieb. Die lokale synthetische Staging-Installation ist keine Produktionsfreigabe.

## Reihenfolge

1. Zielhost, privaten DNS-Namen, VPN-Adresse, Hardware, Backupziel und Verantwortlichen im [Abnahmeprotokoll](OPERATOR_ACCEPTANCE_CHECKLIST.md) festlegen. Docker Engine mindestens 28, Compose mindestens 2.24. Linux: Docker-Daemon aktivieren; Windows: Docker Desktop/WSL2, Loginabhängigkeit und Start nach Hostneustart tatsächlich prüfen.
2. [Konfiguration](PRODUCTION_CONFIGURATION.md) und [Secrets](SECRET_MANAGEMENT.md) außerhalb Git vorbereiten. Staging und Produktion erhalten getrennte Projekte, Volumes, Datenbanken, Schlüssel und Backupziele. Niemals Produktionsvolumes in Staging einhängen.
3. `python ops/preflight.py --env-file /secure/production.env --mode PRODUCTION --offline`, danach ohne `--offline`. Kein bestandener Preflight ersetzt Netzwerk-, TLS-, Backup-, Sicherheits- oder Operatornachweise.
4. `python ops/deploy.py deploy --env-file /secure/production.env` zeigt standardmäßig nur den Plan. Tatsächliche Ausführung benötigt `--mode STAGING` beziehungsweise `PRODUCTION`, `--operator-authorized` und `--migrations-reviewed`. Auf frischer Installation ohne vorhandene Datenbank zuerst kontrolliert Core-Dienste starten und leeres Basisschema anlegen; der Updateweg verlangt ein funktionierendes Backup und bricht sonst ab.
5. [Privatzugang](PRIVATE_NETWORK_ACCESS.md), [CA-Vertrauen](TLS_CA_TRUST.md), Benutzeranlage mit bestehender Auth-CLI und TOTP prüfen. Keine Secrets in CLI-Argumenten.
6. [Backup](BACKUP_SETUP.md), isolierten Restore, [Monitoring](MONITORING_RUNBOOK.md) und Fehler-/Neustarttests ausführen. Erst danach reale Nutzung erwägen.
7. Die vier Entscheidungen im PR3-Bericht getrennt abnehmen. Fehlende Finanzdaten verhindern keine technische Vorbereitung, aber reale Daten-/Forecast-/Recommendation-Freigaben bleiben gesperrt.

`ops/verify_production.py` prüft einen ausdrücklich angegebenen HTTPS-Endpunkt mit normaler Zertifikatsprüfung. Benutzer/Portfolio müssen ein separates genehmigtes Testkonto darstellen; niemals synthetische Transaktionen in echte Portfolios schreiben. Das Skript ist ein technischer Endpunkt-Test, kein Windows-/Android-Vertrauensnachweis. Monitoringzugang erfolgt hostlokal; für entfernte Prüfung geschützte Tunnel verwenden.

## Tatsächlich offene Bedingungen

Zielhost, private DNS-/VPN-Konfiguration, Windows-/Android-CA-Vertrauen, unabhängiges verschlüsseltes Backupziel, aktiver Tageszeitplan, echte Schlüssel-Recovery und nachgewiesene Alarmzustellung sind **NOT_VERIFIED**. Kein Hostneustart oder Firewall-/DNS-/Task-Scheduler-Eingriff wurde autorisiert oder ausgeführt.
