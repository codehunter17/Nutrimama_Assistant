import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.interface.responder import Responder
from app.core.state import MaternalBrainState


def test_structure_suggest_food_hinglish():
    r = Responder()
    state = MaternalBrainState()
    msg = r.respond_to_action("suggest_food", {"food": "palak", "nutrient": "iron"}, state=state, user_message="Aaj main palak try kiya")
    # Should have at least 3 lines separated by blank lines
    parts = msg.split('\n\n')
    assert len(parts) >= 3
    assert "Sun" in parts[0] or "Sun na" in parts[0] or "Hey" in parts[0]


def test_alert_medical_family_tone():
    r = Responder()
    msg = r.respond_to_action("alert_medical", {"alert": "severe_bleeding"}, user_message="I'm bleeding a lot")
    parts = msg.split('\n\n')
    assert "doctor" in msg.lower() or "emergency" in msg.lower()
    assert "Sun" in parts[0] or "Hey" in parts[0]


def test_no_action_support_only():
    r = Responder()
    msg = r.respond_to_action("observe", {}, user_message="ok")
    parts = msg.split('\n\n')
    # No suggestion line for observe
    assert len(parts) == 2 or len(parts) == 3
    assert any(x in msg for x in ["Koi baat", "I'm here", "Im here", "Im here"]) or "I'm here" in msg or "Im here" in msg


def test_avoid_medical_suggestion():
    r = Responder()
    state = MaternalBrainState()
    # Force unsafe suggestion by using medication word
    msg = r.respond_to_action("suggest_food", {"food": "aspirin", "nutrient": "pain"}, state=state, user_message="I have pain")
    assert "doctor" in msg.lower() or "check" in msg.lower() or "surakshit" in msg.lower()
