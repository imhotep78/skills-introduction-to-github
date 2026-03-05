"""
Tests for FactsDatabase.
"""

import pytest
from fact_checker.facts_db import Fact, FactsDatabase, build_default_database, SEED_FACTS


class TestFact:
    def test_normalises_strings(self):
        fact = Fact(subject="  Earth  ", predicate="IS THE", obj="Third Planet")
        assert fact.subject == "earth"
        assert fact.predicate == "is the"
        assert fact.obj == "third planet"

    def test_invalid_confidence_raises(self):
        with pytest.raises(ValueError):
            Fact(subject="x", predicate="y", obj="z", confidence=1.5)

    def test_matches_subject_exact(self):
        fact = Fact(subject="water", predicate="boils at", obj="100c")
        assert fact.matches_subject("water") is True

    def test_matches_subject_alias(self):
        fact = Fact(
            subject="water", predicate="boils at", obj="100c", aliases=["h2o"]
        )
        assert fact.matches_subject("h2o") is True

    def test_does_not_match_unrelated(self):
        fact = Fact(subject="water", predicate="boils at", obj="100c")
        assert fact.matches_subject("fire") is False


class TestFactsDatabase:
    def test_add_and_retrieve(self):
        db = FactsDatabase()
        fact = Fact(subject="test", predicate="is", obj="working")
        db.add_fact(fact)
        results = db.get_facts_for_subject("test")
        assert len(results) == 1
        assert results[0] is fact

    def test_alias_lookup(self):
        db = FactsDatabase()
        fact = Fact(
            subject="hydrogen",
            predicate="symbol is",
            obj="h",
            aliases=["element 1"],
        )
        db.add_fact(fact)
        results = db.get_facts_for_subject("element 1")
        assert len(results) == 1

    def test_size_counts_unique_facts(self):
        db = FactsDatabase()
        fact = Fact(
            subject="x", predicate="p", obj="o", aliases=["alias1", "alias2"]
        )
        db.add_fact(fact)
        assert db.size() == 1  # one fact object, even though indexed 3 times

    def test_search_without_predicate(self):
        db = FactsDatabase()
        db.add_fact(Fact(subject="sun", predicate="is a", obj="star"))
        db.add_fact(Fact(subject="sun", predicate="diameter is", obj="1.4m km"))
        results = db.search("sun")
        assert len(results) == 2

    def test_search_with_predicate_filter(self):
        db = FactsDatabase()
        db.add_fact(Fact(subject="sun", predicate="is a", obj="star"))
        db.add_fact(Fact(subject="sun", predicate="diameter is", obj="1.4m km"))
        results = db.search("sun", predicate="diameter")
        assert len(results) == 1
        assert results[0].obj == "1.4m km"

    def test_load_facts_bulk(self):
        db = FactsDatabase()
        facts = [
            Fact(subject="a", predicate="p", obj="1"),
            Fact(subject="b", predicate="p", obj="2"),
        ]
        db.load_facts(facts)
        assert db.size() == 2


class TestBuildDefaultDatabase:
    def test_returns_database_instance(self):
        db = build_default_database()
        assert isinstance(db, FactsDatabase)

    def test_seed_facts_loaded(self):
        db = build_default_database()
        assert db.size() >= len(SEED_FACTS)

    def test_water_facts_present(self):
        db = build_default_database()
        results = db.search("water")
        assert len(results) >= 1
