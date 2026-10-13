# Bewertung (P5)

Deterministische Decimal-Engine `research-math-v1`. Stichtag verwendet nur eigene validierte Fact- und Preisversionen, die am Wissenszeitpunkt verfügbar waren. Keine externe Live-Abfrage aus der UI. Preis älter als sieben Tage oder Annual-Facts älter als 550 Tage sperren Bewertungen.

| Kennzahl | Formel / benötigte Eingaben |
| --- | --- |
| Market cap | Raw Close × Shares Outstanding; belegte Aktiengattung und exakt kompatibler Split-Stand erforderlich |
| P/E | Market cap / positiver Annual Net Income; negativer Gewinn gibt kein Standard-P/E |
| P/S | Market cap / positiver Annual Revenue |
| P/B | Market cap / positives Closing Equity |
| Enterprise value | Market cap + Total Debt − Cash + Preferred Equity + Minority Interest |
| EV/EBITDA, EV/Revenue, EV/FCF | EV / entsprechenden positiven Annual-Wert |
| FCF Yield / Earnings Yield | Annual FCF bzw. Net Income / Market cap; negative Yields bleiben als solche sichtbar |
| Forward P/E / PEG | benötigen zuverlässige freigegebene Schätzungen samt Perioden-/Per-share-/Split-Vertrag; ohne diesen DATA_UNAVAILABLE |

Fehlende Schulden, Preferred Equity oder Minority Interest werden nicht als null behandelt. Ein ausdrücklich dokumentierter Nullwert ist zulässig. Alle EV-Komponenten brauchen dieselbe Währung und Bilanzperiode. Währungsinkompatibilität bleibt unverfügbar; P5 erfindet keine zusätzlichen FX-Historien. Der erste Vertrag verwendet `share_class=instrument UUID` und einen ausdrücklich belegten `split_basis_date`, der zum Preisdatum passen muss. SEC-Company-Aggregate erhalten diese Belege nicht automatisch. Jede Ausgabe referenziert Eingabefacts, Preisversion, Datenzeitpunkte und Regelversion.

Analystensnapshots sind technisch nutzbar; historische Forward-Valuation aus einem aktuellen Snapshot wird nicht behauptet. Keine LLM-Schätzung wird als Finanzzahl verwendet.
