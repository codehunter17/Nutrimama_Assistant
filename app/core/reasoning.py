# app/core/reasoning.py
"""
Reasoning Engine: The actual brain that picks ONE action per day.

NOT a classifier. NOT a neural network. Pure logic:
1. Check safety (hard stops)
2. Check memory (don't repeat failures)
3. Check state (what's the real problem?)
4. Pick ONE action (not overwhelming)

Key: Slow, deliberate, explainable.
"""

from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Types of actions the system can take."""
    SUGGEST_FOOD = "suggest_food"
    SUGGEST_WATER = "suggest_water"
    SUGGEST_REST = "suggest_rest"
    ASK_QUESTION = "ask_question"
    OBSERVE = "observe"
    ALERT_MEDICAL = "alert_medical"
    CHECK_IN = "check_in"


class ReasoningEngine:
    """
    Decides what action to take based on state + memory + safety.
    """

    # Nutrient thresholds for action
    CRITICAL_THRESHOLD = 0.25
    LOW_THRESHOLD = 0.40
    ADEQUATE_THRESHOLD = 0.70

    def __init__(self):
        self.last_action_time: Optional[datetime] = None
        self.decisions_log = []

    def decide(
        self,
        state,  # MaternalBrainState
        memory,  # Memory
        safety,  # SafetyChecker
    ) -> Tuple[ActionType, Dict, str]:
        """
        Main decision function. Picks ONE action.
        
        Returns:
            (action_type, action_details, reasoning)
        """

        # Step 1: Check for critical alerts
        alert = safety.check_state_for_alerts(state)
        if alert or safety.get_alerts():
            return (
                ActionType.ALERT_MEDICAL,
                {"alert": alert or safety.get_alerts()[0]},
                "Critical state detected. Medical consultation needed."
            )

        # Step 2: Check for critical symptoms
        if state.symptoms:
            for symptom in state.symptoms:
                is_safe, msg = safety.check_critical_symptom(symptom)
                if not is_safe:
                    return (
                        ActionType.ALERT_MEDICAL,
                        {"symptom": symptom, "alert": msg},
                        f"Critical symptom: {symptom}"
                    )

        # Step 3: Should we even take action today?
        if not self._should_take_action_today(state, memory):
            return (
                ActionType.OBSERVE,
                {"reason": "No urgent action needed"},
                "System observing. No action needed today."
            )

        # Step 4: Identify most pressing nutrient
        pressing_nutrient = self._find_pressing_nutrient(state)
        if pressing_nutrient:
            action_type, details, reason = self._suggest_for_nutrient(
                pressing_nutrient, state, memory, safety
            )
            if action_type != ActionType.OBSERVE:
                self._record_decision(action_type, details, reason)
                return (action_type, details, reason)

        # Step 5: If no nutrient action, check lifestyle
        action_type, details, reason = self._suggest_lifestyle(state, memory, safety)
        if action_type != ActionType.OBSERVE:
            self._record_decision(action_type, details, reason)
            return (action_type, details, reason)

        # Step 6: Default: check-in to gather info
        return (
            ActionType.CHECK_IN,
            {"question": "How are you feeling today?"},
            "Regular check-in to understand current state."
        )

    def _should_take_action_today(self, state, memory) -> bool:
        """
        Have we already acted today? Don't spam.
        Only take action once per day, unless critical.
        """
        if state.last_action_date is None:
            return True

        time_since_last = datetime.utcnow() - state.last_action_date
        return time_since_last > timedelta(hours=20)

    def _find_pressing_nutrient(self, state) -> Optional[str]:
        """
        Which nutrient is most pressing?

        Priority (deterministic):
        1. Any nutrient below CRITICAL_THRESHOLD with high confidence (sorted lowest first)
        2. Any nutrient between CRITICAL and LOW thresholds with high confidence (sorted lowest first)
        3. Return None if all adequate
        """
        items = [
            (n, v) for n, v in state.nutrition.items()
            if state.confidence_in_state.get(n, 0.0) > 0.7
        ]
        if not items:
            return None

        # Consider critical nutrients first (deterministic by value)
        critical = sorted(
            [(n, v) for n, v in items if v < self.CRITICAL_THRESHOLD],
            key=lambda x: x[1]
        )
        if critical:
            return critical[0][0]

        # Then low nutrients
        low = sorted(
            [(n, v) for n, v in items if self.CRITICAL_THRESHOLD <= v < self.LOW_THRESHOLD],
            key=lambda x: x[1]
        )
        if low:
            return low[0][0]

        return None

    def _suggest_for_nutrient(
        self,
        nutrient: str,
        state,
        memory,
        safety
    ) -> Tuple[ActionType, Dict, str]:
        """
        Suggest a food to address this nutrient.
        Uses memory to pick foods that worked before. Tries candidates
        iteratively and performs safety checks without recursion to avoid
        potential infinite loops.
        """
        # Get foods that previously worked for this nutrient (sorted by success)
        successful = memory.get_successful_patterns()
        foods_for_nutrient = self._get_foods_for_nutrient(nutrient)

        # Build deterministic candidate list: successful first (by count desc), then remaining foods
        successful_foods = [f for f, _ in successful if f in foods_for_nutrient]
        remaining_foods = [f for f in foods_for_nutrient if f not in successful_foods]
        candidates = successful_foods + remaining_foods

        for food in candidates:
            # Respect memory constraints
            if memory.should_avoid_suggestion(food):
                continue
            if memory.was_recently_suggested(food):
                continue

            # Safety check
            is_safe, reason = safety.check_food_safety(
                food, state.pregnancy_stage, state.breastfeeding
            )
            if not is_safe:
                logger.warning(f"Food {food} failed safety check: {reason}")
                continue

            # Found a safe candidate
            return (
                ActionType.SUGGEST_FOOD,
                {
                    "nutrient": nutrient,
                    "food": food,
                    "reason": f"Your {nutrient} levels seem low"
                },
                f"Suggesting {food} to address {nutrient}"
            )

        # No safe/valid candidates found
        return (
            ActionType.CHECK_IN,
            {"question": f"How have you been feeling about your {nutrient} intake?"},
            f"No safe/valid food candidates for {nutrient}. Need user feedback."
        )

    def _suggest_lifestyle(
        self,
        state,
        memory,
        safety
    ) -> Tuple[ActionType, Dict, str]:
        """
        Suggest lifestyle changes if nutrients are adequate.
        """
        if state.energy_level < 0.4 and state.sleep_quality < 0.5:
            return (
                ActionType.SUGGEST_REST,
                {"suggestion": "Try to get more sleep tonight"},
                "Low energy and poor sleep detected"
            )

        if state.hydration_level < 0.4:
            return (
                ActionType.SUGGEST_WATER,
                {"glasses": 3, "timing": "throughout the day"},
                "Hydration levels low"
            )

        return (ActionType.OBSERVE, {}, "No urgent action")

    def _get_foods_for_nutrient(self, nutrient: str) -> list:
        """
        Return list of foods that provide this nutrient.
        This is static knowledge, not learned.
        """
        foods_map = {
            "iron": ["spinach", "red_meat", "lentils", "fortified_cereal", "pumpkin_seeds"],
            "protein": ["eggs", "chicken", "yogurt", "milk", "beans", "nuts", "fish"],
            "calcium": ["milk", "yogurt", "cheese", "fortified_milk", "dark_leafy_greens"],
            "folic": ["spinach", "broccoli", "lentils", "asparagus", "fortified_grains"],
            "vitamin_b12": ["eggs", "milk", "cheese", "meat", "fortified_cereals"],
            "iodine": ["iodized_salt", "fish", "seaweed", "eggs", "dairy"]
        }
        return foods_map.get(nutrient, [])

    def _record_decision(self, action_type: ActionType, details: Dict, reason: str):
        """Log the decision for analysis."""
        decision = {
            "timestamp": datetime.utcnow().isoformat(),
            "action_type": action_type.value,
            "details": details,
            "reason": reason
        }
        self.decisions_log.append(decision)
        logger.info(f"Decision: {action_type.value} - {reason}")

    def get_decisions_log(self) -> list:
        """Return all decisions made."""
        return self.decisions_log

    def __repr__(self) -> str:
        return f"ReasoningEngine(decisions={len(self.decisions_log)})"
