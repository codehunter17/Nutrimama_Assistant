import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.safety import SafetyChecker


def test_check_food_safety_pregnancy():
    s = SafetyChecker()
    ok, reason = s.check_food_safety("raw_milk", pregnancy_stage="first_trimester")
    assert not ok
    assert "not safe" in reason.lower()


def test_check_medication_safety():
    s = SafetyChecker()
    ok, reason = s.check_medication_safety("aspirin")
    assert not ok
    assert "cannot suggest" in reason.lower() or "not authorized" in reason.lower()


def test_check_critical_symptom():
    s = SafetyChecker()
    ok, alert = s.check_critical_symptom("severe_bleeding")
    assert not ok
    assert "critical" in alert.lower() or "alert" in alert.lower()
    assert len(s.get_alerts()) > 0
