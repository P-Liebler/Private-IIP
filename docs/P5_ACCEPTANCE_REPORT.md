# P5 — Fundamentals, Research und V1.5

Stand: **2026-10-13**. Status: **FUNCTIONAL WITH GATED SOURCES**. P4 bleibt **FUNCTIONAL — PRODUCTION GATE OPEN**; V1.5 ist für die ungeprüfte Zielinstallation nicht produktionsfreigegeben. P6 wurde nicht begonnen.

## 1. Baseline

Branch `main`, Start-Commit `af101ffed5203cc098599c1409587fd93d1ec421`; Arbeitsverzeichnis zu Beginn sauber. Baseline: 61 Backend-Tests bestanden, eine upstream Starlette-Warnung. Änderungen liegen lokal vor. Kein Commit, Push, Release oder Remote-CI-Erfolg wird behauptet.

## 2. Migrationen und Versionierung

`0008_research` ergänzt neun Tabellen: filings, fundamental_fact_versions, research_snapshots, research_metrics, watchlists, watchlist_items, news_articles, news_instruments und analyst_estimate_snapshots. Die aktuelle Fact-Sicht wird aus akzeptierten Versionen abgeleitet; keine zusätzliche veränderliche Fact-Tabelle ist nötig. PK/FK, Raw-/Zeilen-Idempotenz, Watchlist-Mitgliedschaft und PIT-/Filterindizes sind vorhanden.

`0009_filing_document` erhält bisherige Response-Hashes unter `response_hash` und ergänzt nullable `document_hash` für wirklich heruntergeladene Primary-Bytes. Unbekannte Dokumenthashes werden nicht erfunden. Frühe Migrationen 0001–0007 bleiben unverändert. Bestehende DB und frischer Weg bis 0009 wurden geprüft; 30 erforderliche Tabellen.

## 3. SEC

Submissions, Companyfacts und 10-K/10-Q einschließlich Amendments werden aus offiziellen JSON-Verträgen gelesen. CIK/Ticker-Konflikte brauchen Review. Getrennte Filing-Metadaten mit Acceptance-Zeit und exakte Rohantworten sind gespeichert. Ein gesonderter geschützter Download archiviert Primary-Dokumente von geprüften SEC-Archive-URLs, mit tatsächlichem Hash und eigener Filing-Version; dafür ist Scope `filings` erforderlich. HTML-Downloads werden nicht ungeprüft in Finanzzahlen umgewandelt.

Gate vor jedem Request einschließlich Retry, 20-Sekunden-Timeout, maximal drei Versuche, Backoff/Jitter, begrenztes Retry-After. Valkey koordiniert ein gemeinsames Sliding Window, standardmäßig fünf, höchstens zehn Requests/Sekunde; zusätzlich gilt das Source-Minutenlimit. Valkey-Ausfall scheitert kontrolliert. Config und Source müssen beide aktiviert sein; echte Kontakte werden nicht hardcodiert. Details und datierte Primärquellenprüfung: [SEC](architecture/sec-collector.md). Kein Live-Finanzprovider wurde zur Verifikation aufgerufen.

## 4. Company IR

Ein expliziter ReportContract trennt URL/Host, Collector, CSV-Parser, Mapping und Validierung. Der Host muss im genehmigten Source-Scope stehen. Private Adressen, unzulässige URLs und Redirects scheitern. Tatsächlich geprüftes Format ist strukturierte UTF-8-CSV plus validierter manueller Import. **Kein reales Unternehmen besitzt bereits einen abgenommenen automatischen HTML/PDF-Connector.** Die CH-Tests sind ausdrücklich manuelle synthetische CHF-Reports, kein Nachweis einer produktiven Schweizer Website-Anbindung. [Vertrag und Grenzen](architecture/company-ir.md).

## 5. Fundamentals und PIT

Alle Basismetriken aus Abschnitt 43 sind normalisierte interne Namen. Money, Per-share und Shares, Instant, Annual, Quarter und YTD bleiben getrennt. Hard-Gates prüfen Identität, finite Decimal-Präzision, Einheiten, Währungen, konsolidierte Werte, Perioden und Zeitbelege. Negative Gewinne/Cashflows bleiben legitim. Quality folgt erst nach Hard Validation; abgelehnte Fakten bleiben mit Raw-Referenz sichtbar.

`known_at` ist belegte Veröffentlichung; ohne Beleg gilt eigener Empfang. `observed_at` und `retrieved_at` bleiben eigene Zeiten. Historische Abfragen verlangen beide ≤ `as_of`. Spät importierte Berichte erzeugen keine frühere lokale Archivhistorie. CSV bietet Upload, Mapping, Preview, Prüfung, Bestätigung und atomaren Commit; Import gehört dem hochladenden Nutzer und wird vor Parsing archiviert. Die MANUAL_CSV-Rechte werden nicht erweitert. [Vertrag](architecture/fundamentals.md).

## 6. Restatements

Korrekturen erzeugen neue Fact-Versionen und Ersetzungsbezüge. Original 1000 und später 950 bleiben erhalten; historische lokale Sicht vor der Korrektur liefert 1000, danach 950. Beobachtungen derselben Raw-/Zeilenidentität werden nicht doppelt eingefügt. Quellen-/Kontextkonflikte ersetzen keine gültigen Werte still; ungelöste jüngere Konflikte suspendieren Scores. `/financials/versions` zeigt erhaltene Versionen, einschließlich abgelehnter Beobachtungen.

## 7. Metrics

Margins, Revenue/EPS/FCF YoY, FCF, ROE/ROA/ROIC, Debt/Equity, Net Debt, Current/Quick Ratio haben dokumentierte Formeln und Eingabeversionen. FCF kann reported oder konsistent aus OCF minus positivem Capex abgeleitet sein; widersprüchliche Definitionen sind unverfügbar. Negative/Null-Vorjahresbasen erzeugen keine irreführende Wachstumskurve. TTM braucht vier zusammenhängende vergleichbare diskrete Quartale, keine YTD-Doppelzählung oder interpolierten Lücken. Closing-Balance-ROE/ROA und effektive Tax-Rate bei ROIC sind sichtbare methodische Entscheidungen. [Formeln](architecture/fundamentals.md).

## 8. Valuation

P/E, P/S, P/B, EV/EBITDA, EV/Revenue, EV/FCF, FCF/Earnings Yield sowie Market Cap/EV sind deterministisch implementiert. Alle Eingaben müssen am Stichtag bekannt und kompatibel sein; Preise kommen ausschließlich aus P3. Aktiengattung/Split-Stand müssen ausdrücklich belegt sein. Fehlende Schulden, Preferred Equity oder Minority Interest werden nicht zu null. Negativer Gewinn erzeugt kein Standard-P/E. Forward P/E/PEG bleiben ohne zuverlässigen Schätzungs-/Per-share-Vertrag unavailable. [Definitionen](architecture/valuation.md).

## 9. Scores

Quality, Growth, Value, Momentum und Stability nutzen die versionierte absolute Rubrik. Jeder Score zeigt Coverage, Drivers, Gewichte, Skalierung, Missing-Inputs und Regelversion. Fehlende Pflichtinputs geben keinen Ersatzscore und keine Umgewichtung. Keine privaten Marktperzentile oder ML-Entscheidungen. Momentum bleibt ausgesetzt, solange die P3-Action-Abdeckung UNVERIFIED ist. Snapshot-Speicherung erhält vollständiges Ergebnis und Inputversionen. [Gewichte und Grenzen](architecture/research-scoring.md).

## 10. Screener

Datenbankfilter für Land/Börse/Sektor/Industrie/Asset Type und tatsächlich verfügbare numerische Metrics/Scores, Sortierung, Pagination maximal 100, keine Neuberechnung aus Raw-Daten pro Request. Null/unavailable wird von numerischen Filtern ausgeschlossen. Lesemodell, Berechnungszeitpunkt, Kurse, Quelle, Qualität und fehlende Daten bleiben sichtbar. Test mit 300 isolierten Instrumenten: vier SELECTs, 25 Resultate in 0.233 Sekunden auf diesem Rechner. Das ist ein lokaler Nachweis, keine globale Markt-/Hardware-SLA.

## 11. Watchlists

Erstellen, Umbenennen, Archivieren, Instrument hinzufügen/entfernen, Notizen/Tags und geschützte Nutzerzuordnung. Doppelte Mitgliedschaft ist verhindert. Fremder Nutzerzugriff wird verweigert. Quotes stammen unabhängig von Fundamentals aus P3; Datum, Alter, Qualität und Quelle sind sichtbar. Scores bleiben fehlend, wenn Research nicht verfügbar ist.

## 12. News

Freigegebene RSS-2.0-Metadaten und manueller JSON-Import; Rechte für die gesamte Raw-Feed-Archivierung müssen gesondert vorliegen. Keine Artikel-/Paywall-Downloads. Excerpts nur bei genehmigtem Scope. Duplikate nach normalisierter URL, Hash zulässiger Headline-Metadaten und Titelähnlichkeit; Quellenbeobachtungen bleiben verknüpft erhalten. Explizite Identifier können sicher zugeordnet werden; mehrdeutige Ticker/Namen bleiben Kandidaten. Veröffentlichung, Entdeckung und Abruf sind getrennt. Ohne lokales Modell bleibt Sentiment null/unavailable. GDELT und ein automatisches Entity-Embedding-Modell werden nicht behauptet. [Pipeline](architecture/news-pipeline.md).

## 13. Analyst Estimates

Typisierte EPS/Revenue/Price-Target/Recommendation-Snapshots, manueller gated JSON-Import, Raw-Beleg, Versionsbezug, tatsächlicher erster Eingang und historische Abfrage. Keine rekonstruierte Konsenshistorie aus einem aktuellen Wert. Wiederholung derselben Raw-Version ist idempotent; echte neue Beobachtungen beginnen ab ihrem tatsächlichen Eingang. Keine automatische Quelle aktiviert; Yahoo bleibt gesperrt. [Snapshot-Vertrag](architecture/analyst-estimates.md).

## 14. UI

Geschützte Research-, Watchlist- und News-Seiten. Instrumentseite behält V1-Kurse und ergänzt Financials, Valuation, Growth, Profitability, Momentum, News und Scores, Jahres-/Quartals-/TTM-Sicht, berichtete/restated Facts, echte Balkendiagramme und Herkunft. Keine interpolierten Unternehmensquartale. CSV-Mapping/Preview/Confirm und Research-Qualität erweitern den vorhandenen Datenqualitätsbereich. Forecasts, Risikomodelle und Empfehlungen wurden nicht ergänzt.

## 15. Source Registry

| Quelle | Gate | Aktivierung |
| --- | --- | --- |
| MANUAL_CSV | APPROVED | enabled; bisheriger Scope unverändert |
| YAHOO | BLOCKED | disabled |
| STOOQ, OPENFIGI, SNB, ECB | UNKNOWN | disabled |
| SEC_EDGAR, COMPANY_IR, NEWS_RSS, MANUAL_RESEARCH | UNKNOWN | disabled |

Zusätzlich existieren ausdrücklich synthetische lokale Test-Quellen für Acceptance-Fixtures. Ihre Scope-Freigabe ist kein Recht für externe Anbieter. Beat prüft konfigurierte Collector-Verträge täglich; deaktivierte/abgelaufene Sources werden ohne sinnlose Provider-Requests übersprungen. Kein Schätzungsprovider wird aus einem solchen Vertrag erfunden.

## 16. Verifikation

| Befehl / Nachweis | Ergebnis |
| --- | --- |
| Baseline `docker compose exec -T api pytest -q --tb=short` | 61 passed |
| Finale Backend-Regression, derselbe Befehl | 89 passed; eine upstream Starlette-Warnung |
| `docker compose config --quiet`, `docker compose up -d --build` | PASS |
| `docker compose exec -T api alembic upgrade head` | 0009_filing_document |
| `docker compose exec -T api alembic check` | keine neue Schemaabweichung |
| `docker compose exec -T api python -m scripts.verify_fresh_migration` | PASS, 30 erforderliche Tabellen |
| `docker compose exec -T api ruff check .` / `ruff format --check .` | PASS |
| `docker compose exec -T api mypy app` | PASS |
| `docker compose exec -T web npm run lint` / `typecheck` / `build` | PASS, Next.js 16.3.8 |
| `npm.cmd run test:e2e -- --workers=1` mit expliziten Fixture-Variablen | 4 passed, 1,5 Minuten; zwei P4- und zwei P5-Fälle |
| Celery- und MinIO-Smoke | PASS |
| Screener-Pagination, 300 Instrumente | vier SELECTs, 0.233 s |
| Lokales PostgreSQL-/MinIO-Backup und isolierter Restore | PASSED; P5-Raw-Hash und CHF 10'180 bestätigt |

SEC-Tests verwenden ausschließlich gespeicherte synthetische JSON/HTML-Fixtures und MockTransport: Erfolg, ungültige/leere Antwort, 429, 503, Timeout, globales Limit und UNKNOWN/BLOCKED/EXPIRED/DISABLED mit null Requests. Valkey-Ausfall und gesperrte IR/RSS-Quellen sind geprüft. Mathematiktests umfassen passende/mismatched Perioden/Währungen, negative Gewinne, Null-Denominator, FCF, TTM, Bewertung, fehlende Inputs und deterministische Scores. Integrationen prüfen Raw-Bytes, PIT, Restatement, lokale Erstbeobachtung, Watchlist-Isolation, Deduplizierung, Estimates und Screener.

Backup-Satz: `backups/p5-acceptance/sets/20261013T071141Z-39972`. Isolierter Verifier prüfte Benutzer `restore_1bb5bf7d0f40`, Portfolio `8f9e4f5b-09c1-4cee-89f3-bcee3f118852`, Research-Raw `c6858441-7fb9-4173-b6ae-0ae7cf05625b` und Wert `10180`. Testpasswort wurde ausschließlich als Fixture-/Environment-Wert verwendet. Raw- und Backup-Artefakte bleiben Git-ignoriert. Restore-Testvolumes wurden vom isolierten Verifier entfernt.

Workflow wurde um synthetische Fixture-Vorbereitung und Browser-Tests ergänzt. **REMOTE CI NOT VERIFIED FOR THIS CHANGE.** Git-Diffprüfung und Status sind lokale Nachweise, kein Remote-Erfolg.

## 17. P4 und reale Produktion

P4 bleibt FUNCTIONAL — PRODUCTION GATE OPEN. Nicht unabhängig abgenommen: tatsächlicher privater Hostname/VPN, Browservertrauen in die private CA, unabhängiges geschütztes Backup-Ziel, täglich installierter/geprüfter Hostjob und verschlüsselte Wiederherstellbarkeit von Schlüsselmaterial. Der lokale Restore ersetzt diese Zielinstallationsbedingungen nicht. Keine Produktionsquelle wurde aktiviert und kein Produktionsrelease erstellt.

## 18. Known Limitations

Keine abgenommene reale Company-IR-HTML/PDF-Anbindung; explizite strukturierte CSV und manueller Reportingpfad sind der funktionale CH/EU-Weg. SEC unterstützt standardisierte US-GAAP/DEI-Tags, keine universellen Custom-/IFRS-Taxonomies oder beliebige historische Submission-Pages. Für Shares/EV fehlen häufig Pflichtbelege; dann bleiben Bewertungen ausgesetzt. Keine automatische Analystensammlung oder historische Forward-Schätzung, kein installiertes Sentimentmodell. Momentum bleibt ungeprüfter Action Coverage wegen unavailable. Absolute Scores haben feste Grenzen und sind keine Peer-Marktperzentile. Calendar-Day-Staleness und Closing-Balance-Ratios sind dokumentierte erste Definitionen. Alte Research-Lesemodelle zeigen ihren Berechnungszeitpunkt und benötigen nach neuen Marktdaten eine erneute Materialisierung; sie behaupten keine Live-Quote.

## 19. P5-Status und nächste Grenze

**P5 FUNCTIONAL WITH GATED SOURCES:** lokale Research-Funktionalität ist nutzbar und technisch geprüft; fehlende Rechte, Providerformate und Inputs sind sichtbar. **V1.5 NOT PRODUCTION READY** bei offenen P4-Zielgates. P6, Dataset/Feature Store, Backtesting, ML-Training, Forecasting, Risiko und Empfehlungen wurden nicht begonnen.
