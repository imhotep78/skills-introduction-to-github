"""
Ethical Fact Checker Engine
===========================
A fact-checking engine that prioritises verifiable facts over semantic
interpretation, applying transparent ethical guidelines throughout.
"""

from .engine import FactCheckerEngine
from .ethics import EthicsGuard
from .facts_db import FactsDatabase

__all__ = ["FactCheckerEngine", "EthicsGuard", "FactsDatabase"]
__version__ = "0.1.0"
