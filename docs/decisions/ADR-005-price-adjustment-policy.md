# ADR-005: Return calculation from raw closes and explicit actions

**Status:** Accepted for P3 calculation; action coverage remains unverified  
**Date:** 2026-10-12

Returns use unadjusted validated closes plus validated split and dividend events. A split changes share count; a cash dividend contributes cash using the shares held on its ex-date. `adjusted_close` is retained as a source observation and plausibility check only. Applying it again with actions would double count. Golden tests cover price-only, split, dividend, combined split/dividend and reverse split arithmetic.

A ticker change or delisting in the interval suspends the endpoint's calculation pending review. The P3 import path cannot yet certify that an action history is complete, so the endpoint labels calculated results `PROVISIONAL` with `action_coverage=UNVERIFIED`. Later portfolio accounting must require verified coverage and a defined treatment of missing or contradictory actions before accepting total return. This preserves the calculation contract without manufacturing completeness.
