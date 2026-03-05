"""
Tests for FactCheckerEngine – verifying facts-over-semantics behaviour.
"""

import pytest
from fact_checker.engine import CheckResult, FactCheckerEngine
from fact_checker.facts_db import Fact, FactsDatabase, build_default_database


# ---------------------------------------------------------------------------
# Verdict: TRUE
# ---------------------------------------------------------------------------


class TestTrueVerdicts:
    def test_water_boiling_point(self, engine):
        result = engine.check("Water boils at 100 degrees Celsius.")
        assert result.verdict == "TRUE"
        assert result.confidence >= 0.7

    def test_sun_is_a_star(self, engine):
        result = engine.check("The sun is a star.")
        assert result.verdict == "TRUE"

    def test_dna_stands_for(self, engine):
        result = engine.check("DNA stands for deoxyribonucleic acid.")
        assert result.verdict == "TRUE"

    def test_python_first_released(self, engine):
        result = engine.check("Python was first released in 1991.")
        assert result.verdict == "TRUE"

    def test_speed_of_light(self, engine):
        result = engine.check(
            "The speed of light in a vacuum is 299792458 metres per second."
        )
        assert result.verdict == "TRUE"

    def test_world_war_ii_ended_1945(self, engine):
        result = engine.check("World War II ended in 1945.")
        assert result.verdict == "TRUE"


# ---------------------------------------------------------------------------
# Verdict: UNCERTAIN (no matching fact)
# ---------------------------------------------------------------------------


class TestUncertainVerdicts:
    def test_unknown_claim(self, engine):
        result = engine.check(
            "The capital of Mars is Olympus City."
        )
        assert result.verdict == "UNCERTAIN"

    def test_vague_claim(self, engine):
        result = engine.check("Things happen sometimes.")
        assert result.verdict == "UNCERTAIN"


# ---------------------------------------------------------------------------
# Verdict: FALSE (contradiction)
# ---------------------------------------------------------------------------


class TestFalseVerdicts:
    def test_sun_is_not_a_star(self, engine):
        result = engine.check("The sun is not a star.")
        assert result.verdict == "FALSE"

    def test_explicit_false_water(self, engine):
        result = engine.check("Water does not boil at 100 degrees Celsius.")
        assert result.verdict == "FALSE"


# ---------------------------------------------------------------------------
# Verdict: REFUSED (ethics pre-check)
# ---------------------------------------------------------------------------


class TestRefusedVerdicts:
    def test_empty_claim_refused(self, engine):
        result = engine.check("")
        assert result.verdict == "REFUSED"

    def test_whitespace_only_refused(self, engine):
        result = engine.check("   ")
        assert result.verdict == "REFUSED"

    def test_overly_long_claim_refused(self, engine):
        result = engine.check("X" * 2001)
        assert result.verdict == "REFUSED"


# ---------------------------------------------------------------------------
# Source citation is always present for TRUE results
# ---------------------------------------------------------------------------


class TestSourceCitation:
    def test_true_result_has_source(self, engine):
        result = engine.check("Water boils at 100 degrees Celsius.")
        assert result.source is not None and result.source.strip() != ""

    def test_uncertain_result_may_lack_source(self, engine):
        result = engine.check("Invisible dragons live in the sky.")
        # Source can be None for uncertain results – no ethics violation expected
        assert result.verdict == "UNCERTAIN"


# ---------------------------------------------------------------------------
# Custom fact injection
# ---------------------------------------------------------------------------


class TestCustomFacts:
    def test_add_custom_fact_verified(self, engine):
        engine.add_fact(
            Fact(
                subject="fictional city",
                predicate="was founded in",
                obj="1999",
                source="Fictional Encyclopedia",
                confidence=1.0,
            )
        )
        result = engine.check(
            "The fictional city was founded in 1999."
        )
        assert result.verdict == "TRUE"
        assert result.source == "Fictional Encyclopedia"

    def test_alias_resolution(self):
        db = FactsDatabase()
        db.add_fact(
            Fact(
                subject="hydrogen",
                predicate="atomic number is",
                obj="1",
                source="periodic table",
                confidence=1.0,
                aliases=["h", "element 1"],
            )
        )
        engine = FactCheckerEngine(db=db)
        result = engine.check("H atomic number is 1.")
        assert result.verdict in ("TRUE", "LIKELY")


# ---------------------------------------------------------------------------
# CheckResult helpers
# ---------------------------------------------------------------------------


class TestCheckResultHelpers:
    def test_is_verified_true(self, engine):
        result = engine.check("The sun is a star.")
        assert result.is_verified() is True

    def test_is_verified_uncertain(self, engine):
        result = engine.check("Unicorns can fly.")
        assert result.is_verified() is False

    def test_as_dict_keys(self, engine):
        result = engine.check("Water boils at 100 degrees Celsius.")
        d = result.as_dict()
        assert set(d.keys()) >= {"claim", "verdict", "explanation", "source", "confidence", "warnings"}

    def test_as_dict_claim_preserved(self, engine):
        claim = "Water boils at 100 degrees Celsius."
        result = engine.check(claim)
        assert result.as_dict()["claim"] == claim


# ---------------------------------------------------------------------------
# Non-strict ethics mode
# ---------------------------------------------------------------------------


class TestNonStrictEthics:
    def test_non_strict_does_not_refuse_empty(self):
        engine = FactCheckerEngine(strict_ethics=False)
        result = engine.check("")
        # In non-strict mode the empty claim still cannot match any fact
        assert result.verdict == "UNCERTAIN"
