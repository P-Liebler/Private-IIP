# Feature Store

P6. `FeatureSnapshotService` ist die gemeinsame Engine für API, Dataset Builder und spätere P7-Lader. Jeder Snapshot pinnt Cutoff, Feature-Regelversion, Kalender, Availability-Modus, Inputversionen, Reviews und Coverage. Features tragen value als Decimal-String oder null, missing_flag, quality, reason und Input-IDs. Kein Forward-Fill fehlender Handelssessions und keine Nullfüllung.

## Technische Formeln

Basis: validierte rohe Schlusskurse plus explizite validierte Actions. Total-Return-Index wird mit dem ersten rohen Schlusskurs initialisiert; täglicher Faktor `(close_t * split_ratio + dividend_per_original_share) / close_previous`. Dividenden werden für diesen Index am Ex-Date reinvestiert. Adjusted close wird nicht verwendet. Mehrdeutige gleichzeitige Action-Entitlements bleiben unavailable.

| Feature | Formel / Mindesthistorie |
| --- | --- |
| return_1/5/20/60/120/252d | Index-Ende / Index vor N Sessions − 1; N+1 vollständige Sessions |
| momentum_20/60/120d | Entsprechende Total-Return-Rendite |
| SMA20/50/200 | Mittel der letzten N Indexstände; N Sessions |
| distance_SMA50/200 | Index-Ende / SMA − 1 |
| RSI14 | Wilder: initial 14 mittlere positive/negative Änderungen, anschließend `(13*previous + current)/14`; 15 Sessions; unveränderter vollständiger Index ergibt definiert 50 |
| MACD12/26 | EMA12 − EMA26; SMA-Initialisierung, alpha=2/(N+1); 26 Sessions |
| ATR14 | Wilder-Glättung von max(high−low, abs(high−previous_close), abs(low−previous_close)); 15 OHLC-Sessions, konsistente Splitbasis; bei Dividenden ohne OHLC-Anpassungsvertrag ausgesetzt |
| volatility_20/60/252 | Sample-Standardabweichung der N arithmetischen Renditen × sqrt(252); N+1 Sessions |
| max_drawdown | Minimum(Index / bisheriges Maximum − 1) über die gepinnte Historie; mindestens 2 Sessions |
| volume_change | Volume_t / Volume_previous − 1; positive Vorjahressession; 2 Beobachtungen |
| volume_zscore | (aktuelles Volume − Mean20) / Sample-Std20; 20 vollständige Volumes, nicht konstante Reihe |
| relative_strength | 20-Session-Rendite Instrument minus Benchmark; identische Sessions/Währung, geprüfte Actions |

Volume-Features sind bei Splits ohne geklärte Volumenbasis ausgesetzt. SMA/RSI/MACD beziehen sich auf den Total-Return-Index, nicht auf einen behaupteten handelbaren adjustierten Kurs. Fenster enthalten maximal 253 Sessions; Lücken setzen das betroffene technische Ergebnis aus.

## Research und weitere Inputs

P5-Fundamental-/Valuation-Mathematik wird wiederverwendet: Wachstum, Margins, ROE/ROIC, Verschuldung, FCF und Bewertung samt Inputbezügen. Kein heute materialisierter Research-Score wird rückwirkend geladen. Quality/Value ist das gleichgewichtete Mittel vollständiger historischer P5-Quality-/Value-Rubriken. Konflikte und Staleness suspendieren Ergebnisse.

Estimate-Revisions benötigen tatsächliche vergleichbare Snapshots beider Zeitpunkte, gleiche Zielperiode, Einheit und Währung; 30/90 Kalendertage sind hier ausdrücklich Revisionsfenster, keine Target-Horizonte. Erste spätere Schätzung ist kein früherer Vergleichswert. News-Mappings bekommen ab P6 eigene Beobachtungszeiten; alte und nachträglich zugeordnete Mappings werden nicht zurückdatiert. News-Volume zählt nur verifizierte archivierte Beobachtungen der letzten sieben Kalendertage. Ohne Coverage ist ein Nullcount unbekannt. Sentiment und Earnings Surprise bleiben ohne verifizierte Modell-/Estimate-Kontexte unavailable.

Typisierte Macro-CSV-Vintages verwenden einen gesonderten `macro`-Scope auf MANUAL_PIT und einen Review. Einheiten: Raten/Inflation/Spreads PERCENT, VIX INDEX, Öl USD_PER_BARREL, FX RATE. Die erste konservative Freshness-Policy setzt Beobachtungen älter als 31 Kalendertage aus. Fehlende relative Sektor-/Historiengruppen oder Forward-Estimates bleiben unavailable. Kein Provider wird aktiviert.
