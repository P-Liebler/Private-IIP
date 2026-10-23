# PR5D – Private Beta

Stand: 22.10.2026. **BETA_IMPLEMENTED / REAL_PRIVATE_DATA_USE_NOT_APPROVED.**

## Betriebszustände

Die vorhandenen Umgebungen bleiben bestehen. `LOCAL_DEVELOPMENT` bezeichnet die lokale Entwicklungsinstallation; die Beta ist ein getrenntes Abnahmeprotokoll für denselben Workflow. `LOCAL_PRIVATE_BETA` ist derzeit nur ein vorbereitetes Nutzungsziel, keine erteilte Echtdatenfreigabe. `PRIVATE_PRODUCTION` verlangt weiterhin Security-, Zielhost- und Operatorfreigabe des unveränderlichen Release-Manifests. Es gibt keinen neuen Environment-Schalter, der Prüfungen abschaltet.

Der Portfolioeinstieg kennzeichnet die noch offene Echtdatenfreigabe sichtbar. Fehlende Daten werden erklärt und mit Import-/Prüfaktionen verbunden. Research, Risiko, SHADOW-Prognosen und gesperrte Empfehlungen behalten ihre unabhängigen Daten- und Finanzgates. Kein autonomer Handel oder neues großes KI-Feature.

## Benutzeranleitungen

- [Start und erster Workflow](user/GETTING_STARTED.md)
- [Transaktionen und Startbestände](user/IMPORT_TRANSACTIONS.md)
- [Kurse, FX und Corporate Actions](user/IMPORT_MARKET_DATA.md)
- [Depotabgleich](user/PORTFOLIO_RECONCILIATION.md)
- [Datenqualität und nächste Schritte](user/DATA_QUALITY.md)
- [Getrennter echter Portfolio-Pilot](user/REAL_PORTFOLIO_PILOT.md)

## Getrennte Abnahmen

| Bereich | Status |
| --- | --- |
| Lokaler synthetischer Portfolio-Workflow | Implementiert und im API-/Browserablauf geprüft |
| Originale und Archiv-Replay | Neue Checkpoints; alte P6-/P7-Hashes erhalten |
| Automatische tägliche Echtdatenversorgung | NOT_VERIFIED; keine reale Quelle aktiviert |
| Sicherheitsfreigabe | BLOCKED; MinIO-Criticals und übrige Reviews offen |
| Echtes privates Depot | NOT_PROVIDED / NOT_ACCEPTED |
| Zielhost/VPN/Client-CA | NOT_AVAILABLE / NOT_VERIFIED |
| Produktionsbetrieb | NOT_RELEASED |

Es liegen keine echten Brokeroriginale vor. Deshalb wird weder ein realer Depotwert noch ein realer Auszugsvergleich behauptet. Ein späterer Pilot braucht eigene Volumes, eigene Nutzer/Secrets, unabhängiges Backupziel und Belege außerhalb von Git/CI/Testlogs. Erst nach behandelter Sicherheitslage können seine tatsächlich bereitgestellten Daten geprüft werden. Lokale synthetische Testkonten werden dafür nicht weiterverwendet.

## Verbleibende Abnahme

Aktuelle lokale Prüfungen, Image-/SBOM-Nachweise und Einschränkungen stehen im [Gesamtbericht](PR5_ACCEPTANCE_REPORT.md). Danach sind Securityentscheidung für Storage, High-/native-/CSP-Reviews, freigegebene instrumentbezogene Datenquellen und der reale Pilot erforderlich. Für privaten Dauerbetrieb folgen zudem Zielhost, CA-Vertrauen, unabhängiger Backupzeitplan, Schlüssel-Recovery, Neustart und Alarmempfang. Kein Push, Release oder produktiver Cutover ist durch diese Dokumentation autorisiert.
