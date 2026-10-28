from datetime import date
from pathlib import Path
import sys
import unittest
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from holdings_refresh import requests_for_holdings


class HoldingsRefreshTests(unittest.TestCase):
    def test_current_nonzero_positions_deduplicated_and_negative_cash_included(self):
        identifier = str(uuid4())
        valuation = {"base_currency": "CHF", "holdings": [
            {"instrument_id": identifier, "quantity": "2", "currency": "USD"},
            {"instrument_id": identifier, "quantity": "-1", "currency": "USD"},
            {"instrument_id": str(uuid4()), "quantity": "0", "currency": "JPY"}],
            "cash": [{"amount": "-10", "currency": "EUR"}]}
        jobs, unavailable = requests_for_holdings(valuation, date(2026, 10, 1), date(2026, 10, 26))
        self.assertEqual(len(jobs), 3)
        self.assertEqual(jobs[0]["instrument_ids"], [identifier])
        self.assertEqual({j["series"] for j in jobs if j["kind"] == "ECB_FX"}, {"USD_CHF", "EUR_CHF"})
        self.assertEqual(unavailable, [])
        valuation["holdings"] = []
        self.assertTrue(all(job["kind"] == "ECB_FX" for job in requests_for_holdings(valuation, date(2026,10,1), date(2026,10,26))[0]))

    def test_missing_nonfinite_and_unsupported_values_are_not_zero(self):
        with self.assertRaises(ValueError):
            requests_for_holdings({}, date(2026,10,1), date(2026,10,26))
        data = {"base_currency": "CHF", "holdings": [{"instrument_id": str(uuid4()), "quantity": "NaN", "currency": "JPY"}], "cash": []}
        with self.assertRaises(ValueError):
            requests_for_holdings(data, date(2026,10,1), date(2026,10,26))
        data["holdings"][0]["quantity"] = "1"
        jobs, unsupported = requests_for_holdings(data, date(2026,10,1), date(2026,10,26))
        self.assertEqual(len(jobs), 1)
        self.assertEqual(unsupported, ["JPY"])
