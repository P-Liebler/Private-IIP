# Private Core: geführte Installation und Zielhostprüfung

Stand: 28.10.2026. Der Zielhost fehlt. Dieser Ablauf bereitet eine spätere Installation vor; lokale Stagingtests erteilen keine Freigabe.

## 1. Konfiguration außerhalb von Git vorbereiten

1. Ziel-OS/Docker-Unterstützung, privaten DNS-Namen, VPN-Adresse und eigenes Compose-Projekt festlegen. Staging und Produktion erhalten unterschiedliche Projekt-, DB-, Secret- und Volumeidentitäten. Niemals `investment-intelligence` oder ein bereits belegtes Produktionsprojekt verwenden.
2. `ops/production.env.example` in einen privaten Ordner außerhalb des Checkout kopieren. `APP_ENV`, Projekt mit Suffix `-staging` oder `-production`, Hostname und VPN-Adresse anpassen. Alle Platzhalter durch unterschiedliche starke Secrets ersetzen; `CORE_S3_CONFIG` auf eine private absolute Seaweed-Identitätendatei setzen. Keine Secrets in CLI-Argumente, Terminalausgaben, Tickets oder Git kopieren. [Secret-Vertrag](SECRET_MANAGEMENT.md).
3. Windows: NTFS-Zugriff nur für benanntes Dienstkonto, SYSTEM und benannte Administratoren; Vererbung breiter Rechte entfernen. Linux: Ordner 0700, Dateien 0600. Preflight verwirft breite oder nicht überprüfbare Rechte und Links/Junctions. Die vorliegende lokale synthetische Konfiguration ist keine Vorlage mit Produktionszugängen.
4. Ein absolutes bestehendes Backupverzeichnis wählen, ohne Laufwerkswurzel, Checkout-/Quelldateiüberlappung oder umgeleitete Pfade. Für Produktion liegt es außerhalb des Checkout. Ein geschützter Ordner auf C: ist lediglich Staging, kein unabhängiges Recoveryziel. Mindestens 5 GiB frei, zusätzlich die gemessene Aufbewahrung und das reale Archivwachstum planen.
5. Exakte freigegebene Images lokal bereitstellen. Keine Tags substituieren, nicht automatisch bauen oder pullen. Jeder geänderte Digest benötigt eigene Evidenz. `ml`, `llm` und `monitoring-ui` bleiben aus, solange sie nicht separat im freigegebenen Scope stehen.

## 2. Vorprüfung und Installationsplan

Vom Repositoryroot aus, mit tatsächlichen privaten Pfaden und dem endgültigen Inventar:

```powershell
python ops/core_preflight.py --env-file C:/privat/core.env --scope ops/releases/pr9-core-v1-scope.json --inventory C:/privat/final-inventory.json --mode PRODUCTION --output C:/privat/evidence/preflight-UTC.json
python ops/core_install_plan.py --env-file C:/privat/core.env --scope ops/releases/pr9-core-v1-scope.json --inventory C:/privat/final-inventory.json --preflight C:/privat/evidence/preflight-UTC.json --manifest ops/releases/pr9-core-v1-rc1-manifest.json --mode PRODUCTION --output C:/privat/evidence/install-plan-UTC.json
```

Beide Helfer starten keine Dienste. Preflight liest Compose, lokale Imageidentitäten, RAM, Backupplatz, Dateirechte und S3-Identitätsvertrag. Es prüft den vollständigen Scope einschließlich Recovery, private Ports und eigene nicht externe Volumes. Der Plan bindet Preflight an Konfigurations-/Scope-/Inventarbytes, Modus und maximal 24 Stunden. Ein geänderter Checkout kann ein älteres Release-Manifest absichtlich ungültig machen.

`CONFIGURATION_PLAN_READY` bedeutet nur, dass der Plan konsistent vorbereitet wurde. Security-, Zielhost-, unabhängiges Recovery-, Migrations-/Rollback- und Operatorfreigabe bleiben separate dokumentierte Entscheidungen zum exakten unveränderlichen Manifest. `core_install_plan.py` hat absichtlich keinen Apply-/Deploy-Unterbefehl. Das alte `ops/deploy.py` verwendet den Legacy-Servicevertrag und ist kein Core-Installer.

## 3. Spätere Ausführung nach tatsächlicher Freigabe

Der ausgegebene Plan nennt die vollständigen Kommandoargumente: ausschließlich neues Volume initialisieren, PG/Store/Queue/Caddy starten, CA-Export als eigenen einmaligen Schritt mit erfolgreichem Exitcode prüfen, freigegebene Migration mit gepinntem API-Image und anschließend explizite Core-Laufzeitdienste. CA-Export gehört nicht in eine Liste dauerhaft gesunder Daemons. PostgreSQL muss per authentifiziertem TCP-`SELECT 1` auf der konfigurierten Datenbank bereit sein; initdbs temporärer Socketserver genügt nicht. Eine abgebrochene Initialisierung darf nicht durch blindes Wiederverwenden oder Reparieren des Volumes verdeckt werden. Fehlerzustand sichern und ausschließlich ein neues eigenes Stagingvolume verwenden. Alle Starts verwenden `--no-build --pull never`, einzelne `run`-Befehle `--pull never`; optionale Profile werden nicht gestartet. Vorhandene DB-/Storevolumes werden nicht übernommen. Ein PG16-Verzeichnis darf nicht mit PG17 geöffnet werden.

Eine bestehende Installation benötigt vor Cutover den vorhandenen SQL-/S3-/Referenzcheckpoint, `s3_migrate.py`, geprüfte Kopierbelege und vollständigen Zielrestore. Die leere Initialisierung darf nicht als Migration deklariert werden. Provider-, Forecast- und Strategiegates werden dabei nicht verändert.

Rollback: Writes stoppen, neue Buchungen/Originale sichern, Delta seit Cutover klären und verifizierten Satz in neuen isolierten Volumes restaurieren. Erst nach eigener Operatorentscheidung umstellen. Kein `down -v`, kein automatisches Volumedowngrade und kein Verwerfen neuer Buchungen. Bei ungeklärtem Delta Wartungszustand beibehalten.

## 4. Ausführbarer Zielhost-Testablauf

Alle folgenden Schritte bleiben **PENDING**, bis sie auf dem tatsächlichen Ziel ausgeführt und separat geprüft wurden. Private Artefakte in `C:/privat/evidence` oder einem entsprechend geschützten Zielordner ablegen. Ausgaben vor Ablage auf Secrets prüfen; Passwörter, Sessioncookies, TOTP-Codes, CA-Privatekeys und Brokeroriginale gehören nicht in diese Testprotokolle.

| Schritt-ID | Tatsächliche Aktion | Eindeutiger Nachweis |
| --- | --- | --- |
| `private_hostname` | `Resolve-DnsName <privater-Hostname>`; Hostname mit tatsächlichem Manifest/Deployment vergleichen | UTC-Protokoll mit erwartetem Namen, Ziel-IP und Konfigurationsidentität |
| `vpn` | Im VPN `Test-NetConnection <Host> -Port 443`; danach außerhalb des VPN wiederholen | Im VPN erfolgreich; außerhalb keine erreichbare private Anwendung. Beide Netzzustände mit Datum dokumentieren |
| `dns` | DNS-Auflösung im VPN auf Windows und Android testen; keine öffentliche Ersatzadresse verwenden | Tatsächliche Antworten entsprechen ausschließlich den freigegebenen privaten Adressen |
| `windows_client` | Auf echtem Windows-Client anmelden, Portfolio/Instrument/Import/Dialog und Abmelden testen | Client-/Browserversion, Datum und geschützte Screenshots; widerrufene Session hat keinen Zugriff |
| `android_client` | Auf echtem Android-Gerät mit VPN und Browser dieselben Hauptpfade inklusive mobiler Navigation testen | Modell/Android-/Browserversion, tatsächliche Screenshots und Fehlerprotokoll |
| `tls_ca` | Öffentliche CA-Fingerprints getrennt vergleichen, CA nach [TLS-Anleitung](TLS_CA_TRUST.md) installieren; `curl.exe --cacert <öffentliche-CA.pem> https://<Host>/api/v1/health/ready` und Browser ohne Warnung testen | HTTP-Ergebnis und beide Client-Vertrauensnachweise. Negative Probe mit falscher CA muss scheitern; niemals `-k` |
| `login_totp` | Eigenes genehmigtes Testkonto, Argon2id-Login, TOTP-Einrichtung, Fehlversuch, Abmelden und Sessionwiderruf über bestehende UI testen | Nur Ergebnis/Zeitpunkt/Konto-ID; weder QR-Seed noch Code/Passwort/Cookie protokollieren |
| `backup` | Unabhängiges verschlüsseltes Ziel prüfen; Tagesjob unter tatsächlichem Taskkonto ausführen, anschließend Ziel/Mount absichtlich nicht verfügbar machen und Job wiederholen | Erfolgreiches Manifest/Dateihashes und getrenntes Fehlerprotokoll; fehlendes Ziel erzeugt keinen lokalen Fallback |
| `restore` | Bestehendes `restore_verify.py --help` verwenden, exakte API-/PG-/Store-/Client-/Legacy-Digests aus Manifest und tatsächlichen Checkpoint übergeben; ausschließlich zufälliges isoliertes Projekt | Restorestatus `success=true`, `cleanup_success=true`, Hashvergleiche und historische Bewertung CHF 10’180 am dokumentierten Stichtag; heutige Freshness bleibt separat |
| `secrets_recovery` | In eigener isolierter Umgebung vom getrennten verschlüsselten Secretbackup S3-/DB-Zugänge, originalen TOTP-Key und CA wiederherstellen; falschen Schlüssel negativ testen | Originale CA-Fingerprintgleichheit, funktionierender DB-/S3-Zugang/TOTP-Login, scheiternder falscher Key; keine Schlüssel in Belegen |
| `alert_delivery` | Kontrollierten Backupfehler und ausbleibenden geplanten Lauf erzeugen; Restorealter-/Platzalarm prüfen und echten Empfangskanal testen | Alarm-ID, firing/resolved-Zeit, Empfängerbestätigung. Ein Prometheus-Firing ohne tatsächlichen Empfang genügt nicht |
| `host_reboot` | Nach ausdrücklicher Operatorfreigabe Zielhost neu starten, Docker-/VPN-/Dienste-/Taskstart, persistierte Daten, Login/TOTP, Queue und Tagesbackup prüfen | Vorher-/Nachher-Boot-ID und tatsächliche Dienste-/Job-/Backupnachweise. Containerrestart ist kein Hostrestart |

Für jeden ausgeführten Schritt einen neuen privaten Beleg erzeugen:

```powershell
python ops/record_host_check.py --step dns --result PASS --operator <Operator-ID> --hostname <privater-Hostname> --manifest ops/releases/pr9-core-v1-rc1-manifest.json --evidence C:/privat/evidence/dns-UTC.txt --output C:/privat/evidence/dns-UTC-receipt.json
```

Der Helfer bindet existierende Belegbytes und Manifest per SHA-256, verweigert Überschreiben und Ablage in sichtbaren Repositorydateien. Er protokolliert ausdrücklich eine **Operatoraussage mit ausstehendem Review**; er erteilt keine Host- oder Releasefreigabe und kann eine Aussage nicht als wahr beweisen. Fehlgeschlagene Prüfungen und spätere Wiederholungen bleiben eigene Belege. Erst der berechtigte Reviewer bewertet die vollständige tatsächliche Evidenz.
