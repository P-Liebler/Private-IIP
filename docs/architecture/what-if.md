# What-if Simulator (P8)

Eine Hypothese enthält 1–20 ausdrücklich vom Benutzer ausgewählte Käufe/Verkäufe. Kauf: positiver Betrag in Portfolio-Basiswährung. Verkauf: Anteil >0 bis 1 der vorhandenen Stückzahl. Kein Short-Selling und kein impliziter Kredit. Neue Instrumente benötigen eine bekannte, aktive, unterstützte Identität sowie einen validierten Snapshot-Kurs und FX. Fehlende Kurse oder FX erzeugen einen Fehler, keinen Nullwert.

Das reine Rechenmodul kopiert Positionen und Cash aus dem eingefrorenen Datenstand. Es schreibt keine Ledger-Transaktionen. Hypothetische Shares ergeben sich aus Kaufbetrag / (Kurs × Basis-FX). Geld wird dem ersten stabil sortierten vorhandenen Cash-Account der ausdrücklich gewählten Währung entnommen bzw. gutgeschrieben; standardmäßig Basiswährung. Die hypothetische Cross-Currency-Zahlung ist eine deklarierte Referenz-FX-Konversion, kein behaupteter Broker-Spotkurs. Mehrere Trades werden in angegebener Reihenfolge berechnet.

Kosten: Basis-Kommission + Bruttowert × (Spread-bps + Slippage-bps)/10'000. Defaults: 1 Basiswährungseinheit, 5 bps Spread, 5 bps Slippage. Alle Parameter sind sichtbar und begrenzt. Nullkosten benötigen einen expliziten Vergleichsvertrag. Die Kosten reduzieren Cash und NAV. Buchungen im realen P4-Ledger verwenden weiterhin ihre bestehende Posting-Präzision; hypothetische Mengen bleiben Decimal und werden nicht als Brokerabrechnung ausgegeben.

Vergleich:

- tatsächliche historische Portfolio-Risiken und vorgeschlagene Allocation;
- Exposure, Konzentration, Health, Korrelationen und sieben Szenariohypothesen;
- hypothetische historische Volatilität, Beta, Drawdown, VaR/CVaR anhand konstanter vorgeschlagener Gewichte auf den gepinnten Instrument-/Cash-FX-Renditen.

Die zweite Renditekette ist ausdrücklich **pro forma** mit unterstellter Wiedergewichtung, keine tatsächlich erzielte Performance und kein neu ausgeführter P6-Strategiebacktest. Fehlende Historie einer bestehenden oder neuen Position bzw. Fremdwährungs-Cash sperrt die hypothetischen historischen Kennzahlen. Aktuelle Allocation und Kosten können trotzdem verfügbar sein. Quality wird mit denselben gepinnten P5-Scores neu gewichtet; fehlende neue Score-/Liquiditätsinputs bleiben unverfügbar. Marktszenarien verlangen die gleichen expliziten Proxy-Zuordnungen wie eigenständige Szenarioläufe (`scenario_benchmark_mappings` mit SP500/NASDAQ und der passenden Snapshot-Benchmark-ID).

`POST /portfolios/{id}/what-if` speichert einen unveränderlichen WhatIfRun mit Risiko-Parent, Konfiguration, tatsächlichen Eingabeversionen und Inhaltshash. `/simulation-history` liest maximal 100 Zusammenfassungen eigener Szenarien und Hypothesen pro Seite (`offset`). Einzelresultate sind über `/scenarios/{run_id}` und `/what-if/{run_id}` abrufbar. Maximal 30 Instrumente, ein globaler What-if-Lock und 120 Sekunden Timeout. Kein MLflow-/LLM-Zwang, keine automatischen Portfolioempfehlungen.
