# PR6 – Lokale Produktabnahme

Abgleich: 26.10.2026. **LOCAL_REGRESSION_AND_RESTORE_PASSED / EXTERNAL_GATES_OPEN**. Die vollständige Regression, Imageprüfung und der Restore stammen vom 23.10.; sie werden nicht als neue Gesamtabnahme vom 26.10. ausgegeben. Ausgangscommit `f05cb70cc7db40d6185892e88aed6c6e4bcd871c`. Keine automatische Quellenfreigabe, Produktivmigration, Modellpromotion, Order, kein Push/Release.

## Status

| Entscheidung | Aktueller Zustand |
| --- | --- |
| DESIGN_SYSTEM_STATUS | IMPLEMENTED_AND_LOCALLY_TESTED; keine vollständige WCAG-Zertifizierung |
| UX_COMPLETENESS_STATUS | PARTIAL; PENDING_USER_TEST |
| FUNCTIONAL_COMPLETENESS_STATUS | SCOPED_LOCAL_ACCEPTANCE; 26 Browserfälle und Restore bestanden; vollständiger Fehlerraum nicht abgenommen |
| REAL_DATA_ACQUISITION_STATUS | BLOCKED_BY_SOURCE_APPROVAL; zulässiger manueller Ersatzpfad technisch geprüft |
| AUTOMATIC_REFRESH_STATUS | DISABLED_BY_DEFAULT; reale tägliche Versorgung nicht abgenommen |
| SECURITY_STATUS | SECURITY_BLOCKED |
| REAL_PORTFOLIO_STATUS | NOT_APPROVED; kein echter Brokerexport/Pilotnachweis |
| PRIVATE_DEPLOYMENT_STATUS | TARGET_HOST_NOT_VERIFIED; nur lokale Vorbereitung autorisiert |
| ML_VALIDATION_STATUS | SHADOW_ONLY; reale Forecastvalidierung offen |
| RECOMMENDATION_STATUS | GATED; keine reale P9-Strategieabnahme |

## Was geändert wurde

Neue App-Shell mit sechs Hauptbereichen, semantische Design-Tokens, Light/Dark/System, gemeinsame zugängliche Dialoge/Drawer, Suche, Tabellen/Karten, Lade-/Fehler-/Leerzustände. Dashboard, Portfolio-Onboarding und Positionen wurden neu aufgebaut. Instrumentdetails verbinden Kurse, kanonische Ereignisse und Nachrichten; Risiko zeigt ausschließlich aus gespeicherten P8-Beobachtungen abgeleitete Kurven. Die übrigen technischen Bereiche übernehmen Shell/Tokens und strukturierte Ergebnisansichten, sind nicht sämtlich als vollständig neu gestaltete Fachworkflows abgenommen.

Bestehende P4-/PR1-/P6–P10-Services und APIs werden wiederverwendet. Der Ledger bleibt die Buchhaltungsquelle. CHF-Aggregation bewertet Originalereignisse neu, statt heutige FX auf historische Summen anzuwenden. CSV-Formate sind explizit an Originalbytes und Vorschauhash gebunden. Bestätigte Einzelbuchungen, atomare Portfolio-/Kontobelege und stabile Anfrageschlüssel schützen Wiederholungen. Dokumentrückzug erhält Originale und frühere Evidenz und sperrt neue Abrufe einschließlich historischer Suche.

Behoben sind unter anderem der falsche Allokationsstatusvergleich, Nachrichtenpagination nach Filterwechsel, UUID-pflichtige Watchlistauswahl, übergreifende private Querycaches, fehlende getrennte Betreiberanzeige und unklare Importformate. Die mobile Routenprüfung fand zusätzlich einen Überlauf der Assistenten-Unterhaltungsauswahl; Flexumbruch und begrenzte Formularbreiten korrigieren ihn. Relative Produktions-API-Adressen werden für Dokumentlinks korrekt gegen den Browserursprung aufgelöst.

## Tatsächliche technische Nachweise

- Vor Änderungen: 281 Backend-, 22 Browser- und 35 Hostfälle bestanden.
- Aktueller Backendstand: **297 Tests bestanden**, Ruff/Format/Mypy bestanden, bekannte Starlette/httpx-Deprecation-Warnung.
- **35 Hosttests bestanden**.
- Frische Alembic-Migration: **0021_ui_requests, 78 Tabellen**, ohne Drift. Neue Tabellen sind technische append-only Historien; alte Daten-/Modellhashverträge bleiben bestehen.
- Frontend-Lint, Typecheck und abgeschlossener Standalone-Build bestanden. Browserprüfung nutzt `ops/docker-compose.e2e.yml`.
- **26 unterschiedliche Browserfälle bestanden, ohne Skips**: finaler Gesamtlauf 25/26; der übrige Chart-/Themefall bestand nach Korrektur seines Accessible-Name-Selektors gezielt (Anwendungsbuild unverändert). Enthalten sind 30 geschützte Start-/Unterziele auf 390/1440 px, Login, sechs primäre Bereiche, 360/390/768/1024/1440/1920 px, Light/Dark/System, Tokenkontraste, Tastaturdialog/Fokusrückkehr, tatsächliche Chart-Canvas und Zeitraumwechsel, CH-CSV, bestätigte Buchungen, Depotabgleich, Dokumentrückzug und Fachgates. Frühere fehlgeschlagene/abgebrochene Versuche bleiben erhalten; sie sind keine Gesamtpässe.
- Echte lokale Ollama-Laufzeit: qwen3:0.6b und embeddinggemma:300m mit Versions-/Digestbindung, 768-dimensionale Embeddings und Retrieval eines bereits freigegebenen synthetischen Originaldokuments bestanden. Originalbytes und Zitat-Hash unverändert, vorhandene Embeddings wiederverwendet. Direkter Chat 35.545 s, zusammen mit Embedding 51.187 s. Größerer Kontext erreichte zunächst 60 s; bei unterstützten 120 s bestand die vollständige Orchestrierung mit drei Tools und archivierter Antwort in 101.562 s. Die ignorierte lokale Konfiguration verwendet jetzt 120 s; der allgemeine Standard bleibt 60 s. Bei gestopptem Ollama bestand die gespeicherte strukturierte Ersatzantwort samt Forecastgate in 4.942 s; danach wieder gestartet. Kein Assistenten-Dauerbetriebsnachweis für den Zielhost.
- Fünf exakte Image-Scans vom 23.10., originale SBOMs formal gültig: [Inventar](security/pr6-20261023-final/inventory.json), [SBOM-Validierung](security/pr6-20261023-final/sbom-validation.json). Teilumfang, kein neuer Gesamtscan aller unveränderten optionalen PR4-Images. Der Datenbankstand vom 23.10. liegt am 26.10. außerhalb des 48-Stunden-Fensters für eine neue Releaseprüfung; keine aktuelle Freigabe daraus.
- Backup `20261023T131714Z-50868`: **502 Raw-Objekte / 503 geprüfte Dateien**, erneut gegen alle SHA256s gelesen. Isolierter Restore mit dem exakten PR6-Backend, PG17-/Seaweed-Testkandidaten und Golden CHF10’180 bestanden; PG/pgvector/JSONB/Numeric/Indizes/PIT-Trigger und alte Archivverträge geprüft. Separater networkloser Legacyprozess verifiziert unveränderte Modell-/Lockbytes. Fünf Dokumentrückzüge und 26 UI-Wiederholungsbelege besitzen eigene Checkpointhashes; der Restore-Verifier prüft beide zusätzlich zum alten Intelligence-Hash. Cleanup erfolgreich. Keine Originalvolumes migriert. [Kompakte Belege und Originalhashes](validation/PR6_LOCAL_ACCEPTANCE_EVIDENCE.json).
- Normaler lokaler Neustart am 26.10. nach vorübergehend nicht antwortendem Docker geprüft: APP_ENV=local, ASSISTANT_TEST_MODE=false, temporäre Daten-/ML-Rollen leer, Collection/Forward aus, lokaler Timeout120. Keine Docker-weite erzwungene Rücksetzung.

## Security und Remote-CI

Der Original-CI-Befund OTel1.45.0 wurde gezielt auf 1.45.1 gepatcht. Numerische Pins/alte Manifeste bleiben erhalten; neue Runtimeguards und exakte PR5-Lockarchive schützen Legacyverträge. Next16.4.2 behebt aktuelle Next-Advisories. Aktiver Core-/Assistant-Audit und npm-Produktionsaudit: null bekannte Befunde. Vollständiger npm-Dev-Audit: fünf High-Einträge einschließlich ungepatchtem braces; keine Ignores.

| Gescanntes Image | Critical | High |
| --- | ---: | ---: |
| Backend PR6 rc3 | 0 | 44 |
| Web PR6 rc6 | 0 | 0 |
| PG17-Kandidat PR5 rc3 | 0 | 0 |
| Bestehendes MinIO | 9 | 125 |
| Seaweed-Testkandidat | 0 | 5 |

Keine Securityexception erteilt. Verbleibende Befunde/Reviews und bestehende Releasegates bleiben blockierend. Der lokale PG17-/Seaweed-Restorekandidat migriert kein produktives System. Remote verify im Ausgangslauf erfolgreich, Security fehlgeschlagen; **kein neuer Remote-CI-Pass verifiziert**, da kein Push autorisiert/ausgeführt. [Details](PR6G_SECURITY_STATUS.md).

Separater Quelltext-Secret-Snapshot vom 26.10.: null bekannte Befunde, sichere Dateihashliste veröffentlicht. Lokale PR6-Dokumentlinks und die unveränderte Folge der 212 Masterhauptabschnitte sind geprüft. Diese Abschlussprüfungen aktualisieren keine Vulnerability- oder Produktionsfreigabe.

## Lokale Performance

Einzelmessungen unter Windows/Docker Desktop, laufenden lokalen Diensten und zeitweise parallelem Build; synthetisches Archiv, kein Zielhostbenchmark. IPv4-Loopback: Login 506 ms, Dashboard-API 677 ms, Portfoliozusammenfassung 226 ms, Instrumentensuche 59 ms, Kurschart-API 42 ms, Risikohistorie 85 ms. Drei parallele Dashboardanfragen: jeweils 1.48–1.56 s, insgesamt 1.61 s. Das sind API-Zeiten, keine vollständigen wahrgenommenen Browserzeiten.

Ein separater localhost-Lauf benötigte etwa 2.1–3.1 s je Anfrage. Der Vergleich grenzt einen lokalen Namens-/Verbindungsanteil ein; er begründet keine Änderung einer fremden Produktionskonfiguration und keine SLA. Originale: `backups/pr6-local-api-performance.json` und `...-ipv4.json`.

Browsermessung vom 23.10.: Login bis geladenes Dashboard einschließlich Historie **3’843 ms**. CH-CSV-Vorschauen **92/86 ms**, Commit **83 ms**; dies sind Requestzeiten für die kleine synthetische Datei. 60 Routen-/Breitenaufrufe: Shell median **458 ms**, maximal **1’142 ms**, ohne Garantie vollständig geladener Fachanalysen. Originale JSONs liegen neben den Browserartefakten. Echte externe Aktualisierung ist wegen fehlender Quellenfreigabe nicht gemessen; größere Brokerdateien und ein echter Zielhost ebenfalls nicht. Kein Leistungsversprechen für einen unbekannten Zielhost.

Zusätzlicher Sichtlauf nach Docker-Wiederanlauf am 26.10.: Login bis geladenes Dashboard samt Historie **24’060 ms**, Risikopanel samt Historienauswahl **6’900 ms**. Normalmodus ohne Testprovider, 390/1440 px ohne Seitenfehler oder finanzielle Mutation. Die langsameren Einzelwerte bleiben ausdrücklich erhalten; wechselnde lokale Last/Kaltstart ist keine isolierte Abfrageanalyse. Vollseitenbilder werden nach Rückkehr zum Seitenanfang aufgenommen, damit feste Navigation nicht mitten im Bild erscheint. Originale: `backups/pr6-final-visual-20261026/`.

Reviewbilder mit ausdrücklich synthetischen lokalen Prüfdaten: [Desktop/Hell](ux/screenshots/PR6-dashboard-1440-light.png), [Mobil/Dunkel](ux/screenshots/PR6-dashboard-390-dark.png). [Normalmodus-, Sichtprüfungs- und Bildhashnachweis](validation/PR6_NORMAL_RUNTIME_20261026.json). Die sichtbaren Testwerte sind keine realen Portfolio- oder Marktbelege.

## Reale Quellen und Märkte

Allgemeine Prüfung verschiedener ISINs gemäß Nutzerentscheidung; keine behauptete weltweite Kursversorgung. ISIN benötigt weiterhin konkrete MIC/Handelswährung und gegebenenfalls menschliche Auflösung. Manuelle CSV ist im bestehenden Gate zulässig und lokal mit synthetischen Originalen geprüft. ECB, SEC, OpenFIGI, SNB, Alpha Vantage, IR/RSS bleiben ohne konkrete neue Quellenentscheidung gesperrt; Yahoo weiterhin BLOCKED. Kein neuer Finanzproviderabruf. Primärdokumentation wurde am 23.10. geprüft; Erreichbarkeitsfehler sind ausdrücklich dokumentiert.

[Quellenbericht](PR6E_DATA_ACQUISITION_REPORT.md), [Einzelnachweise](data/LIVE_PROVIDER_TEST_MATRIX.md), [tatsächliche Abdeckungsgrenzen](data/REAL_MARKET_COVERAGE.md). Weder CH/US/internationale Aktien/ETFs noch Delistings, historische Membership oder vollständige Corporate Actions sind allgemein real abgenommen. CHF/EUR/USD im bestehenden Portfolioumfang bedeuten nicht alle Handelswährungen.

## Noch erforderlich

Für einen echten Pilot: Securityfreigabe mit aktuellen exakten Scans, rechtmäßige Originale und konkrete Kurs-/FX-/Action-Abdeckung, echter Depotabgleich und unabhängiger Anfängertest (**PENDING_USER_TEST**). Bis zur privaten Produktion bleiben außerdem Zielhost/VPN, CA/Clients, unabhängiges Backupziel/Zeitschaltung und Schlüsselrecovery offen. Vollständige manuelle Screenreader-/Fehlerraumabnahme und LLM-Dauerbetrieb sind nicht behauptet. Quellen-, Forecast-, Strategie- und Betriebsfreigaben bleiben getrennt. Der lokale Restore ist kein Nachweis eines unabhängigen Backupziels. **Der echte private Portfolio-Pilot ist weiterhin nicht freigegeben.**

[Funktionsmatrix](ux/FUNCTIONAL_MATRIX.md), [Nutzerwege](ux/USER_JOURNEYS.md), [Designsystem](PR6B_DESIGN_SYSTEM.md), [UX](PR6C_UX_ACCEPTANCE.md), [Dashboard](PR6D_DASHBOARD_ACCEPTANCE.md).
