import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.reasoning import ReasoningEngine, ActionType
from app.core.state import MaternalBrainState
from app.core.memory import Memory
from app.core.safety import SafetyChecker


def test_alert_on_critical_nutrient():
    state = MaternalBrainState()
    mem = Memory("user_x")
    safety = SafetyChecker()
    engine = ReasoningEngine()

    # Make iron critically low and confident
    state.nutrition["iron"] = 0.15
    state.confidence_in_state["iron"] = 0.85

    action_type, details, reason = engine.decide(state, mem, safety)
    assert action_type == ActionType.ALERT_MEDICAL
    assert "critical" in reason.lower() or "medical" in reason.lower()


def test_suggests_food_for_low_nutrient():
    state = MaternalBrainState()
    mem = Memory("user_y")
    safety = SafetyChecker()
    engine = ReasoningEngine()

    state.nutrition["iron"] = 0.35
    state.confidence_in_state["iron"] = 0.9

    action_type, details, reason = engine.decide(state, mem, safety)
    assert action_type in (ActionType.SUGGEST_FOOD, ActionType.CHECK_IN)
    if action_type == ActionType.SUGGEST_FOOD:
        assert details["nutrient"] == "iron"
        assert details["food"] in engine._get_foods_for_nutrient("iron")


def test_avoids_failed_suggestions():
    state = MaternalBrainState()
    mem = Memory("user_z")
    safety = SafetyChecker()
    engine = ReasoningEngine()

    # Setup nutrient low
    state.nutrition["iron"] = 0.35
    state.confidence_in_state["iron"] = 0.9

    # Simulate that 'spinach' failed before
    mem.failed_suggestions["spinach"] = 1
    mem.dislikes.add("spinach")

    action_type, details, reason = engine.decide(state, mem, safety)
    if action_type == ActionType.SUGGEST_FOOD:
        assert details["food"] != "spinach"


def test_only_one_action_per_day():
    state = MaternalBrainState()
    mem = Memory("user_q")
    safety = SafetyChecker()
    engine = ReasoningEngine()

    # set recent action date to now
    from datetime import datetime
    state.last_action_date = datetime.utcnow()

    action_type, details, reason = engine.decide(state, mem, safety)
    assert action_type == ActionType.OBSERVE
