# Strategieevaluation

Status: **V3 RECOMMENDATIONS GATED · BLOCKED_BY_REAL_DATA**.

Der PR2-Auftrag bindet eigenes Portfolio und P6-Dataset. Nicht reale oder nicht belegte Herkunft erzeugt einen unveränderlichen blockierten Bericht mit `metrics: null`; keine simulierte positive Empfehlung. Zulässige Ausführung verwendet die vorhandene P9-Replay- und P6-Ausführungslogik.

`RESEARCH_BACKTEST` bezeichnet Forschung. `ARCHIVED_FORWARD_EVALUATION` verlangt tatsächlich archivierte historische Profile, Rules, Prognosen und Risiko-/Portfoliozustände. Heutiges Ranking wird nicht in die Vergangenheit eingesetzt. Modell- und Strategieverfügbarkeit, Signalzeit, nächste handelbare Session, Gebühren, FX und Corporate Actions bleiben gepinnt.

Baselines: No Change, Benchmark, Equal Weight, Momentum und Quality/Value. Vorhandene P9-Ergebnisse liefern Recommendation-/Abstention-Frequenz, Turnover, Kosten, Nettoertrag, Drawdown, Konzentration und risikobezogene Kennzahlen soweit Daten vorhanden sind. Kein belastbarer Alpha-Nachweis liegt vor.

Freigabe verlangt validierte Produktionsprognosen, unabhängige Strategieevidenz, vollständige erforderliche Daten, bestandene Risiko-/Portfoliolimits und explizites bestehendes Operator-Review. PR2 aktiviert keine Strategie und führt keine Broker-Orders aus.
