"""Shared test fixtures."""
import pytest
from fact_checker.facts_db import Fact, FactsDatabase, build_default_database
from fact_checker.engine import FactCheckerEngine
from fact_checker.ethics import EthicsGuard


@pytest.fixture()
def default_db():
    return build_default_database()


@pytest.fixture()
def engine(default_db):
    return FactCheckerEngine(db=default_db)


@pytest.fixture()
def guard():
    return EthicsGuard()
