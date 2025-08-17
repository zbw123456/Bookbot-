# Language Learning Bookstore Assistant (English dialogue)

## Quickstart
- Python 3.10+
- pip install scikit-learn tabulate
- Run assistant: `python pipeline.py`
- Evaluate: `python evaluate.py`

## Try these
- “I’m learning Italian at A2. I want a reader under €20.”
- “Add 1 to cart.”
- “Show my cart.”
- “Checkout.”
- “Courier delivery.”
- “Ship to 221B Baker Street, London.”
- “Pay with Visa.”

## Files
- pipeline.py: interactive loop (NLU → DM → NLG)
- utils.py: rule-based NLU, DM policy, NLG, retrieval/ranking
- catalog.json: sample catalog across languages × CEFR × genres
- evaluate.py: intent/slot/DM evaluation
- tests/test_intents.jsonl: small test suite
- REPORT.md: 4–5 page report + appendices
