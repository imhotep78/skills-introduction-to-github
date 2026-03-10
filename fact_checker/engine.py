"""
Fact Checker Engine
===================
The core engine that combines the :class:`FactsDatabase` and the
:class:`EthicsGuard` to produce verifiable, ethically sound verdicts.

Design principle – **facts over semantics**:
  The engine first attempts to match a claim against a structured fact
  database.  Only when no structured fact matches does it fall back to
  a lightweight semantic heuristic.  This ensures that the primary
  source of truth is always an explicit, attributed fact record rather
  than a language-model inference.

Verdict taxonomy
----------------
``TRUE``      – claim matches a known fact (confidence ≥ 0.8).
``LIKELY``    – claim matches a known fact with moderate confidence (0.5–0.8).
``FALSE``     – claim directly contradicts a known fact.
``UNCERTAIN`` – no matching fact found, or confidence < 0.5.
``REFUSED``   – the claim failed ethics pre-screening.
``ERROR``     – an unexpected error occurred during processing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .ethics import EthicsGuard, EthicsReport
from .facts_db import Fact, FactsDatabase, build_default_database


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class CheckResult:
    """The complete output of a single fact-check operation."""

    claim: str
    verdict: str  # TRUE | LIKELY | FALSE | UNCERTAIN | REFUSED | ERROR
    explanation: str
    source: Optional[str] = None
    confidence: float = 0.0
    matched_fact: Optional[Fact] = None
    ethics_report: Optional[EthicsReport] = None
    warnings: List[str] = field(default_factory=list)

    def is_verified(self) -> bool:
        """Return True if the claim was positively verified."""
        return self.verdict in ("TRUE", "LIKELY")

    def as_dict(self) -> dict:
        return {
            "claim": self.claim,
            "verdict": self.verdict,
            "explanation": self.explanation,
            "source": self.source,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class FactCheckerEngine:
    """
    Fact-checking engine with built-in ethics enforcement.

    Parameters
    ----------
    db:
        The :class:`~fact_checker.facts_db.FactsDatabase` to use.
        Defaults to the built-in seed database.
    ethics_guard:
        Custom :class:`~fact_checker.ethics.EthicsGuard`.
        Defaults to a standard guard instance.
    strict_ethics:
        When ``True`` (default), a failed ethics pre-check causes the
        verdict to be ``REFUSED``.  Set to ``False`` to treat ethics
        failures as warnings only (not recommended for production).
    """

    def __init__(
        self,
        db: Optional[FactsDatabase] = None,
        ethics_guard: Optional[EthicsGuard] = None,
        strict_ethics: bool = True,
    ) -> None:
        self._db = db if db is not None else build_default_database()
        self._guard = ethics_guard if ethics_guard is not None else EthicsGuard()
        self._strict_ethics = strict_ethics

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self, claim: str) -> CheckResult:
        """
        Fact-check *claim* and return a :class:`CheckResult`.

        Steps
        -----
        1. Ethics pre-check on the raw claim.
        2. Normalise and tokenise the claim.
        3. Look for matching facts in the database (facts over semantics).
        4. Determine verdict from match quality.
        5. Ethics post-check on the proposed verdict.
        6. Attach any warnings and return.
        """
        # --- 1. Ethics pre-check ---
        ethics_report = self._guard.check_claim(claim)
        if not ethics_report.passed and self._strict_ethics:
            return CheckResult(
                claim=claim,
                verdict="REFUSED",
                explanation=(
                    "This claim was not checked because it failed ethical "
                    "pre-screening: "
                    + "; ".join(v.explanation for v in ethics_report.violations)
                ),
                ethics_report=ethics_report,
                warnings=[w for w in ethics_report.warnings],
            )

        warnings: List[str] = list(ethics_report.warnings)

        # --- 2. Normalise ---
        normalised = self._normalise(claim)

        # --- 3. Match against structured facts (facts over semantics) ---
        fact, confidence, contradiction = self._match_facts(normalised)

        # --- 4. Determine verdict ---
        verdict, explanation = self._determine_verdict(
            normalised, fact, confidence, contradiction
        )

        # --- 5. Ethics post-check ---
        source = fact.source if fact else None
        out_ethics = self._guard.check_verdict(
            verdict=verdict,
            source=source,
            confidence=confidence,
            matched=fact is not None and not contradiction,
        )
        if not out_ethics.passed and self._strict_ethics:
            verdict = "UNCERTAIN"
            explanation = (
                "The result could not be presented because it failed ethical "
                "post-screening: "
                + "; ".join(v.explanation for v in out_ethics.violations)
            )
        warnings.extend(out_ethics.warnings)

        return CheckResult(
            claim=claim,
            verdict=verdict,
            explanation=explanation,
            source=source,
            confidence=confidence,
            matched_fact=fact,
            ethics_report=ethics_report,
            warnings=warnings,
        )

    def add_fact(self, fact: Fact) -> None:
        """Add a single :class:`~fact_checker.facts_db.Fact` to the database."""
        self._db.add_fact(fact)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise(text: str) -> str:
        """Lower-case, strip punctuation noise, collapse whitespace."""
        text = text.lower()
        # remove possessive apostrophes
        text = re.sub(r"'s\b", "", text)
        # collapse all non-alphanumeric runs to a single space
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return text.strip()

    def _match_facts(
        self, normalised_claim: str
    ) -> Tuple[Optional[Fact], float, bool]:
        """
        Search the database for a fact relevant to *normalised_claim*.

        Returns ``(fact, confidence, is_contradiction)``.

        Strategy – facts over semantics:
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        We look for the longest subject string from the database that
        appears verbatim in the claim text, then check whether the fact's
        object also appears.  This keeps matching anchored to explicit
        textual evidence rather than embeddings or fuzzy NLP.
        """
        tokens = set(normalised_claim.split())
        best_fact: Optional[Fact] = None
        best_score: float = 0.0
        is_contradiction = False

        # Collect all unique subjects across the entire database
        all_subjects = list(self._db._index.keys())

        # Prefer longer subjects (more specific match)
        all_subjects.sort(key=len, reverse=True)

        for subject in all_subjects:
            if not self._subject_in_claim(subject, normalised_claim):
                continue

            facts = self._db.get_facts_for_subject(subject)
            for fact in facts:
                score = self._score_fact(fact, normalised_claim)
                if score > best_score:
                    best_score = score
                    best_fact = fact
                    is_contradiction = self._is_contradiction(fact, normalised_claim)

        effective_confidence = best_score * (best_fact.confidence if best_fact else 1.0)
        return best_fact, effective_confidence, is_contradiction

    @staticmethod
    def _subject_in_claim(subject: str, claim: str) -> bool:
        """Return True if *subject* appears as a token sequence in *claim*."""
        pattern = r"\b" + re.escape(subject) + r"\b"
        return bool(re.search(pattern, claim))

    def _score_fact(self, fact: Fact, claim: str) -> float:
        """
        Score how well *fact* matches *claim*.

        Scoring rubric (facts over semantics):
          +0.5  if the fact's object appears verbatim in the claim.
          +0.3  if the fact's predicate keywords appear in the claim.
          +0.2  subject match (already guaranteed by caller, bonus for exact).

        Maximum raw score is 1.0.
        """
        score = 0.0

        # Subject already matched; reward exact (non-alias) match
        if self._subject_in_claim(fact.subject, claim):
            score += 0.2

        # Predicate keyword overlap
        pred_words = set(fact.predicate.split())
        claim_words = set(claim.split())
        if pred_words & claim_words:
            overlap_ratio = len(pred_words & claim_words) / max(len(pred_words), 1)
            score += 0.3 * overlap_ratio

        # Object appears verbatim in claim
        obj_pattern = r"\b" + re.escape(fact.obj) + r"\b"
        if re.search(obj_pattern, claim):
            score += 0.5

        return min(score, 1.0)

    @staticmethod
    def _is_contradiction(fact: Fact, claim: str) -> bool:
        """
        Return True if the claim appears to *contradict* the fact.

        Detects negation that is closely followed by the fact's object, e.g.
        "is not a star" or "does not boil at 100 degrees celsius".
        """
        neg_then_obj = re.compile(
            r"\b(not|no|never|isn't|aren't|wasn't|weren't|doesn't|don't|"
            r"cannot|can't|false|wrong|incorrect|untrue)\b[^.!?]{0,40}\b"
            + re.escape(fact.obj)
            + r"\b",
            re.IGNORECASE,
        )
        return bool(neg_then_obj.search(claim))

    @staticmethod
    def _determine_verdict(
        claim: str,
        fact: Optional[Fact],
        confidence: float,
        contradiction: bool,
    ) -> Tuple[str, str]:
        """Map match result to a human-readable verdict + explanation."""
        if fact is None:
            return (
                "UNCERTAIN",
                "No matching fact was found in the database for this claim.",
            )

        if contradiction:
            return (
                "FALSE",
                (
                    f"The claim contradicts the known fact: "
                    f"'{fact.subject} {fact.predicate} {fact.obj}' "
                    f"(source: {fact.source})."
                ),
            )

        if confidence >= 0.7:
            return (
                "TRUE",
                (
                    f"The claim is supported by a known fact: "
                    f"'{fact.subject} {fact.predicate} {fact.obj}' "
                    f"(source: {fact.source}, confidence: {confidence:.0%})."
                ),
            )

        if confidence >= 0.5:
            return (
                "LIKELY",
                (
                    f"The claim is probably supported by a known fact: "
                    f"'{fact.subject} {fact.predicate} {fact.obj}' "
                    f"(source: {fact.source}, confidence: {confidence:.0%}). "
                    "Verify independently before relying on this result."
                ),
            )

        return (
            "UNCERTAIN",
            (
                f"A related fact was found ('{fact.subject} {fact.predicate} "
                f"{fact.obj}') but confidence is too low ({confidence:.0%}) "
                "to make a definitive determination."
            ),
        )
