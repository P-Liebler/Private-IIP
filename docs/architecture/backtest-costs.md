# Backtest Costs

P6, cost-model-v1. Konfiguration: feste Commission je virtuellem Fill in Basiswährung, vollständiger Spread in Basispunkten, einseitige Slippage in Basispunkten. Kaufpreis = Raw Price × (1 + spread_bps/20000 + slippage_bps/10000); Verkauf mit negativem Vorzeichen. Native Preise werden über die gepinnte P3-FX-Richtung in die Basiswährung übersetzt. Implizite Kosten = Menge × Raw Price × FX × Aufschlag; zusätzlich Commission.

Defaults 1 Commission, 5 Spread-bps, 5 Slippage-bps. Nullkosten benötigen `zero_cost_comparison=true` und bleiben sichtbar. Keine unbekannte Risk-Free-Rate als null. FX trägt Source, Version, Rate Date, Richtung und begrenzten Carry. Missing FX verhindert Fill beziehungsweise Bewertung.

Dies ist ein transparenter einfacher Kostenvertrag, kein Market-Impact-/Liquiditätsmodell. Nicht modelliert sind Steuern, Borrow, Shorting, Margin und komplexe Derivate. Alle vier Portfolio-Baselines verwenden dieselbe Konfiguration. Referenz-Golden: 1000 Cash, Open 100, Commission 1, Spread/Slippage explizit 0, daher 9.99 Shares; End-Close 110 ergibt 1098.90, Kosten 1 und Turnover 0.999.
