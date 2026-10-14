# Portfolio Risk (P8)

## Datenvertrag

`PortfolioRiskService` verwendet den tatsächlichen P4-Ledger und einen reproduzierbaren P4-Bewertungssnapshot. Ein Risiko-Snapshot ist unveränderlich. Er speichert Wissensstichtag, Konfiguration, vollständige Resultate, Transaktionsreferenzen, Kurse/FX/Actions/Coverage, kanonische Inhaltshashes und Raw-Hashes. Spätere Korrekturen erzeugen einen neuen Snapshot. Nachträglich importierte Historie wird ausdrücklich als `EX_POST_LEDGER_CURRENT_KNOWLEDGE_NOT_ORIGINAL_PIT_ARCHIVE` bezeichnet.

Das Datum einer Beobachtung beweist keine damalige lokale Verfügbarkeit: `known_at` und `observed_at` müssen beide am oder vor `as_of` liegen. Neuere ungeklärte/rejected Beobachtungen werden nicht durch ältere akzeptierte Versionen gerettet. Keine Finanzprovider-Anfrage erfolgt während einer Risikoanalyse.

Die tägliche Bewertung verwendet P4-Cash, Positionen, Kosten und explizit angewandte Corporate Actions. Historische Kurse müssen an jedem offenen Börsentag vorliegen. An geschlossenen Börsentagen ist ausschließlich der Schlusskurs der vorherigen tatsächlichen Sitzung zulässig. Der Börsenkalender eines Instruments wird nicht geraten. Action-Coverage wird instrument- und intervallbezogen nach dem P6-Vertrag geprüft. Fehlende Coverage, Kurs- oder FX-Lücken sperren betroffene Kennzahlen.

## Renditen und Kalender

Tägliche Ledger-Rendite mit P4-End-of-Day-Flow-Konvention: `(NAV_heute - externer_Flow_heute) / NAV_gestern - 1`. Ein- und Auszahlungen werden mit FX ihres tatsächlichen Tages neutralisiert, einschließlich Wochenenden und Feiertagen. Gebühren, Steuern, Dividenden und Transaktionen sind interne Portfolioereignisse. Tagesfaktoren werden geometrisch auf die Referenzsitzungen zusammengeführt. So verschieben Feiertags-Flows keine Rendite zwischen Portfolios und Benchmark.

Referenz ist die ausdrücklich konfigurierte Benchmark-Börse, sonst die Börse der ersten stabil sortierten tatsächlichen Portfolio-Instrument-ID. Cash-only verwendet dokumentiert NYSE für USD, SIX für CHF/EUR. Eine Sitzung wird erst nach dem Schluss aller an diesem Tag offenen beteiligten Börsen berücksichtigt. Abtastung: 30/90/252 Referenzrenditen plus Eröffnungswert; maximal `window*3` Kalendertage ab erster Ledger-Buchung. Die Kalenderversion wird gespeichert.

Instrument-/Benchmark-Renditen verwenden die P6-Kette aus Raw-Close, expliziten Splits/Dividenden mit Wiederanlage und einmaliger Basis-FX-Umrechnung. Adjusted Close wird nicht zusätzlich verwendet. Die tatsächliche Portfoliorendite folgt dem Ledger und unterstellt keine Dividenden-Wiederanlage. Der Drawdown bezieht sich auf beobachtete EOD-Referenzwerte, nicht auf unbeobachtete Intraday-Tiefs.

## Kennzahlen und harte Gates

| Kennzahl | Definition | Mindestumfang |
| --- | --- | --- |
| Volatilität | Stichprobenstandardabweichung, ddof=1; annualisiert mit √252 | 20 vollständig validierte Renditen |
| Beta | Stichprobenkovarianz Portfolio/Benchmark geteilt durch Benchmark-Stichprobenvarianz | 60 identische, validierte Referenzperioden; Benchmarkvarianz > 0 |
| Maximum Drawdown | Minimum `wealth_index / bisheriger_Peak - 1`; Peak-/Tiefdatum, anfänglicher Baseline-Peak | vollständige analysierte Renditekette |
| VaR 95% | Negativer 5%-Quantilwert; Type-7-Interpolation `p*(n-1)` | 252 Renditen |
| CVaR 95% | Negativer Mittelwert aller tatsächlichen Returns ≤ VaR-Quantil | zusätzlich mindestens 10 Tail-Beobachtungen |
| Korrelation | Stichproben-Pearson auf identischen Referenzperioden | exakt 30/90/252 Beobachtungen; beide Varianzen > 0 |

Vorzeichen VaR/CVaR: positiver Verlust, negativer historischer Gewinn. VaR ist kein maximal möglicher Verlust. Jede Matrixzelle zeigt ihre eigene Stichprobengröße. Lücken werden nicht durch ältere Beobachtungen außerhalb des Fensters aufgefüllt. Vollständig belegte konstante Cash-Bestände dürfen mathematisch null Volatilität haben; fehlende Daten ergeben `null`.

## Exposure und Health

Instrumentpositionen werden über Accounts zusammengeführt. Largest/Top-3/Top-5/HHI beziehen sich auf vollständige positive Portfolio-NAV; Cash ist im Nenner, aber nicht in den Instrumentquadraten enthalten. Sektor, Industrie, Land und Handelswährung bleiben bei fehlender Klassifizierung `UNKNOWN`. Klassifizierungen sind ausdrücklich lokal erfasste Metadaten mit eigenem Beobachtungszeitpunkt.

Netto-FX-Exposure umfasst Wertpapiere sowie positive und negative Cashbestände. Der P4-FX-Beitrag übersetzt die vorherigen nativen Schlussbestände zu den heutigen FX-Raten (`OPENING_EXPOSURE_DAILY_FX_TRANSLATION`). Wirtschaftliche Umsatzwährungen bleiben ohne Nachweise unverfügbar.

Health-Rubrik v1, alle Werte auf 0–100 begrenzt:

- Diversification: `100*(1-HHI)`.
- Concentration: `100*(1-largest_weight)`.
- Volatility: `100*(1-annualized_volatility/.5)`.
- Quality: Wertpapiergewichteter P5-Quality-Score; alle Positionen erforderlich, Snapshotalter maximal sieben Tage, Stichtag und Erstellung ≤ `as_of`.
- Currency Risk: `100*(1-sum(abs(foreign_net_weights)))`; klar gekennzeichneter Accounting-Translation-Konzentrationsindikator, keine wirtschaftliche FX-Volatilität.
- Liquidity: Wertpapiergewichtetes `100*(1-position_quantity/average_20_session_volume/.1)`. Exakt 20 geschlossene, belegte Sitzungen mit positivem Volumen, Action-Coverage und unveränderter Share Unit erforderlich. Ein Split im Fenster sperrt den Proxy. Volumen-Proxy ohne Spread-/Ausführungsgarantie.

Jeder Teilscore enthält Status, Eingaben, Gewichte, Version, Qualität und fehlende Inputs. Fehlende Inputs werden nicht durch Umgewichtung ersetzt. Ein Gesamtscore wird bewusst nicht ausgegeben. Hohe Teilscores ändern keine Daten-Gates.

## API und Ressourcen

Geschützt und user-owned: `POST /portfolios/{id}/risk`, `GET /portfolios/{id}/risk`, `/risk/history`, `/risk/{snapshot_id}`, `/correlations`, `/exposures`. GET liest gespeicherte Resultate; POST erzeugt den Datenstand. Ohne Snapshot: `RISK_UNAVAILABLE`.

Maximal 30 Instrumente einschließlich Benchmark, Fenster ≤252, ein globaler Risiko-Rechenlauf per PostgreSQL-Advisory-Lock, konfigurierbares Timeout standardmäßig 120 Sekunden. Timeout erzeugt keinen scheinbar vollständigen Snapshot. Historien liefern maximal 100 kleine Zusammenfassungen pro Seite (`offset`); Detailresultate werden einzeln geladen. P8 benötigt weder MLflow noch ML-Worker, Produktionsmodell oder LLM.
