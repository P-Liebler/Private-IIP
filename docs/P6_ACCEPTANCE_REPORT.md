# P6-Abnahmebericht

Stand: 2026-10-14. **FUNCTIONAL WITH HISTORICAL DATA LIMITATIONS.** Normative Grundlage: Masterplan 75–95, 141–142, 153–158, 204 und 208. P7 wurde nicht begonnen.

## 1. Baseline

Branch main, Start-Commit `a59f94cbd3e8c5038440101088bfe06bf68c309d`, zunächst sauberer Arbeitsbaum. Remote main wurde read-only auf denselben Commit geprüft. Baseline 89 Backend-Tests; bestehende vier Browserfälle bleiben erhalten. Änderungen sind lokal, ohne Push, Release oder neuen Commit.

## 2. CI-Fix

GitHub-Run [38389788455](https://github.com/P-Liebler/Private-IIP/actions/runs/38389788455), Job 115270450753: Backend/Frontend erfolgreich; npm ci scheitert tatsächlich mit EACCES beim Host-Verzeichnis `frontend/web/node_modules/@alloc`. Compose bindet `/app`, während Docker den verschachtelten node_modules-Mountpoint als root erstellt. Linux-Reproduktion: Runner-UID kann den root-eigenen Unterordner nicht beschreiben; ein Runner-eigener isolierter Ordner funktioniert.

Workflow installiert package.json/Lock, Playwright-Konfiguration und E2E-Dateien in `mktemp -d "$RUNNER_TEMP/iip-browser.XXXXXX"`. Container- und Runner-Dependencies sind getrennt; keine globalen Rechteänderungen. Isoliertes npm ci und sechs Browserfälle wurden lokal geprüft. **REMOTE CI NOT VERIFIED:** der alte Run bleibt fehlgeschlagen; kein neuer Remote-Lauf wurde ausgelöst.

## 3. P5-Hardening

Research identity v2 entfernt ausschließlich beiläufige Live-as_of-Felder aus der Identität. Verwendete Fact-/Price-/Provenienzversionen, Regeln, Perioden und semantische Ergebnisse bleiben enthalten; Staleness/Eligibility erzeugt neue Ergebnisse. Explizite historische Cutoffs bleiben exakt gepinnt. Alte Snapshots werden nicht geändert. Live-Doppelrefresh verwendet im Integrationstest dieselbe ID; Änderungen an Fact/Price/Regel/Eligibility und historischen Cutoffs ändern im Referenztest die Identität.

Reviews unterscheiden VERIFIED_PUBLIC_TIMESTAMP, VERIFIED_SOURCE_DOCUMENT, LOCAL_FIRST_OBSERVATION, USER_ASSERTED und UNVERIFIED. Ein Belegtext ist keine verifizierte Veröffentlichung. Review-Zeitpunkt gilt selbst als Informationsgrenze. Bestehende unbekannte Belege bleiben unbekannt.

## 4. Migrationen

Neue Heads 0010_pit_backtesting, 0011_pit_contracts, 0012_pit_immutability. Elf neue Tabellen: availability_reviews, action_coverage_reviews, universe_definitions, universe_membership_versions, feature_snapshots, dataset_versions, backtest_runs, macro_observation_versions, news_mapping_versions, walk_forward_splits, pit_jobs. Aktueller Head **0012_pit_immutability**; frische Migration über alle 41 erforderlichen Tabellen und bestehendes Schema geprüft. Alembic check ohne Drift. Update-Trigger schützen neun P6-Versionstabellen. Vorhandene 0001–0009 wurden nicht umgeschrieben.

## 5. Universes

Private Ownership, stabile Instrument-IDs, öffentliche und lokale Zeitgrenzen, effektive Intervalle, Eintritt/Austritt, Delisting und append-only Korrekturen. Removal/Delisting überschreibt ältere offene Membership ab seiner effektiven Grenze; spätere neue Listung kann wieder eintreten. Mehrdeutige Überlappungen werden ausgeschlossen. Keine Auswahl aus dem heutigen active-Verzeichnis. Strenge Vollständigkeit braucht einen dokumentierten Zeitraumbeleg einschließlich delisteter Titel. CSV: Upload → Raw → validiertes UUID-Mapping → Preview → Commit; eigener Source-Scope.

## 6. Kalender

Offline exchange-calendars 4.13.2, NYSE/XNYS, NASDAQ/XNAS als dokumentierter XNYS-Alias und SIX/XSWX. UTC, Feiertage, DST, Early Close und bekannte Sonderausfälle. Referenztests prüfen unter anderem 2012 Sandy, Independence Day und Thanksgiving. 30/90 sind Instrument-Handelssessions. Keine erfundenen Feiertagslisten.

## 7. Features

Zentraler versionierter Store: sechs Returns, drei Momentum-Horizonte, Wilder RSI, SMA-seeded EMA/MACD, SMA20/50/200 und Distanzen, ATR mit OHLC-Gates, drei Volatilitäten, Drawdown, Volume-Change/Z-Score und Relative Strength. Formeln, Mindesthistorien und Action-/Lückenregeln stehen im [Feature-Vertrag](architecture/feature-store.md). P5-Math für Fundamentals, Valuation, Quality/Value wird wiederverwendet; Net Debt/EBITDA ergänzt. Historische Estimate-Revisions, zeitversionierte News-Mappings und typisierte Macro-Vintages haben ihre eigenen Gates. Ohne valide Kontexte/Modelle bleiben Forward-, Surprise-, Sentiment- und relative Peer-Features ausgesetzt.

## 8. Dataset Builder

Configuration, Code-/Dependency-Manifest, alle benötigten Raw-/Canonical-/Review-/Membership-/Calendar-/Feature-/Target-Versionen, Einzel-Content-Hashes, Rows und Quality werden unveränderlich gehasht. Identische Inputs sind idempotent. Rebuild liest gepinnte Artefakte, prüft deren Inhalte und Raw-Bytes und meldet fehlende/geänderte Versionen ausdrücklich. Keine Neuauswahl aktueller Daten. Frühere lokale Entwicklungsartefakte ohne Content-Belege werden abgewiesen. Replay gespeicherter Artefakte ist von einer Neu-Parsierung mit alter Software unterschieden.

## 9. Targets

30-/90-Session Benchmark-Outperformance, Excess Return und realisierte Volatilität. Entry t+1 Open, Ende t+30/t+90, genau N Sessions. Label 1 bei positivem Excess, sonst 0. Vollständige passende Benchmark-/Action-/FX-Reihen erforderlich. Separate signal_as_of, label_start/end/available_at und Inputversionen. Keine Targets in Feature-Inputs. Unverfügbarer Benchmark oder unvollständige Reihen erzeugen TARGET_UNAVAILABLE.

## 10. Walk Forward

Geordnete Train/Validation/Test-Fenster, tatsächliche Labelintervalle, Purging und mindestens N Sessions Embargo vor Validation und finalem Test. Grenzen sind kalenderbezogen überprüfbar. Split-Ergebnisse und train-only Prävalenz/Mittelwert werden versioniert gespeichert. Kein Shuffle oder Modelltraining.

## 11. Backtest Engine

Pure Offline-Engine mit Long-only-Cash/Positionen, BUY/SELL-Rebalances, Decimal-Mengen, Frequenz, Top-N und Positionslimit. Orders/Fills/Signals/Equity und Warnings sind gespeichert. Splits ändern Positionen/Orders einmal; Dividenden erzeugen Forderung am Ex-Date und Cash erst am Payment Date. Keine erfundene Delisting-Liquidation. Verkäufe dürfen durch Gebühren kein Margin-Cash erzeugen.

## 12. Execution Timing

Default NEXT_OPEN, optional NEXT_CLOSE. Signal/Information-Cutoff/Tradable-Time/Preistyp/Füllzeit sind explizit. Derselbe zur Entscheidung verwendete Close ist kein zulässiger Fill. Decision-Quantity verwendet keinen späteren Open. Fill-FX wird separat zum Ausführungszeitpunkt geprüft. Exchange-Mischung wartet auf den spätesten verwendeten Informationscutoff. Strenge Actions werden in der am jeweiligen Tag bekannten Version verarbeitet, nicht mit heutigen Korrekturen rückwirkend gebucht.

## 13. Kosten

Commission in Basiswährung, halber vollständiger Spread und einseitige Slippage in bps; Kosten im Cash und separat nachvollziehbar. Nullkosten nur ausdrücklich markierte Vergleichskonfiguration. FX ist die gepinnte tägliche P3-Referenz mit Datum/Richtung/Carry, keine behauptete Intraday-Spotquote.

## 14. Baselines

Constant 0.5 und train-only Class Prevalence; Zero Excess Return und train-only Historical Mean. Investierbare Baselines: Benchmark-only, Equal Weight, 120-Session Momentum, vollständige historische Quality/Value-Rubrik. Gleicher Kalender-/Availability-/Kosten-/Execution-Vertrag. Fehlgeschlagener passiver Benchmark wird nicht als gültiges 0%-Cash-Benchmark-Ergebnis angezeigt.

## 15. Metrics

Total Return, CAGR, Sample-Volatility, Sharpe/Sortino, Maximum Drawdown, Alpha/Beta, positive Equity-Session-Rate, einseitiger Notional-Turnover, Kosten, Trade-Anzahl, Coverage und Missing Observations. Sharpe/Sortino/Alpha ohne explizite Risk-Free-Rate unavailable; Ratio-Mindeststichprobe 20 Returns. Kein misleading Ergebnis aus zwei Tagen oder unbekannter Bewertung. No-Fill-Runs erhalten keine erfundene investierte Rendite.

## 16. APIs und UI

Geschützte Universe-/Membership-/Import-, Dataset-/Quality-/Rebuild-/Split-, Feature-/History-, Backtest-/Trades-/Metrics- und Job-Endpunkte. `/backtests` baut echte Datasets/Runs und zeigt Kurven, Status, Kosten, Fills und Provenienz. `/data-quality` zeigt Coverage, Missingness, Membership-/Action-Probleme und Survivorship Risk. Synthetische Simulationen und rekonstruierte Historie sind ausdrücklich markiert. Kein Forecast-Produkt.

## 17. Golden Tests und lokale Verifikation

- **113 Backend-Tests bestanden**, einschließlich aller bisherigen P0–P5-Fälle. Ein bestehender Upstream-Starlette/httpx-Deprecation-Hinweis bleibt.
- **6 Browser-Tests bestanden**: vier bestehende P4/P5-Fälle und zwei P6-Flows. Positiver synthetischer Strict-PIT-Run; ungeprüfte historische Membership wird abgewiesen.
- Ruff, Format-Check, Mypy über 103 App-Quelldateien, Frontend lint/typecheck/build, Compose und Alembic geprüft. Celery-Smoke und MinIO-Roundtrip erfolgreich.
- Unabhängiges Golden: Kapital 1000, Open 100, Commission 1, Spread/Slippage explizit 0 → 9.99 Shares, Cash 0, Endwert **1098.90**, Return **0.0989**, Kosten 1, Drawdown −0.001, Turnover 0.999. Vier Baselines reproduzieren den Wert.
- Unabhängige 30-/90-Target-Reihe: eine +10%-Session unter N Returns, Volatilität `.1/sqrt(N)*sqrt(252)`, Excess 0.1, korrektes Label-Ende und spätere Review-Availability.
- Indikatorreferenzen, Missing Sessions, Split/Dividende, fehlender Open/FX, Same-Close-Ablehnung, Purge/Embargo, Dataset-Replay, fehlende gepinnte Version, DB-Immutability, Ownership, Source Gate und sichere Universe-Exit-/Fee-Regeln geprüft.

## 18. Missing Data

Null plus Grund, kein Zero-/Forward-Fill. Unverifizierte Membership/Verfügbarkeit und ungeprüfte Action Coverage werden ausgeschlossen. Missing FX/Open erzeugt NO_FILL; fehlende Bewertung bleibt null. Sentiment ohne verifiziertes Modell bleibt unavailable. Die kurze lokale Vier-Session-Fixture erzeugt absichtlich keine vollständigen 30-/90-Session-Labels oder Sharpe-Schätzungen.

## 19. P4

**FUNCTIONAL — PRODUCTION GATE OPEN.** Reale Homelab-/VPN-Hostname-Prüfung, Client-CA-Vertrauen, unabhängig geschützter Backup-Mount, installierter/getesteter täglicher Hostjob und verschlüsselte Schlüssel-Recovery bleiben offen. Kein lokaler P6-Test ersetzt diese Zielinstallationsbedingungen.

## 20. P5 und Quellen

**FUNCTIONAL WITH GATED SOURCES.** Yahoo BLOCKED; SEC/IR/RSS entsprechend bestehender Entscheidung deaktiviert/UNKNOWN. Neue MANUAL_PIT-Scopes werden nicht still aktiviert. Keine Live-Finanzprovider-Abfrage in Tests. P3-Returns bleiben provisional; P5-Momentum wird nicht pauschal freigegeben. Keine reale vollständige historische US-/CH-Universe- oder Corporate-Action-Historie wurde erfunden.

## 21. CI und Betriebsprüfung

Lokale Linux-Berechtigungsreproduktion, isolierter Runner und vollständige sechs E2E-Fälle geprüft. Workflow behält Compose, Migrations-, Backend-/Frontend-Gates und Cleanup. Backend- und Browser-Dataset-Builds auf derselben lokalen Instanz werden nacheinander geprüft, da sie dasselbe konservative Run-Limit verwenden. **REMOTE CI NOT VERIFIED**, kein Push.

Backup und **isolierter Restore bestanden am 2026-10-14**. Set `backups/p6-acceptance/sets/20261014T054851Z-34852`: PostgreSQL-Dump und originale MinIO-Bytes mit Prüfsummen. Wiederherstellung in einer neuen temporären Compose-Instanz prüfte Head 0012_pit_immutability, P6-Raw-Hash, Login, exakt **CHF 10'180** Portfolio-Wert und den gepinnten Dataset-Replay. Dataset `a4c9d4ff-07de-44d0-a89b-53e843648994`, Hash `dd5cd6ef97b9248eb148725797470069b9b33635df15f8506d61bf99761ea538` blieb erhalten. Temporäre Restore-Volumes wurden durch das bestehende begrenzte Cleanup entfernt. Backups/Testartefakte bleiben ignoriert und lokal; die getrennte echte Produktionssicherung ist damit nicht freigegeben.

## 22. Known Limitations

Keine nachgewiesene reale vollständige historische Datenabdeckung. Review-Kriterien sind Operator-Nachweise mit Originalreferenzen; ein bloßer Text wird nicht automatisch verifiziert. Keine installierten Sentimentmodelle, universellen historischen Estimates oder Peer-Gruppen. Forward/Sentiment/Surprise-Felder bleiben bei fehlenden Kontrakten unavailable. ATR mit Dividenden und Volumen mit ungeklärter Splitbasis sind konservativ ausgesetzt. Cross-Exchange-Lücken werden nicht künstlich aufgefüllt. FX/Kosten sind ein einfaches tägliches Referenzmodell, kein historisches Orderbuch-/Market-Impact-Modell. Builds sind begrenzt synchron; Progress ist Start/Ende und kein minutenweises Celery-Dashboard. Code-/Dependency-Pinning beweist einen reproduzierbaren Artefakt-Replay, keine frei verfügbare ältere Softwareausführung.

## 23. P6-Status

**FUNCTIONAL WITH HISTORICAL DATA LIMITATIONS.** Die normative technische Basis und ihre Golden-/Leakage-/Execution-Gates sind lokal nachgewiesen. Eine vollständige reale strenge ML-Dataset-Abnahme wird mangels belegter Historie nicht behauptet. P6-Datenbeschränkungen bleiben sichtbar.

## 24. Nächste Grenze

P7 erst auf eigenen Auftrag: Modelle, OOS-Vergleich, zeitbewusste Kalibrierung, Registry, immutable Predictions/Outcomes und Forecast UI. P6 startet diese Infrastruktur nicht.
