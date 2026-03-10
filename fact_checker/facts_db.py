"""
Facts Database
==============
Stores structured, verifiable facts.  Each fact is represented as a
:class:`Fact` dataclass with a canonical subject/predicate/object triple
plus optional metadata (source, confidence, domain).

The database deliberately keeps facts as discrete, structured records so
that the engine can match claims against *facts* rather than trying to
infer truth from language patterns alone ("facts over semantics").
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Fact:
    """A single verifiable fact stored as a structured triple."""

    subject: str
    predicate: str
    obj: str
    source: str = "unknown"
    confidence: float = 1.0  # 0.0 – 1.0
    domain: str = "general"
    aliases: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        self.subject = self.subject.strip().lower()
        self.predicate = self.predicate.strip().lower()
        self.obj = self.obj.strip().lower()
        self.aliases = [a.strip().lower() for a in self.aliases]

    def matches_subject(self, text: str) -> bool:
        """Return True if *text* refers to this fact's subject (or an alias)."""
        normalised = text.strip().lower()
        return normalised == self.subject or normalised in self.aliases


class FactsDatabase:
    """
    In-memory store of :class:`Fact` objects.

    Facts are indexed by subject so look-ups are O(k) in the number of
    facts that share a subject rather than O(n) over the whole database.
    """

    def __init__(self) -> None:
        self._index: Dict[str, List[Fact]] = {}

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_fact(self, fact: Fact) -> None:
        """Add *fact* to the database."""
        self._index.setdefault(fact.subject, []).append(fact)
        for alias in fact.aliases:
            self._index.setdefault(alias, []).append(fact)

    def load_facts(self, facts: List[Fact]) -> None:
        """Bulk-load a list of :class:`Fact` objects."""
        for fact in facts:
            self.add_fact(fact)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_facts_for_subject(self, subject: str) -> List[Fact]:
        """Return all facts whose subject matches *subject*."""
        key = subject.strip().lower()
        return list(self._index.get(key, []))

    def search(self, subject: str, predicate: Optional[str] = None) -> List[Fact]:
        """
        Return facts matching *subject* and optionally *predicate*.

        Only *subject* is required; *predicate* is matched as a
        case-insensitive substring so callers don't need exact wording.
        """
        candidates = self.get_facts_for_subject(subject)
        if predicate is None:
            return candidates
        pred_norm = predicate.strip().lower()
        return [f for f in candidates if pred_norm in f.predicate]

    def size(self) -> int:
        """Return the number of unique facts stored (deduplicated by id)."""
        seen = set()
        count = 0
        for facts in self._index.values():
            for fact in facts:
                fid = id(fact)
                if fid not in seen:
                    seen.add(fid)
                    count += 1
        return count


# ---------------------------------------------------------------------------
# Built-in seed facts used when no custom database is supplied
# ---------------------------------------------------------------------------

SEED_FACTS: List[Fact] = [
    Fact(
        subject="earth",
        predicate="is the",
        obj="third planet from the sun",
        source="NASA",
        confidence=1.0,
        domain="astronomy",
        aliases=["the earth", "our planet"],
    ),
    Fact(
        subject="water",
        predicate="boiling point at sea level is",
        obj="100 degrees celsius",
        source="NIST",
        confidence=1.0,
        domain="chemistry",
        aliases=["h2o"],
    ),
    Fact(
        subject="water",
        predicate="chemical formula is",
        obj="h2o",
        source="IUPAC",
        confidence=1.0,
        domain="chemistry",
        aliases=["h2o"],
    ),
    Fact(
        subject="sun",
        predicate="is a",
        obj="star",
        source="NASA",
        confidence=1.0,
        domain="astronomy",
        aliases=["the sun", "sol"],
    ),
    Fact(
        subject="great wall of china",
        predicate="length is approximately",
        obj="21196 kilometres",
        source="State Administration of Cultural Heritage, China",
        confidence=0.9,
        domain="history",
        aliases=["the great wall"],
    ),
    Fact(
        subject="mount everest",
        predicate="height above sea level is",
        obj="8848.86 metres",
        source="Survey of India / China National Administration of Surveying",
        confidence=0.95,
        domain="geography",
        aliases=["everest", "mt everest", "sagarmatha", "chomolungma"],
    ),
    Fact(
        subject="speed of light",
        predicate="in a vacuum is",
        obj="299792458 metres per second",
        source="CODATA / NIST",
        confidence=1.0,
        domain="physics",
        aliases=["c", "speed of light in vacuum"],
    ),
    Fact(
        subject="dna",
        predicate="stands for",
        obj="deoxyribonucleic acid",
        source="IUPAC",
        confidence=1.0,
        domain="biology",
        aliases=["deoxyribonucleic acid"],
    ),
    Fact(
        subject="world war ii",
        predicate="ended in",
        obj="1945",
        source="encyclopaedia britannica",
        confidence=1.0,
        domain="history",
        aliases=["ww2", "second world war", "wwii"],
    ),
    Fact(
        subject="python",
        predicate="first released in",
        obj="1991",
        source="python software foundation",
        confidence=1.0,
        domain="technology",
        aliases=["python programming language"],
    ),
]


def build_default_database() -> FactsDatabase:
    """Return a :class:`FactsDatabase` pre-loaded with :data:`SEED_FACTS`."""
    db = FactsDatabase()
    db.load_facts(SEED_FACTS)
    return db
