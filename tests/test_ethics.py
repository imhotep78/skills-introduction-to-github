"""
Tests for EthicsGuard.
"""

import pytest
from fact_checker.ethics import EthicsGuard, EthicsReport, EthicsViolation


class TestClaimPreCheck:
    def test_valid_claim_passes(self, guard):
        report = guard.check_claim("Water boils at 100 degrees Celsius.")
        assert report.passed is True
        assert report.violations == []

    def test_empty_claim_fails(self, guard):
        report = guard.check_claim("")
        assert report.passed is False
        rules = [v.rule for v in report.violations]
        assert "NON_EMPTY_CLAIM" in rules

    def test_whitespace_claim_fails(self, guard):
        report = guard.check_claim("    ")
        assert report.passed is False

    def test_too_long_claim_fails(self, guard):
        report = guard.check_claim("A" * 2001)
        assert report.passed is False
        rules = [v.rule for v in report.violations]
        assert "MAX_CLAIM_LENGTH" in rules

    def test_2000_char_claim_passes(self, guard):
        report = guard.check_claim("A" * 2000)
        assert report.passed is True

    def test_protected_group_triggers_warning(self, guard):
        report = guard.check_claim("People of a certain religion are smart.")
        assert report.passed is True  # warning, not violation
        assert any("protected-group" in w.lower() for w in report.warnings)

    def test_absolute_language_triggers_warning(self, guard):
        report = guard.check_claim("Everyone always lies.")
        assert report.passed is True  # warning, not violation
        assert any("absolute" in w.lower() for w in report.warnings)


class TestVerdictPostCheck:
    def test_matched_fact_with_source_passes(self, guard):
        report = guard.check_verdict(
            verdict="TRUE",
            source="NIST",
            confidence=0.9,
            matched=True,
        )
        assert report.passed is True

    def test_matched_fact_without_source_fails(self, guard):
        report = guard.check_verdict(
            verdict="TRUE",
            source=None,
            confidence=0.9,
            matched=True,
        )
        assert report.passed is False
        rules = [v.rule for v in report.violations]
        assert "SOURCE_REQUIRED" in rules

    def test_matched_fact_blank_source_fails(self, guard):
        report = guard.check_verdict(
            verdict="TRUE",
            source="   ",
            confidence=0.9,
            matched=True,
        )
        assert report.passed is False

    def test_low_confidence_fails(self, guard):
        report = guard.check_verdict(
            verdict="TRUE",
            source="NIST",
            confidence=0.4,
            matched=True,
        )
        assert report.passed is False
        rules = [v.rule for v in report.violations]
        assert "MIN_CONFIDENCE" in rules

    def test_medium_confidence_warning(self, guard):
        report = guard.check_verdict(
            verdict="TRUE",
            source="NIST",
            confidence=0.60,
            matched=True,
        )
        assert report.passed is True
        assert len(report.warnings) > 0

    def test_unmatched_no_source_required(self, guard):
        report = guard.check_verdict(
            verdict="UNCERTAIN",
            source=None,
            confidence=0.0,
            matched=False,
        )
        assert report.passed is True


class TestPiiRedaction:
    def test_email_redacted(self, guard):
        result = guard.redact_pii("Contact me at alice@example.com please.")
        assert "[EMAIL]" in result
        assert "alice@example.com" not in result

    def test_phone_redacted(self, guard):
        result = guard.redact_pii("Call +1-800-555-1234 now.")
        assert "[PHONE]" in result

    def test_clean_text_unchanged(self, guard):
        text = "The sun is a star."
        assert guard.redact_pii(text) == text


class TestEthicsReportHelpers:
    def test_add_violation_sets_passed_false(self):
        report = EthicsReport(passed=True)
        report.add_violation("TEST_RULE", "Test violation.")
        assert report.passed is False
        assert len(report.violations) == 1

    def test_add_warning_does_not_affect_passed(self):
        report = EthicsReport(passed=True)
        report.add_warning("Just a warning.")
        assert report.passed is True
        assert len(report.warnings) == 1
