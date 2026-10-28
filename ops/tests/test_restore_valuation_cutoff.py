import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from restore_verify import main, valuation_cutoff


class RestoreValuationCutoffTests(unittest.TestCase):
    def test_core_restore_cannot_silently_fall_back_to_legacy_client(self):
        args = ['restore_verify', 'not-read', '--username', 'restore_synthetic',
                '--portfolio-id', 'synthetic', '--raw-id', 'synthetic', '--expected-value', '10180',
                '--object-store-kind', 'seaweed-synthetic']
        with patch('sys.argv', args), patch('restore_verify.command') as command:
            with self.assertRaises(SystemExit) as error:
                main()
            self.assertEqual(error.exception.code, 2)
            command.assert_not_called()

    def test_unpinned_recovery_client_rejected_before_services_or_backup_reads(self):
        args = ['restore_verify', 'not-read', '--username', 'restore_synthetic',
                '--portfolio-id', 'synthetic', '--raw-id', 'synthetic', '--expected-value', '10180',
                '--client-image', 'private-iip/mc:latest']
        with patch('sys.argv', args), patch('restore_verify.command') as command:
            with self.assertRaises(SystemExit) as error:
                main()
            self.assertEqual(error.exception.code, 2)
            command.assert_not_called()

    def test_observed_instant_is_normalized_but_future_and_naive_are_rejected(self):
        self.assertEqual(valuation_cutoff('2026-01-01T03:00:00+02:00'), '2026-01-01T01:00:00+00:00')
        for value in ['2026-01-01T03:00:00', (datetime.now(UTC) + timedelta(days=1)).isoformat(), 'invalid']:
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                valuation_cutoff(value)


if __name__ == '__main__':
    unittest.main()
