import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.state import MaternalBrainState


def test_state_serialization_roundtrip():
    s = MaternalBrainState(pregnancy_stage="second_trimester", breastfeeding=False, age=32)
    s.nutrition["iron"] = 0.23
    s.confidence_in_state["iron"] = 0.82
    s.report_symptom("tired")
    s.last_action = "suggest_spinach"

    data = s.to_dict()
    s2 = MaternalBrainState.from_dict(data)

    assert s2.pregnancy_stage == s.pregnancy_stage
    assert s2.nutrition["iron"] == s.nutrition["iron"]
    assert s2.confidence_in_state["iron"] == s.confidence_in_state["iron"]
    assert "tired" in s2.symptoms
    assert s2.last_action == s.last_action
