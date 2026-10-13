# Fundamentals (P5)

Stand: 2026-10-13. PostgreSQL hält `fundamental_fact_versions` append-only. Der natürliche fachliche Schlüssel ist Instrument, Metrik, Periodenbeginn, Periodenende und Periodentyp. Jede Beobachtung referenziert Raw-Ingestion, Parser-/Regelversion, Quelle und optional Filing. Ein zusätzlicher veränderlicher Fact-Head ist nicht erforderlich: Die aktuelle Sicht wird aus akzeptierten Versionen abgeleitet. `research_snapshots` und `research_metrics` sind reproduzierbare Lesemodelle, keine Originaldaten.

`known_at` bezeichnet belegte öffentliche Veröffentlichung, `observed_at` und `retrieved_at` den eigenen Eingang. Ohne Veröffentlichungsbeleg wird `known_at` auf den Eingang gesetzt. Die konservative historische Abfrage verlangt **beide** Zeitpunkte ≤ `as_of`; spätes Importieren erzeugt keine frühere lokale Archivhistorie. Restatements ergänzen Versionen mit `replaces_version_id`. Frühere Werte und Rohobjekte bleiben erhalten. Unterschiedliche Quellen mit widersprüchlichen Werten benötigen Review und werden nicht still ersetzt oder gemittelt.

Basiskennzahlen: revenue, gross_profit, operating_income, net_income, eps_basic/diluted, cash, total_assets/liabilities/equity/debt, operating_cash_flow, capex, free_cash_flow, shares_outstanding. Ergänzende explizite Komponenten unterstützen Liquiditäts- und EV-Formeln. Money, Per-share und Shares sind getrennte Einheiten. Berichtswährung wird erhalten; inkompatible Währungen werden nicht verrechnet.

Harte Prüfungen: stabile Instrument-ID, finite darstellbare Decimal-Zahl, passende Einheit/Währung, konsolidierte Werte, geordnete Perioden, Instant versus Duration, nachvollziehbare Veröffentlichung. Annual: 330–400 Tage; Quarter: 60–110 Tage; YTD: 111–329 Tage. Negative Gewinne/Cashflows sind zulässig. Null-Denominatoren sind keine gültigen Ratios. Unbekannte Tags/Perioden bleiben unverfügbar. CSV-Vorschau bewahrt abgelehnte Zeilen mit Raw-Referenz in der vorhandenen Quarantäne.

Manueller Weg: Upload → Raw-Speicherung → Spaltenmapping → Vorschau → ausdrückliche Bestätigung → atomarer Commit → Research-Lesemodell. Nur `MANUAL_RESEARCH` mit gültigem Scope `fundamentals`; der Scope von `MANUAL_CSV` bleibt unverändert. Die neue Source ist standardmäßig UNKNOWN/deaktiviert und benötigt eine dokumentierte Operatorentscheidung.

Formeln (`research-math-v1`):

| Kennzahl | Definition |
| --- | --- |
| Gross/Operating/Net Margin | Entsprechender Gewinn / Umsatz derselben Periode |
| FCF | Operating cash flow minus Capex als positiver Cash-Abfluss |
| ROE / ROA | Net Income / Eigenkapital bzw. Assets am selben Periodenende; Closing-Balance-Definition |
| ROIC | Operating Income × (1 − income_tax / pretax_income) / (debt + equity − cash); nur valide effektive Tax-Rate 0..1 |
| Debt/Equity | Total debt / Equity |
| Net debt | Total debt − Cash |
| Current ratio | Current assets / Current liabilities |
| Quick ratio | (Current assets − Inventory) / Current liabilities |
| YoY | Aktueller / passender positiver Vorjahreswert − 1; nichtpositive Vorjahresbasis bleibt unverfügbar |
| TTM | Vier lückenlose, nicht überlappende, vergleichbare diskrete Quartale; keine YTD-Addition |

Derived-Ausgaben referenzieren Eingabeversionen und Regelversion. Q4 wird nicht aus ungeprüften Zeiträumen errechnet. Für IPOs, Kalenderwechsel und fehlende Perioden ist Unverfügbarkeit ein zulässiger Zustand. Annual-Facts älter als 550 Tage bzw. Quarterly älter als 200 Tage sperren aktuelle Derived-Scores; historische Tabellen bleiben sichtbar.
