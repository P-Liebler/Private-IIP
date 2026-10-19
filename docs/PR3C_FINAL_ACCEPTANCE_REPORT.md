# PR3C – Private Endabnahme

Stand 19.10.2026. **LOCAL_ACCEPTANCE_PASSED; TARGET_ACCEPTANCE_BLOCKED_NO_HOST.** Der Nutzer hat lokale Vorbereitung bestätigt. Keine reale Installation oder Windows-/Android-VPN-/CA-Abnahme behauptet.

## Matrix

TESTED_LOCAL bezeichnet Tests mit lokalen Diensten/ausdrücklichen synthetischen Fixtures. TESTED_STAGING bedeutet einen lokalen isolierten Staging-Stack, niemals den echten Zielhost. TARGET bleibt für alle Pflichtbereiche BLOCKED, bis echte Evidenz vorliegt.

| Bereich | Implementierung / lokal | Staging | Ziel |
| --- | --- | --- | --- |
| Security | TESTED_LOCAL; Imagebefunde offen | HTTPS-/Headerprobe bestanden | BLOCKED |
| Netzwerk/VPN/DNS | Sichere Compose-Bindings / Offline-Goldens | Nur localhost | BLOCKED |
| TLS/CA | Kette/Hostname getestet | TESTED_STAGING per Python-Truststore | BLOCKED; kein Clienttrust-Nachweis |
| Auth | TESTED_LOCAL; Argon2id/TOTP/Sessions/Ownership | Login/Cookie bestanden | BLOCKED |
| Integrität | TESTED_LOCAL; Raw-/Modell-/Immutable-Gates | Kein positiver Real-Datenbeweis | BLOCKED |
| Portfolio | TESTED_LOCAL; Golden CHF 10'180 | TESTED_STAGING | BLOCKED |
| Research | TESTED_LOCAL; Lücken/Provenienz | Fehlende reale Fakten bleiben fehlend | BLOCKED |
| Backtests | TESTED_LOCAL; PIT/Execution/Kosten/Replay | Keine reale historische Eignung | BLOCKED |
| ML-Gates | TESTED_LOCAL; SHADOW/Abstention | Keine Promotion | BLOCKED |
| Risiko/Szenarien | TESTED_LOCAL; fehlende Historie sichtbar | Keine erfundenen Kennzahlen | BLOCKED |
| Empfehlungen | TESTED_LOCAL; harte P7/P9-Gates | GATED | BLOCKED |
| Assistant/RAG | TESTED_LOCAL; Read-only/Quellen/Ownership | Optionaler LLM nicht Voraussetzung | BLOCKED |
| Alerts/Brief | TESTED_LOCAL; Deduplication ohne LLM | Zustellung nicht belegt | BLOCKED |
| Optimizer/Time Machine | TESTED_LOCAL; Simulation/Archive | Keine rückdatierte Evidenz | BLOCKED |
| Collector | TESTED_LOCAL; Source-/Retry-/Raw-Gates | Automatik aus | BLOCKED |
| Backup/Restore | TESTED_LOCAL; Integritäts-/Fehlergoldens und vollständiger PR3-Restore | Neues isoliertes Projekt ohne Hostports | BLOCKED |
| Monitoring | TESTED_LOCAL; Metriken/Regeln | Prometheus/Grafana-Scrape geprüft | BLOCKED |
| Performance/Restart | TESTED_LOCAL; tatsächliche Messwerte unten | Kontrollierte Containerfaults bestanden | BLOCKED; kein Hostrestart |

Die volle endgültige Backend-Regression ist **264 passed in 120,33 Sekunden**; vorbestehende 257 Fälle erhalten. Browserabschluss: **21 passed in 2,2 Minuten**. Ein zu früher Coverage-Assert sowie vorübergehende 503-/Socketfehler während großer Image-Transfers wurden untersucht. Der Coveragefall wartet auf die erfolgreiche Antwort des konkreten gewählten Intervalls; die anschließende vollständige Browserregression ist grün. Report-Authheaders werden vor Ausgabe redigiert. Negative Source-/Session-/TOTP-/Ownership-/Assistanttests bleiben Teil der bestehenden Regression. Kein Live-Finanzprovider wurde aufgerufen. Frischer isolierter PR3-Restore mit 320 Rohobjekten, alten Archiv-Hashes und Golden CHF 10'180 bestanden.

Zusätzlicher tatsächlicher Chromium-Smoke gegen den lokalen Caddy: Login→Dashboard→Portfolio→Instrument→Logout ohne Page-/CSP-Fehler. Node prüft vorher Leaf/Kette/Hostname gegen die öffentliche Test-CA; der temporäre Browser verwendet ausschließlich den so ermittelten Leaf-SPKI-Pin. **Das ist ein CSP-/Hydrationstest, kein Windows-/Android-OS-Trustnachweis** und keine Zielabnahme. Die Client-Trust-Gates bleiben offen. Artefakt `backups/pr3-staging-csp-browser.json`, Workflow `ops/staging_browser_smoke.cjs`.

## Tatsächlich gemessene lokale Performance

Windows-Arbeitsplatz mit 33.178.040 KiB sichtbarem RAM; Docker Engine stellt zwölf CPUs und 16.579.235.840 Bytes RAM bereit. Docker-/Host-Ressourcensnapshot unter `backups/pr3-final-resources.txt`; es liefen zusätzlich Entwicklung, Staging und Sicherheitsprüfungen. Testlast: **ein Client, eine gleichzeitige Fachoperation**, kein Last-/Skalierungstest und keine Zusage für einen künftigen Zielhost.

| Operation über lokal vertrautes HTTPS | Beobachtete Dauer |
| --- | --- |
| Login | 3,333 s |
| Portfolio-Bewertung | 2,462 s |
| Dashboard-API | 2,258 s |
| Instrument-API | 2,306 s |
| Risikoberechnung mit expliziten Historienlücken | 3,567 s |
| Assistant-Verfügbarkeitsabfrage ohne LLM | 2,989 s |
| Container-Prozessstart mit vorhandenen Daten/Caches | 96,382 s |
| API-Warmneustart | 12,776 s |

Werte enthalten den Windows/Python-Client-/TLS-/Proxyweg, nicht nur serverinterne Rechenzeit. 34 einzelne Request-/HTTPstatus-/Zeitmessungen stehen im lokalen Recovery-JSON. Kein ungefangener Fehler im abschließenden Probe-Runner; fehlende LLM-/Finanzwerte bleiben unavailable. Ein echter LLM-Inferenz- oder RAG-Performancebenchmark wurde nicht ausgeführt; die vorherige funktionale RAG-/Ownershipregression nutzt die ausdrücklich synthetischen Fixtures. Host-/Client-/Ziel-RAG-Performance bleibt offen.

`/system/status` ist nur für explizit autorisierte Operationskonten zugänglich. Es zeigt Dienst-/Backup-/Restorezustände, Alter, Sammlung/Forwardflags und konservative getrennte Freigaben. Ungeprüfte Operatorbelege sind NOT_VERIFIED, keine anklickbare Freigabe. Finanzbereitschaft muss weiterhin über vorhandene PR2-/P7-/P9-Evidenz bewertet werden; der Systemstatus erteilt keine Promotion.

Die abschließende Ergänzung „letzter erfolgreicher Backupstand“ wurde mit sieben gezielten Backendfällen, Typecheck, erneutem Standalone-Build und einem zusätzlichen Operator-Browserfall erfolgreich geprüft. Normale lokale Einstellungen sind danach wieder aktiv, Testfreigabe zurückgesetzt und konfigurierte Healthchecks grün.

## Unabhängige Entscheidungen

- **PRIVATE_CORE_DEPLOYMENT_NOT_VERIFIED**
- **REAL_DATA_LIMITED**
- **FORECASTS_SHADOW_ONLY**
- **RECOMMENDATIONS_GATED**

Offen: Zielhost, realer VPN-/DNS-Zugang, Windows-/Android-TLS-Trust, unabhängiger Backupmount/-Zeitplan, vollständige Schlüssel-/CA-Recovery, zugestellte Monitoringalarme, Sicherheitsbefunde der Images. [Operatorprotokoll](operations/OPERATOR_ACCEPTANCE_CHECKLIST.md).
