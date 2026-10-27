import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from restore_verify import valuation_cutoff


class RestoreValuationCutoffTests(unittest.TestCase):
    def test_observed_instant_is_normalized_but_future_and_naive_are_rejected(self):
        self.assertEqual(valuation_cutoff('2026-01-01T03:00:00+02:00'), '2026-01-01T01:00:00+00:00')
        for value in ['2026-01-01T03:00:00', (datetime.now(UTC) + timedelta(days=1)).isoformat(), 'invalid']:
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                valuation_cutoff(value)


if __name__ == '__main__':
    unittest.main()
