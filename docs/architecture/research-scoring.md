# Research-Scoring (P5)

`absolute-rubric-v1` ist eine feste deterministische Rubrik, kein Marktperzentil, kein ML-Modell und keine Empfehlung. Skala 0..100. Jeder Input wird linear zwischen dokumentierten Grenzen auf 0..1 begrenzt, anschließend mit Gewicht × 100 verrechnet. Grenzen beschreiben die gewählte Research-Rubrik, keine allgemeingültige Investmentregel.

| Score | Inputs mit Gewicht | Grenzen für 0 → 100 Prozent des Beitrags |
| --- | --- | --- |
| Quality | ROIC 40 %, FCF Margin 30 %, Debt/Equity 30 % | 0→0,20; 0→0,25; 3→0 |
| Growth | Revenue YoY 40 %, EPS YoY 30 %, FCF YoY 30 % | jeweils −0,10→0,20 |
| Value | Earnings Yield 50 %, FCF Yield 50 % | jeweils 0→0,10 |
| Momentum | 252-Tage-Komponente 100 % | −0,20→0,30; derzeit ausgesetzt wegen UNVERIFIED Action Coverage |
| Stability | Margin Stability 100 % | vier vergleichbare Jahres-Netto-Margen: max(0, 1 − Population-Standardabweichung / 0,10) |

Alle definierten Inputs sind Pflicht. Fehlende/stale/ungültige Inputs erzeugen `score=null`, `INSUFFICIENT_DATA`, Coverage, Drivers und Missing-Inputs; es gibt keine Umgewichtung oder neutralen Fantasiewert. Drivers enthalten Input, Gewicht, Beitrag und Versionen. Harte Daten-Gates gehen vor Qualität und Score.

Momentum verwendet keine heimliche Adjusted-Close-Reihe. Solange Action-Abdeckung nicht verifiziert ist, bleibt der Score ausgesetzt. Relative Branchen-/Sektorperzentile werden nicht aus dem kleinen privaten Bestand erfunden. Absolute Rubrik und fehlende Vergleichsgruppe sind sichtbar. Research-Snapshots speichern Regelversion, Stichtag und vollständiges Ergebnis mit Fakt-/Preisversionen; spätere Regeln überschreiben alte Ergebnisse nicht.

Screener liest die materialisierten Snapshots mit einer DB-Window-Auswahl je Instrument, indizierten numerischen Kennzahlen, Datenbankfiltern und Pagination (höchstens 100). Er berechnet beim Suchrequest keine Facts neu und erzeugt kein N+1 pro Resultat. Unverfügbare Kennzahlen werden von numerischen Filtern ausgeschlossen. Der Berechnungszeitpunkt bleibt sichtbar.
