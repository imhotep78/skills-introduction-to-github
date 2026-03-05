"""Tests for the CLI interface."""

import json
import pytest
from fact_checker.cli import main


class TestCliBasic:
    def test_true_claim_exit_zero(self):
        code = main(["Water boils at 100 degrees Celsius."])
        assert code == 0

    def test_false_claim_exit_nonzero(self):
        code = main(["The sun is not a star."])
        assert code == 1

    def test_multiple_claims_all_true(self):
        code = main([
            "Water boils at 100 degrees Celsius.",
            "The sun is a star.",
        ])
        assert code == 0

    def test_multiple_claims_one_false(self):
        code = main([
            "Water boils at 100 degrees Celsius.",
            "The sun is not a star.",
        ])
        assert code == 1

    def test_refused_claim_exit_nonzero(self):
        code = main([""])
        assert code == 1


class TestCliJsonOutput:
    def test_json_flag_produces_array(self, capsys):
        code = main(["--json", "Water boils at 100 degrees Celsius."])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["verdict"] == "TRUE"

    def test_json_keys_present(self, capsys):
        main(["--json", "The sun is a star."])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "verdict" in data[0]
        assert "explanation" in data[0]
        assert "source" in data[0]
        assert "confidence" in data[0]
