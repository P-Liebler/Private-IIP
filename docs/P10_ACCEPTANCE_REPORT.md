# P10 – technische Abnahme

Prüfdatum: 2026-10-15. **P10 FUNCTIONAL — DATA/SOURCE GATED. V3+ NOT RELEASED.**

## Ausgangslage und Trennung von P9

Start `main`, `1294080ba0042706d4df99f37f39646aea736673`, sauberer Arbeitsbaum. Baseline 155 Backendtests. P9 wurde vorher separat abgenommen: [P9-Bericht](P9_ACCEPTANCE_REPORT.md), Migration 0015, 55 Tabellen, deterministische harte Recommendation-Gates, elf Browserfälle und isolierter Restore. P10 folgt darauf mit Migration **0016_local_intelligence** und 16 weiteren Tabellen. Keine frühere Migration wurde geändert.

Neue Pakete: `pgvector==0.5.1`, `pypdf==6.20.1`, im separaten `requirements-assistant.lock` gepinnt, mit `--no-deps` nach dem unver?nderten numerischen Core installiert. Bestehende NumPy-/SciPy-/scikit-learn-Abhängigkeiten werden wiederverwendet. Images für API, Worker, Scheduler und ML-Worker erfolgreich gebaut; `pip check` ohne Konflikte. Optionaler privater Ollama-Dienst, keine verpflichtende Cloud oder kostenpflichtige API.

## Umsetzung

| Bereich | Ergebnis |
| --- | --- |
| Ollama | Version 0.40.4 mit Image-Digest, privates Netz ohne Host-Port, CPU-/RAM-/Parallelitätsgrenzen, explizite Modelldownloads, Health unabhängig von Kern-Readiness |
| Modelle | Qwen3 0.6b und EmbeddingGemma 300m tatsächlich lokal ausgeführt, vollständige Digests archiviert; 768 Embeddingdimensionen, gemessene Norm 0.9999997311 |
| Assistant | Zehn typisierte private Read-only-Tools, feste Faktenklassen, serverseitig geprüfte Faktenauswahl und Quellen, SSE, Abbruch, Historie, Löschung und Retention; keine freie Erfindung von Zahlen oder Empfehlungen |
| RAG | Private Rechteprüfung, Quellen-/Nutzungsgates, exakte MinIO-Originale vor Parsing, begrenzter PDF-Prozess, Chunks und Hashes, versionierte pgvector-Embeddings, Filter und geschützte Originallinks |
| Quellenvalidierung | MANUAL_DOCUMENTS/MANUAL_EVENTS beginnen UNKNOWN/deaktiviert; Operator-Allowlist und dokumentbezogene Rechte nötig; nur ausdrücklich benannte TEST_-Quellen für technische Fixtures angelegt |
| Sicherheit | Besitzprüfung, keine SQL-/Shell-/URL-/Write-Tools, Schema- und Kontextgrenzen, Prompt-Injection bleibt Text, unbekannte Fakten-IDs verworfen, erkannte Geheimnisse redigiert, DB-Parameter verborgen |
| Alerts | Acht Typen, versionierte Regeln/Auswertungen/Ereignisse, gültige Vorgängerwerte, Schwellenübergänge, Cooldown, persistente Deduplizierung und private Notifications; fehlende Eingaben bleiben UNAVAILABLE |
| Kalender | Operatorgeprüfte manuelle Original-JSONs, Quelle vor Nutzung geprüft, Korrekturen append-only, Stornierung als belegter Zustand ohne erfundenen Nullwert |
| Daily Brief | Strukturierter unveränderlicher Bericht ohne LLM, belegte Performance und Änderungen, explizite Lücken, private Konfiguration, UTC/IANA-Zeitzonen/DST, begrenzter Wiederanlauf und eindeutiger Tagesbericht |
| Optimizer | Vier Simulationsziele, renditeorientierter Modus nur mit Produktionsprognosen, Ledoit-Wolf/PSD/Konditionierung, Kosten und harte Grenzen, P8-Replay, Szenarien, Vergleichs- und Sensitivitätsanalyse; keine Ledger-Schreibaktionen |
| Time Machine | Strikter tatsächlicher Archivstand, spätere Rekonstruktion getrennt; Raw-Belege, Restatements, tatsächliche Modell-/Prognoseexistenz, spätere Outcomes separat; vor Portfolioerstellung kein fingierter Nullwert |
| UI/API | Geschützte Routen `/assistant`, `/documents`, `/alerts`, `/daily-brief`, `/optimizer`, `/time-machine`; Notification-Badge, Quellenlinks und Historien |
| Monitoring | Aggregierte Bestands-/Fehler-/Operationsmetriken ohne Nutzer-/Promptlabels, Scheduler-Heartbeat und Fehlerzahl in Valkey |

## Tatsächliche Prüfungen

- Abschließender vollständiger Backendlauf nach Neubau und Neustart der Dienste: **195 Tests bestanden**, 144,25 Sekunden. Eine bestehende Starlette-TestClient-DeprecationWarning; kein Testfehler.
- **13 von 13 Browserfällen** im kompilierten Standalone-Produktionsserver bestanden, 59,6 Sekunden. Enthalten: bisherige P4–P9-Fälle und beide neuen P10-Fälle.
- Ein vorheriger Entwicklungslauf hatte drei Fehler bei Anmeldung, asynchroner Profilanzeige und Navigation. Login akzeptiert Eingaben nun erst nach Hydration; Profilbearbeitung wartet auf geladene Daten. Die CI-Browserprüfung startet den gebauten Standalone-Server über `ops/docker-compose.e2e.yml`. Keine laufende Entwicklungskompilierung während der Abnahme.
- Backend-Unit-/Integrationstests verwenden lokale Services, explizite Fixtures und injizierte Stubs; keine Live-Finanzprovider. CI lädt keine LLM-Gewichte. Der Stub ist ausschließlich in APP_ENV=test zulässig und wird vor normalem Betrieb ausgeschaltet.
- Geprüft: unbekannte Modell-/Quellen-IDs, SQL-/Write-Argumente, fremde private IDs, Chatlöschung, abgebrochene Streams, unveränderliche Brief-/Dokumentzeilen, Hash und Rechte, später importierte Restatements, nachträgliche Prognosen, fehlende Originale, UTC und DST, fehlende Kovarianz/FX, unerfüllbare Grenzen und vier Optimizerziele.
- Kalendergolden: Originalbytes, zukünftiger Testtermin, genau eine Notification, Wiederholung und Wiederanlauf, korrigierte Stornierung, Rechteentzug. Kein echter Earnings-Termin erfunden.
- Mehrere Cashkonten derselben Währung teilen einen FX-Risikofaktor; fehlende FX-Beobachtung sperrt die Optimierung. Seit dem Snapshot geänderte Stammdaten sperren neue Simulationen.
- Ruff und Format bestanden; Mypy für 173 Anwendungsdateien bestanden. Frontend lint/typecheck/build bestanden, einschließlich gebauten Standalone-Server im Container.
- Alembic driftfrei; komplette Migration auf einer frischen temporären Datenbank: 0016, **71 erforderliche Tabellen**.
- Echter lokaler Ollama-Test mit beiden realen Modellen erfolgreich; ein selbst verfasstes technisches PDF mit echtem Modell indexiert. Zusätzlich explizites TEST_ONLY-Embedding für CI-/Browserprüfung, getrennt modellversioniert.
- Tatsächlicher Ausfall: Ollama und MLflow gestoppt → Portfolio CHF 10’180, Research, Risiko, gesperrte Recommendations, strukturierter Assistent und Daily Brief weiterhin nutzbar. Ledger unverändert. MinIO gestoppt → Originaldownload explizit HTTP 503; Buchhaltung bleibt nutzbar. Dienste danach wieder gestartet.
- Scheduler tatsächlich ausgeführt: erfolgreiche Dispatchläufe, keine Fehler, Heartbeat sichtbar. Privater Tagesbericht bleibt idempotent.
- GitHub Actions für diese Änderungen **nicht remote verifiziert**; Workflow aktualisiert, kein Push oder Release. Der vom Nutzer bestätigte Ausgangslauf ist kein CI-Nachweis für diese Änderungen.

## Grenzen und Roadmap

| Gate | Stand |
| --- | --- |
| P9 technical status | FUNCTIONAL — RECOMMENDATIONS GATED; separat abgenommen |
| V3 recommendation validation | NOT VALIDATED; keine reale Strategie-/Produktionsprognosefreigabe |
| P10 technical status | FUNCTIONAL — DATA/SOURCE GATED; separat technisch abgenommen |
| V3+ release readiness | NOT RELEASED; technische Fixtures sind kein fachlicher Anlagestrategienachweis |
| P4 production gate | Homelab/VPN, CA, echte Backup-Mounts/-Zeitplan und Schlüssel-Recovery weiterhin offen |
| P5 source gate | Keine reale Quelle ungefragt freigegeben oder aktiviert |
| P6 historical completeness | Reale historische Vollständigkeit weiterhin eingeschränkt; spätere Importe beweisen keine PIT-Historie |
| P7 production model | SHADOW / keine validierten realen Produktionsprognosen |
| P8 risk data completeness | Reale Kalender-/Actions-/Kurs-/FX-Abdeckung weiterhin maßgeblich; fehlende Eingaben sperren Kennzahlen |

Der Optimizer verwendet ein geschlossenes Bestandsuniversum, konstante investierte Nominale und festes Fremdwährungscash. Er unterstützt keine Leverage-/Negativcash-Optimierung und keine impliziten FX-Trades. Begrenzte Stresschecks beweisen keine Robustheit in allen Märkten. Renditeorientierte Optimierung bleibt ohne P7-Freigabe gesperrt.

PDFs ohne extrahierbaren Text erhalten keine OCR; Tabellen werden nicht automatisch zu Finanzfakten. Temporäre Inhaltsrechte mit notwendiger Ablauf-Löschung werden nicht angenommen. Retention löscht aktive Chats, nicht rückwirkend vorhandene Backups. Modellgewichte sind optionale Laufzeitdaten außerhalb des Finanzbackups; nach Restore muss derselbe Digest verfügbar sein oder ein ausdrücklich neuer Index erzeugt werden.

Originale P6-News-Mappingversionen sind für historische Zuordnung nötig. Fehlende Quellen, Archive, Modelle, Sentimentklassifikationen oder Termine bleiben sichtbar nicht verfügbar. Keine nachträglichen Prognosen, keine autonomen Trades, keine kostenpflichtige Pflichtabhängigkeit.

## Im Restore gefundene Dependency-Abweichung

Der erste isolierte Lauf wurde vom unver?nderten P7-Modelllader mit `ARTIFACT_DEPENDENCY_MISMATCH` gestoppt. Ursache: Erg?nzung der zwei P10-Pakete im vollst?ndigen Core-Lockfile. Ein Vergleich mit dem Ausgangsstand zeigte keine ge?nderte numerische Paketversion. Core-Eingabe-/Lockfiles wurden bytegetreu beibehalten; alle **64 installierten Core-Pins** wurden anschließend gegen den Lockfile geprüft; die beiden Zusatzpakete liegen jetzt in einem eigenen Lockfile, werden mit `--no-deps` installiert und separat im Codemanifest aufgezeichnet. Alte Modellartefakte oder ihre Metadaten wurden nicht ver?ndert; die exakte Core-Pr?fung bleibt bestehen. [ADR-022](decisions/ADR-022-preserve-model-dependency-pins.md). Der nachfolgende erfolgreiche Restore ist der Abnahmenachweis.

## Abschlussnachweise

**Isolierter Restore bestanden: 2026-10-15 14:16:58–14:18:37 UTC.** Backup `backups/p10-acceptance/sets/20261015T140739Z-868`, erstellt 14:07:39–14:07:50 UTC. Hintergrundjobs und API waren für den Backup-Checkpoint angehalten; danach normale Dienste wieder gestartet. Der Prüflauf verwendete eigene temporäre PostgreSQL-/MinIO-/Valkey-/API-Ressourcen ohne Hostports, danach wurde ausschließlich dieses temporäre Projekt entfernt.

Geprüft: Migration, bytegleiche Originale, Dataset-Replay, unverändertes P7-Artefakt einschließlich strikter numerischer Pins und MLflow-Metadaten, Prediction-/Outcome-Historie, P8-Risiko-/Szenario-/What-if-Archive, P9-Profile/Regeln/Recommendations sowie private P10-Archive. Login und Bewertung lieferten wieder exakt **CHF 10’180**. Keine Modellgewichte für den Restore heruntergeladen, kein produktives Modell hochgestuft.

| Archiv am eingefrorenen Checkpoint | Anzahl |
| --- | ---: |
| Prognosen / Outcomes | 11 / 0 |
| Risiko / Szenarien / What-if | 16 / 9 / 10 |
| Recommendations / Profilversionen | 5 / 4 |
| Dokumente / Chunks / exakte Embeddings | 2 / 2 / 2 |
| Chatnachrichten / Alert-Auswertungen | 6 / 7 |
| Daily Briefs / Optimizerläufe | 1 / 3 |
| Kalender-Versionen / Alert-Ereignisse / Notifications | 2 / 1 / 2 |

Content-Checkpoints:

```text
P7 prediction_history_hash
4c3bff825103de11c4087c04886c884a34d40052b2c42ecfe95db38792c6bc59
P8 risk_history_hash
b18db7c6ba4400d3c3473968751ad5cad3e39dab99fe8bb785f30dbc003d23b2
P9 recommendation_history_hash
a4575e5b0385b1b377364e15586164a9750871a3d29f39d92a39972a1f845b5f
P10 intelligence_history_hash
942873124708a6ecf68ec0ee82970ae68dc47393741457d0d5fd908885e15efb
```

Die Hashes beziehen sich auf den Backupzeitpunkt; spätere private Auswertungen und operative Prüfzeitpunkte verändern erwartungsgemäß den Live-Checkpoint. Originale und bestehende Finanzarchive bleiben unverändert. Neue positive Kalender-/Alertdaten sind ausdrücklich selbst verfasste **SYNTHETIC**-Restore-Fixtures, nach der Korrektur deaktiviert; sie sind keine echten Earnings-Termine.

Normalzustand nach Abnahme: APP_ENV=local, ASSISTANT_TEST_MODE=false; Standard-Entwicklungsserver und Hintergrunddienste wieder verfügbar. GitHub-CI, reale Modell-/Strategievalidierung und Zielproduktionsfreigabe wurden dadurch nicht geschlossen. Der Arbeitsstand bleibt zur Prüfung lokal, ohne Push oder Release.
