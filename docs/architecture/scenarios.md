# Scenario Engine (P8)

Alle Szenarien sind explizite Hypothesen auf einem unveränderlichen, user-owned Risiko-Snapshot. Konfiguration, Resultat, Parent-Hash und Definition-ID werden als unveränderlicher `ScenarioRun` gespeichert. Migration 0014 seedet sieben feste v1-Definitionen mit stabilen UUIDs; Änderungen benötigen neue Versionen.

| Definition | Berechnung |
| --- | --- |
| S&P 500 −10% / −20% | `BETA_BASED_MARKET_SHOCK` |
| NASDAQ −20% | `BETA_BASED_MARKET_SHOCK` |
| Technology −25% | `DIRECT_POSITION_SHOCK`, belegte Klassifizierung Technology |
| USD/CHF −10% / EUR/CHF −10% | `CURRENCY_TRANSLATION_SHOCK` |
| Volatilität ×2 | `RISK_PARAMETER_STRESS` |

Direkter Schock: ausgewählte Positionen × expliziter Schock. Bei Sektorhypothesen bleiben Positionen ohne Klassifizierung unmodelliert. Freie direkte Positions- und FX-Schocks sind über API und UI verfügbar.

FX-Schock: einmalige Übersetzung des gesamten belegten Nettoexposures der Fremdwährung, einschließlich negativer Cashbestände. Ein USD-Wertpapier CHF 1'080 und USD-Cash CHF −900 ergeben beim −10%-Schock CHF −18. CHF-Definitionen werden bei anderer Portfolio-Basis nicht still umgedeutet.

Marktschock: Positionswert × validiertes, zeitlich passendes Beta × Marktschock. Der Benutzer muss den im Snapshot verwendeten Benchmark ausdrücklich als Proxy für den gewählten Markt bestätigen und genau dessen Benchmark-ID angeben. Diese deklarierte Zuordnung ist keine automatische instrumentenübergreifende Übertragung eines beliebigen Betas. Fehlender Benchmark, unzureichende gemeinsame Renditen, konstante Benchmarkserie und unmodellierte Positionen bleiben sichtbar. Modellierte Teile erhalten `modeled_impact_base`; bei partieller Abdeckung bleiben Gesamtwirkung und gesamte gestresste NAV `null`. Eine lineare Beta-Hypothese ist kein kausales Modell; implizite Preisverluste unter −100% werden nicht akzeptiert.

Volatilitätsstress multipliziert ausschließlich eine verfügbare Volatilität. Er erzeugt keinen erfundenen monetären Kursverlust. Resultate nennen Berechnungstyp, Annahmen, Einzelwirkungen, unmodellierte Positionen und Status. Kein Szenario löst einen Handel aus.

APIs: `GET /scenario-definitions`, `POST /portfolios/{id}/scenarios`, `GET /portfolios/{id}/simulation-history`. Nur angemeldete Eigentümer erhalten Portfolioresultate. Definitionen sind gemeinsame hypothetische Regeln und enthalten keine privaten Daten.
