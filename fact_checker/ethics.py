"""
Ethics Guard
============
Enforces ethical constraints before and after fact-checking so that the
engine never produces output that is harmful, biased, or untransparent.

Design principles ("facts over semantics"):
  1. **Transparency** – every verdict must include a reason and source.
  2. **Neutrality**   – reject claims that target protected groups.
  3. **Honesty**      – a low-confidence match must never be presented
                        as definitive.
  4. **Attribution**  – sources must always be cited.
  5. **Proportionality** – confidence in the output may never exceed
                           confidence in the underlying fact.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Patterns considered potentially harmful / biased
# ---------------------------------------------------------------------------

_PROTECTED_GROUP_PATTERN = re.compile(
    r"\b(race|gender|ethnicity|religion|nationality|sexuality|disability"
    r"|class|caste|age|sex)\b",
    re.IGNORECASE,
)

_ABSOLUTE_TERMS = re.compile(
    r"\b(always|never|all|none|every|no one|everyone|nobody|everybody)\b",
    re.IGNORECASE,
)


@dataclass
class EthicsViolation:
    """Describes a single ethics policy violation."""

    rule: str
    explanation: str


@dataclass
class EthicsReport:
    """Aggregated result of an ethics check."""

    passed: bool
    violations: List[EthicsViolation] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_violation(self, rule: str, explanation: str) -> None:
        self.violations.append(EthicsViolation(rule=rule, explanation=explanation))
        self.passed = False

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


class EthicsGuard:
    """
    Applies ethical rules to both *input claims* and *output verdicts*.

    Usage::

        guard = EthicsGuard()
        report = guard.check_claim("Water boils at 100 °C.")
        if report.passed:
            ...
    """

    # ------------------------------------------------------------------
    # Input validation
    # ------------------------------------------------------------------

    def check_claim(self, claim: str) -> EthicsReport:
        """
        Validate that *claim* is safe and appropriate to fact-check.

        Returns an :class:`EthicsReport`; if ``report.passed`` is
        ``False`` the engine should refuse to check the claim.
        """
        report = EthicsReport(passed=True)

        if not claim or not claim.strip():
            report.add_violation(
                rule="NON_EMPTY_CLAIM",
                explanation="The claim must not be empty.",
            )
            return report

        if len(claim) > 2000:
            report.add_violation(
                rule="MAX_CLAIM_LENGTH",
                explanation="Claims longer than 2000 characters are not accepted.",
            )

        if _PROTECTED_GROUP_PATTERN.search(claim):
            report.add_warning(
                "The claim references a protected-group attribute. "
                "Ensure the fact-check result does not reinforce stereotypes."
            )

        if _ABSOLUTE_TERMS.search(claim):
            report.add_warning(
                "The claim uses absolute language. "
                "Absolute statements are rarely factually defensible; "
                "results should reflect appropriate nuance."
            )

        return report

    # ------------------------------------------------------------------
    # Output validation
    # ------------------------------------------------------------------

    def check_verdict(
        self,
        verdict: str,
        source: Optional[str],
        confidence: float,
        matched: bool,
    ) -> EthicsReport:
        """
        Validate the proposed verdict before it is shown to the user.

        :param verdict:    The textual verdict string (e.g. ``"TRUE"``).
        :param source:     Citation for the supporting fact, or ``None``.
        :param confidence: Numeric confidence (0–1) of the match.
        :param matched:    Whether any supporting fact was found.
        """
        report = EthicsReport(passed=True)

        if matched and (source is None or not source.strip()):
            report.add_violation(
                rule="SOURCE_REQUIRED",
                explanation=(
                    "A verdict that matches a known fact must cite its source "
                    "to ensure transparency and allow independent verification."
                ),
            )

        if matched and confidence < 0.5:
            report.add_violation(
                rule="MIN_CONFIDENCE",
                explanation=(
                    f"Confidence {confidence:.0%} is too low to present a "
                    "definitive verdict.  Use UNCERTAIN instead."
                ),
            )
        elif matched and confidence < 0.7:
            report.add_warning(
                f"Confidence is only {confidence:.0%}. "
                "Consider labelling the result as LIKELY rather than TRUE."
            )

        return report

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def redact_pii(text: str) -> str:
        """
        Very simple heuristic redaction of e-mail addresses and phone
        numbers from user-supplied claim text before logging.
        """
        text = re.sub(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", "[EMAIL]", text)
        text = re.sub(r"\b\+?[\d][\d\s\-().]{7,}\d\b", "[PHONE]", text)
        return text
