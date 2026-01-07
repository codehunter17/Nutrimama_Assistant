import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.perception.nlp import NLPParser


def test_symptom_extraction():
    p = NLPParser()
    r = p.parse("I'm feeling really tired and have a headache today")
    assert "fatigue" in r["symptoms"]
    assert "headache" in r["symptoms"]
    assert r["intent"] == "report_symptom"


def test_feedback_target_and_outcome():
    p = NLPParser()
    ft = p.extract_feedback_target("The spinach suggestion was great and helped a lot")
    assert ft == "spinach"

    hist = p.get_action_history_intent("I tried spinach yesterday and felt great")
    assert hist is not None
    assert hist["action"] == "spinach"
    assert hist["outcome"] == "positive"


def test_nutrition_discussion_intent():
    p = NLPParser()
    r = p.parse("Do you think I need more iron or protein?")
    assert r["intent"] == "ask_question" or r["intent"] == "discuss_nutrition"


def test_request_suggestion_intent():
    p = NLPParser()
    r = p.parse("Can you suggest something for low energy?")
    assert r["intent"] == "request_suggestion"


def test_greeting_intent():
    p = NLPParser()
    r = p.parse("Hi there")
    assert r["intent"] == "greeting"


def test_confidence_bounds():
    p = NLPParser()
    r = p.parse("I feel tired")
    assert 0.5 <= r["confidence"] <= 0.95
