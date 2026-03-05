# Ethical Fact Checker Engine

A lightweight Python engine that fact-checks natural-language claims by
matching them against a structured, attributed facts database.

## Design principle – facts over semantics

The engine anchors every verdict to an explicit **Fact** record
(`subject / predicate / object / source / confidence`) rather than
relying on language-model inference or fuzzy semantic similarity.
This keeps results auditable and independently verifiable.

## Verdict taxonomy

| Verdict     | Meaning |
|-------------|---------|
| `TRUE`      | Claim matches a known fact (confidence ≥ 70 %). |
| `LIKELY`    | Moderate confidence match (50 – 70 %). |
| `FALSE`     | Claim directly contradicts a known fact. |
| `UNCERTAIN` | No matching fact found or confidence too low. |
| `REFUSED`   | Claim failed ethical pre-screening. |

## Ethical safeguards

* **Pre-check** – rejects empty, overly long, or otherwise problematic claims.
* **Post-check** – every positive verdict must cite its source; low-confidence
  verdicts are blocked or flagged with a warning.
* **PII redaction** – e-mail addresses and phone numbers are stripped before
  any claim is logged.

## Quick start

```bash
# Install
pip install -e .

# CLI – plain text output
fact-checker "Water boils at 100 degrees Celsius." "The sun is not a star."

# CLI – JSON output
fact-checker --json "DNA stands for deoxyribonucleic acid."
```

## Extending the fact database

```python
from fact_checker import FactCheckerEngine
from fact_checker.facts_db import Fact

engine = FactCheckerEngine()
engine.add_fact(Fact(
    subject="mount fuji",
    predicate="height is",
    obj="3776 metres",
    source="Geospatial Information Authority of Japan",
    confidence=1.0,
    domain="geography",
))
result = engine.check("Mount Fuji height is 3776 metres.")
print(result.verdict)   # TRUE
```

## Running tests

```bash
pip install pytest
pytest
```

---

&copy; 2025 GitHub &bull; [MIT License](https://gh.io/mit)
