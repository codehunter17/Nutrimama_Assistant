# Perception (NLP) — Manual & Technical Notes

## Overview
The perception layer uses a lightweight, rule-based `NLPParser` (in `app/perception/nlp.py`) to extract structured signals from user text. This keeps the system fast, explainable, and privacy-preserving (no external services required).

## What it extracts
- Symptoms (mapped to canonical symptom names)
- Sentiment (positive / negative / neutral)
- Nutrients mentioned (iron, protein, calcium, folic, vitamin_b12, iodine)
- Food mentions (multi-word supported) and feedback targets
- Intent categories: `report_symptom`, `give_feedback_positive`, `give_feedback_negative`, `request_suggestion`, `ask_question`, `discuss_nutrition`, `greeting`, `general_chat`
- Confidence score (0.5–0.95 for rule-based heuristics)

## Privacy Notes
- No PII extraction. Avoid adding any feature that extracts names, locations, or sensitive identifiers.
- All parsing is local — no network calls.

## Testing
- Unit tests: `tests/test_nlp.py` covers symptoms, feedback extraction, intents, and confidence bounds.

## Extensibility
- Add domain-specific keyword lists in `NLPParser.NUTRIENT_KEYWORDS`.
- Keep intent rules conservative. If uncertain, prefer `ask_question` or `general_chat` rather than making health claims.
