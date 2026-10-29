"""Canonical identifiers add no exception approval or alternate digest scope."""
from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from security_policy import approved_exception, evaluate, finding_identifier


class FindingIdentifierTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(UTC)
        self.finding = {"component": "legacy-verifier", "cve": "GHSA-6q48-6c7w-9gw2",
                        "image_id": "sha256:" + "a" * 64, "severity": "CRITICAL"}
        self.exception = {"finding_id": self.finding["cve"], "component": "legacy-verifier",
                          "digest": self.finding["image_id"], "technical_reason": "synthetic fixture",
                          "reachability_evidence": "synthetic fixture", "mitigations": "synthetic fixture",
                          "reviewer": "synthetic-fixture-only", "approval_reference": "synthetic-fixture-only",
                          "approved_at": (self.now - timedelta(minutes=1)).isoformat(),
                          "expires_at": (self.now + timedelta(minutes=30)).isoformat(),
                          "re_review_trigger": "changed digest/config/advisory/input"}

    def test_verified_ghsa_identifier_needs_no_invented_cve_alias(self):
        self.assertTrue(approved_exception(self.exception, self.finding, self.now))
        self.assertNotIn("cve", self.exception)
        for key in ("reviewer", "approval_reference", "re_review_trigger", "technical_reason",
                    "reachability_evidence", "mitigations", "expires_at", "approved_at"):
            for value in (None, " ", ["synthetic-not-a-review-string"]):
                self.assertFalse(approved_exception(self.exception | {key: value}, self.finding, self.now))

    def test_aliases_are_compatible_only_when_exactly_equal(self):
        self.assertTrue(approved_exception(self.exception | {"cve": self.finding["cve"]}, self.finding, self.now))
        self.assertFalse(approved_exception(self.exception | {"cve": "CVE-2026-9999999"}, self.finding, self.now))
        self.assertFalse(approved_exception(self.exception, self.finding | {"finding_id": "CVE-2026-9999999"}, self.now))

    def test_malformed_and_unrelated_identifiers_cannot_authorize_exception(self):
        for value in (None, [], "CVE-TEST", "CVE-26-1234", "CVE-2026-123", "GHSA-aaaa-bbbb-cccc",
                      "ghsa-6q48-6c7w-9gw2", "GHSA-6q48-6c7w-9gw2 ", "CVE-2026-1234\n"):
            with self.subTest(identifier=value):
                self.assertIsNone(finding_identifier({"finding_id": value}))
                self.assertFalse(approved_exception(self.exception | {"finding_id": value}, self.finding, self.now))
        self.assertFalse(approved_exception(self.exception | {"finding_id": "CVE-2026-1234"}, self.finding, self.now))

    def test_exact_digest_component_and_expiry_stay_mandatory(self):
        for mutation in ({"digest": "sha256:" + "b" * 64}, {"component": "api"},
                         {"expires_at": self.now.isoformat()},
                         {"expires_at": (self.now + timedelta(days=100)).isoformat()}):
            self.assertFalse(approved_exception(self.exception | mutation, self.finding, self.now))

    def test_absence_of_real_decision_still_blocks_and_exception_never_releases(self):
        image = {"component": "legacy-verifier", "image_id": self.finding["image_id"],
                 "scan_status": "SCANNED_EXACT_IMAGE", "sbom_sha256": "b" * 64,
                 "findings": [self.finding]}
        self.assertEqual(evaluate([image], ["legacy-verifier"], now=self.now), "SECURITY_BLOCKED")
        self.assertEqual(evaluate([image], ["legacy-verifier"], [self.exception], self.now), "SECURITY_REVIEW_REQUIRED")
