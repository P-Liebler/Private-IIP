import copy
from datetime import UTC, date, datetime
from pathlib import Path
import sys
import unittest
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from holdings_refresh import completion, quota_errors, requests_for_holdings


class HoldingsRefreshTests(unittest.TestCase):
    def setUp(self):
        self.iid = str(uuid4())
        self.start, self.end = date(2026, 10, 1), date(2026, 10, 26)
        self.now = datetime(2026, 10, 28, tzinfo=UTC)
        self.detail = {"id": self.iid, "ticker": "FIXTURE", "mic": "XNAS", "currency": "USD",
                       "asset_type": "STOCK", "active": True}
        self.valuation = {"base_currency": "CHF", "holdings": [
            {"instrument_id": self.iid, "quantity": "2", "currency": "USD"},
            {"instrument_id": self.iid, "quantity": "-1", "currency": "USD"},
            {"instrument_id": str(uuid4()), "quantity": "0", "currency": "JPY"}],
            "cash": [{"amount": "-10", "currency": "EUR"}]}
        self.alpha = {"slug": "ALPHAVANTAGE", "enabled": True, "gate_status": "APPROVED",
            "checked_at": "2026-10-27T00:00:00+00:00", "next_review_at": "2026-11-01T00:00:00+00:00",
            "terms_url": "https://example.invalid/fixture-only", "rate_limit_per_minute": 1,
            "allowed_uses": ["prices", "raw_archive", "derived_analysis"],
            "scope": f"instrument={self.iid} price_listing={self.iid}|FIXTURE|XNAS|USD|STOCK|2026-10-01|2026-10-26"}
        self.ecb = {**self.alpha, "slug": "ECB", "allowed_uses": ["fx_rates", "raw_archive", "derived_analysis"],
            "scope": "fx_inputs=EXR.D.CHF.EUR.SP00.A,EXR.D.USD.EUR.SP00.A fx_coverage=2026-10-01|2026-10-26"}

    def plan(self, sources=None, detail=None):
        return requests_for_holdings(self.valuation, self.start, self.end,
            sources if sources is not None else [self.alpha, self.ecb],
            {self.iid: detail if detail is not None else self.detail}, now=self.now)

    def test_current_nonzero_positions_deduplicated_and_negative_cash_included(self):
        jobs, unavailable = self.plan()
        self.assertEqual([job["kind"] for job in jobs], ["ALPHA_PRICES", "ECB_FX"])
        self.assertEqual(jobs[0]["instrument_ids"], [self.iid])
        self.assertEqual(jobs[1]["series"], "USD_CHF")
        self.assertEqual(unavailable, [])
        self.valuation["holdings"] = []
        jobs, unavailable = self.plan()
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["series"], "EUR_CHF")

    def test_source_absence_never_falls_back_to_advertised_provider(self):
        jobs, unavailable = self.plan([])
        self.assertEqual(jobs, [])
        self.assertEqual({row["kind"] for row in unavailable}, {"prices", "fx"})
        self.assertTrue(all(row["action"] == "MANUAL_IMPORT_OR_REVIEW" for row in unavailable))

    def test_approved_enabled_and_current_review_are_independent_hard_gates(self):
        for change in [{"enabled": False}, {"gate_status": "UNKNOWN"}, {"gate_reason": "SOURCE_NOT_APPROVED"},
                       {"checked_at": "2026-10-29T00:00:00+00:00"}, {"checked_at": "2026-10-27"},
                       {"next_review_at": "2026-10-28T00:00:00+00:00"}, {"rate_limit_per_minute": None}]:
            with self.subTest(change=change):
                jobs, missing = self.plan([{**self.alpha, **change}, self.ecb])
                self.assertFalse(any(job["kind"] == "ALPHA_PRICES" for job in jobs))
                self.assertTrue(any(row["kind"] == "prices" for row in missing))

    def test_generic_personal_use_does_not_imply_raw_archive_and_analysis_rights(self):
        self.alpha["allowed_uses"] = ["prices"]
        self.assertEqual([job["kind"] for job in self.plan()[0]], ["ECB_FX"])
        self.alpha["allowed_uses"] = ["prices", "raw_archive"]
        self.assertEqual([job["kind"] for job in self.plan()[0]], ["ECB_FX"])

    def test_listing_and_window_must_match_exactly_even_when_same_isin(self):
        for field, value in [("ticker", "OTHER"), ("mic", "XNYS"), ("currency", "EUR"),
                             ("asset_type", "ETF"), ("active", False), ("id", str(uuid4()))]:
            with self.subTest(field=field):
                detail = {**self.detail, field: value, "isin": "same-isin-is-not-a-listing"}
                self.assertFalse(any(j["kind"] == "ALPHA_PRICES" for j in self.plan(detail=detail)[0]))
        self.alpha["scope"] = self.alpha["scope"].replace("2026-10-01|2026-10-26", "2026-10-02|2026-10-26")
        self.assertFalse(any(j["kind"] == "ALPHA_PRICES" for j in self.plan()[0]))

    def test_coverage_tokens_cannot_replace_existing_collector_identity_scope(self):
        self.alpha["scope"] = self.alpha["scope"].split(" ", 1)[1]
        self.assertFalse(any(j["kind"] == "ALPHA_PRICES" for j in self.plan()[0]))

    def test_conflicting_or_duplicate_listing_attestations_require_review(self):
        self.alpha["scope"] += " " + self.alpha["scope"].split(" ", 1)[1]
        self.assertFalse(any(j["kind"] == "ALPHA_PRICES" for j in self.plan()[0]))
        with self.assertRaisesRegex(ValueError, "SOURCE_REGISTRY_AMBIGUOUS"):
            self.plan([self.alpha, copy.deepcopy(self.alpha)])

    def test_fx_requires_rights_to_both_actual_collector_input_legs_and_window(self):
        self.ecb["scope"] = self.ecb["scope"].replace(",EXR.D.USD.EUR.SP00.A", "")
        jobs, missing = self.plan()
        self.assertFalse(any(j["kind"] == "ECB_FX" for j in jobs))
        self.assertEqual(missing[0]["reason"], "NO_APPROVED_ECB_INPUT_COVERAGE")

    def test_missing_nonfinite_and_unsupported_values_are_not_zero(self):
        with self.assertRaises(ValueError):
            requests_for_holdings({}, self.start, self.end)
        for value in ["NaN", "Infinity", None]:
            with self.subTest(value=value):
                self.valuation["holdings"][0]["quantity"] = value
                with self.assertRaises(ValueError):
                    self.plan()
        self.valuation["holdings"][0]["quantity"] = "1"
        self.valuation["cash"].append({"amount": "-1", "currency": "JPY"})
        self.assertTrue(any(row.get("currency") == "JPY" for row in self.plan()[1]))

    def test_holdings_currency_disagreement_does_not_select_price_source(self):
        self.valuation["holdings"][0]["currency"] = "EUR"
        self.assertFalse(any(j["kind"] == "ALPHA_PRICES" for j in self.plan()[0]))

    def test_preview_budgets_do_not_claim_remaining_provider_quota(self):
        receipt = {"request": {"source_slug": "ALPHAVANTAGE"}, "maximum_requests": 3}
        overview = {"daily_request_limit": 100, "jobs": []}
        self.assertEqual(quota_errors([receipt], overview), [])
        self.assertIn("CONSERVATIVE_DAILY_REQUEST_BUDGET_EXCEEDED", quota_errors([receipt] * 9, overview))
        self.assertIn("PENDING_JOB_BUDGET_EXCEEDED", quota_errors([receipt] * 5, overview))
        self.assertIn("APPLICATION_QUOTA_RESPONSE_INVALID", quota_errors([receipt], {}))

    def test_checkpoint_receipt_keeps_failure_and_progress_without_raw_response(self):
        receipt = completion({"id": str(uuid4()), "status": "PARTIAL", "progress": 1,
                              "last_error_code": "SOURCE_RATE_LIMITED", "results": [{"raw": "not-for-receipt"}]})
        self.assertEqual(receipt["last_error_code"], "SOURCE_RATE_LIMITED")
        self.assertEqual(receipt["result_chunks"], 1)
        self.assertNotIn("results", receipt)


if __name__ == "__main__":
    unittest.main()
