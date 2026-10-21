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

## PR4: überprüfbarer Imagebestand vor dem Rollout

Die Build-Vorgaben verwenden geprüfte Basis-Digests. Eigene Images werden lokal unter versionierten RC-Tags gebaut; diese Tags allein sind keine Freigabe und kein Nachweis ihrer Verfügbarkeit in einer Registry. Für den Zielhost müssen die exakt geprüften Images über eine genehmigte Registry oder verifizierte Offline-Archive bereitgestellt werden. Keine ungeprüften Ersatzimages verwenden.

Vor einer Produktionsausführung verlangt `ops/deploy.py` zusätzlich `--release-manifest <genehmigtes-manifest.json>`. Geprüft werden Manifestinhalt, referenzierte Artefakthashes, der Git-sichtbare Quellbestand, vollständige Digest-Zuordnung aller Dienste sowie die separaten Zustände `SECURITY_REMEDIATED`, `TARGET_HOST_VERIFIED` und `OPERATOR_APPROVED` mit Operatornachweis. Das lokale PR4-Manifest erfüllt diese Freigabezustände ausdrücklich nicht. Es darf nicht allein durch Umbenennen von Statusfeldern zu einer Freigabe erklärt werden; die nachgewiesenen Entscheidungen benötigen einen neuen append-only Nachweis.

Nach bestandener Freigabe startet der Produktionspfad ausschliesslich die Manifestimages mit `--no-build`. Ein neuer Build, eine andere Konfiguration oder ein neuer Digest verlangt erneute Audit-/Kompatibilitätsnachweise. Backup und kontrollierte, ausdrücklich geprüfte Alembic-Migration bleiben vorgeschaltet. Der lokale Stagingpfad ist weiterhin getrennt und erteilt keine Produktionsfreigabe.

Security-Prüfkette: verifizierten Trivy-Scanner und aktuelle DB bereitstellen; `ops/ci_full_image_audit.py` für den vollständigen Compose-Bestand ausführen; `ops/validate_sboms.py` prüft die exakten SBOM-Bytes gegen vendorte offizielle Schemas; `ops/security_policy.py` bewertet das vollständige Inventar. Fehlende Images, Scanfehler, ungültige SBOMs und nicht genehmigte Critical-Befunde sind Blocker. Der kritische CI-Paketcheck ist keine vollständige Release-Abnahme. Details: [PR4A](../PR4A_SECURITY_ASSESSMENT_REPORT.md), [S3-Entscheidung](S3_COMPATIBILITY_REVIEW.md).
