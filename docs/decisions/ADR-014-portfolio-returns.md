# ADR-014: Portfolio return definitions

**Status:** Accepted for P4, 2026-10-12.

V1 reports absolute return excluding net external flows, daily-linked TWR with end-of-day flow convention, bounded XIRR, CAGR from linked TWR and opening-exposure FX translation. Every return requires complete dated valuations and P3 FX. Missing market/FX data produces `DATA_UNAVAILABLE`; no known subtotal is treated as a complete portfolio. Raw closes and explicitly applied validated corporate actions follow ADR-005. The benchmark uses real closes, explicit splits and non-reinvested gross dividends with dated FX; its basis differs visibly from the portfolio's net-of-cost TWR. Returns remain provisional until action coverage is verified.

The end-of-day flow convention is reproducible from the available daily ledger. Intraday capital-weighting is deferred until intraday valuations and timestamps exist. XIRR returns null when roots are absent or ambiguous. FX attribution is a dated component, not a claim of exact trade-level currency attribution.
