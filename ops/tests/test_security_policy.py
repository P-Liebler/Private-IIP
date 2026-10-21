"""Expired/unapproved exceptions and absent scans must never clear release gates."""
from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from security_policy import approved_exception, evaluate


class SecurityPolicyTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(UTC)
        self.finding = {"component": "test", "cve": "CVE-TEST", "image_id": "sha256:" + "a" * 64, "severity": "CRITICAL"}
        self.image = {"component": "test", "image_id": self.finding["image_id"], "scan_status": "SCANNED_EXACT_IMAGE", "sbom_sha256": "b" * 64, "findings": [self.finding]}
        self.exception = {"component": "test", "cve": "CVE-TEST", "digest": self.finding["image_id"], "technical_reason": "synthetic test", "reachability_evidence": "synthetic evidence", "mitigations": "synthetic isolation", "reviewer": "synthetic-reviewer", "approval_reference": "synthetic-operator-decision", "approved_at": (self.now - timedelta(days=1)).isoformat(), "expires_at": (self.now + timedelta(days=1)).isoformat(), "re_review_trigger": "new image, configuration, advisory or evidence"}

    def test_missing_optional_service_scan_still_incomplete_when_in_release(self):
        self.assertEqual(evaluate([self.image], ["test", "optional"]), "SCAN_INCOMPLETE")
        self.assertEqual(evaluate([self.image | {"findings": None}], ["test"]), "SCAN_INCOMPLETE")

    def test_critical_blocks_without_approved_exact_digest_exception(self):
        self.assertEqual(evaluate([self.image], ["test"]), "SECURITY_BLOCKED")
        self.assertFalse(approved_exception(self.exception | {"digest": "sha256:other"}, self.finding, self.now))
        self.assertFalse(approved_exception(self.exception | {"approval_reference": ""}, self.finding, self.now))

    def test_exception_expiry_and_re_review_are_enforced(self):
        self.assertTrue(approved_exception(self.exception, self.finding, self.now))
        self.assertFalse(approved_exception(self.exception | {"expires_at": self.now.isoformat()}, self.finding, self.now))
        self.assertFalse(approved_exception(self.exception | {"expires_at": (self.now + timedelta(days=100)).isoformat()}, self.finding, self.now))
        self.assertFalse(approved_exception(self.exception | {"re_review_trigger": ""}, self.finding, self.now))

    def test_zero_findings_requires_separate_runtime_review(self):
        self.assertEqual(evaluate([self.image | {"findings": []}], ["test"]), "SECURITY_REVIEW_REQUIRED")
