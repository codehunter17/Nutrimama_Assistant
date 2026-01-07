# app/core/state.py
"""
MaternalBrainState: The belief system of Nutrimama.

This is NOT a data container. This is how the system BELIEVES
the mother's state is, based on:
  - Past observations (memory)
  - ML signals (damped, not direct)
  - User feedback (ground truth)

Key principle: State changes slowly, like human belief formation.
ML signals are merged in with a dampening factor.
"""

from datetime import datetime
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class MaternalBrainState:
    """
    Represents the internal belief about the mother's
    nutritional and physical state.
    
    Values are 0-1 tendencies, NOT medical numbers.
    State updates slowly to avoid jitter from model noise.
    """

    # Dampening factor: How much to trust new signals vs. keep old belief
    # 0.7 = keep 70% of old belief, add 30% of new signal
    DAMPENING_FACTOR = 0.7
    
    # Confidence threshold: Only act if we're confident in our belief
    MIN_CONFIDENCE_TO_ACT = 0.7

    def __init__(
        self,
        pregnancy_stage: Optional[str] = None,
        breastfeeding: bool = False,
        age: Optional[int] = None
    ):
        """
        Initialize maternal brain state.
        
        Args:
            pregnancy_stage: "planning", "first_trimester", "second_trimester", 
                           "third_trimester", or None if not pregnant
            breastfeeding: Is mother currently breastfeeding?
            age: Mother's age (optional, affects nutritional needs)
        """
        # Nutritional belief (0-1: how adequate is this nutrient?)
        self.nutrition: Dict[str, float] = {
            "iron": 0.5,
            "protein": 0.5,
            "calcium": 0.5,
            "folic": 0.5,
            "vitamin_b12": 0.5,
            "iodine": 0.5
        }

        # Physical state beliefs
        self.energy_level = 0.5
        self.hydration_level = 0.5
        self.sleep_quality = 0.5
        self.stress_level = 0.5

        # Contextual information
        self.pregnancy_stage = pregnancy_stage  # Changes slowly
        self.breastfeeding = breastfeeding
        self.age = age

        # Symptoms reported by user (ground truth, not belief)
        self.symptoms: set = set()

        # Confidence in our beliefs (0-1: how sure are we?)
        self.confidence_in_state: Dict[str, float] = {
            nutrient: 0.5 for nutrient in self.nutrition
        }

        # Action history
        self.last_action: Optional[str] = None
        self.last_action_date: Optional[datetime] = None

        # Metadata
        self.created_at = datetime.utcnow()
        self.last_updated = datetime.utcnow()
        self.update_count = 0

    def apply_ml_signal(
        self,
        nutrient: str,
        ml_prediction: float,
        model_confidence: float
    ) -> None:
        """
        Incorporate ML model signal into state belief.
        
        This is NOT direct assignment. We dampen the signal to avoid
        jitter from model noise or retraining.
        
        Formula:
            new_belief = DAMPENING * old_belief + (1-DAMPENING) * ml_prediction
        
        Args:
            nutrient: Which nutrient to update
            ml_prediction: Raw model output (0-1)
            model_confidence: How accurate is this model? (0-1)
        """
        if nutrient not in self.nutrition:
            logger.warning(f"Unknown nutrient: {nutrient}")
            return

        # Clamp prediction to valid range
        prediction = max(0.0, min(1.0, ml_prediction))

        # Apply dampening: slow change to avoid jitter
        old_belief = self.nutrition[nutrient]
        new_belief = (
            self.DAMPENING_FACTOR * old_belief +
            (1.0 - self.DAMPENING_FACTOR) * prediction
        )

        self.nutrition[nutrient] = new_belief

        # Update confidence based on model accuracy
        # If model is confident AND consistent, boost our confidence
        self.confidence_in_state[nutrient] = (
            0.5 * self.confidence_in_state[nutrient] +
            0.5 * model_confidence
        )

        self.last_updated = datetime.utcnow()
        self.update_count += 1

        logger.debug(
            f"Updated {nutrient}: {old_belief:.2f} → {new_belief:.2f} "
            f"(confidence: {self.confidence_in_state[nutrient]:.2f})"
        )

    def apply_user_feedback(self, nutrient: str, direction: str) -> None:
        """
        User says "I feel tired" or "I feel better after eating spinach".
        This is GROUND TRUTH. Update state AND boost confidence.
        
        Args:
            nutrient: Which nutrient to adjust
            direction: "increase", "decrease", or "stable"
        """
        if nutrient not in self.nutrition:
            logger.warning(f"Unknown nutrient: {nutrient}")
            return

        delta = {
            "increase": 0.05,
            "decrease": -0.05,
            "stable": 0.0
        }.get(direction, 0.0)

        old_belief = self.nutrition[nutrient]
        new_belief = max(0.0, min(1.0, old_belief + delta))

        self.nutrition[nutrient] = new_belief

        # User feedback is VERY reliable, boost confidence significantly
        self.confidence_in_state[nutrient] = min(
            1.0,
            self.confidence_in_state[nutrient] + 0.15
        )

        self.last_updated = datetime.utcnow()

        logger.info(
            f"User feedback: {nutrient} {direction} "
            f"({old_belief:.2f} → {new_belief:.2f})"
        )

    def report_symptom(self, symptom: str) -> None:
        """
        User reports a symptom: "I'm tired", "I have headache", etc.
        Store it. This helps reasoning figure out what happened.
        
        Args:
            symptom: Symptom description
        """
        self.symptoms.add(symptom.lower())
        self.last_updated = datetime.utcnow()
        logger.info(f"Symptom reported: {symptom}")

    def clear_symptoms(self) -> None:
        """Clear reported symptoms (after taking action, symptoms may resolve)."""
        self.symptoms.clear()

    def is_nutrient_critical(self, nutrient: str, threshold: float = 0.3) -> bool:
        """
        Is this nutrient critically low?
        Only return True if BOTH belief is low AND confidence is high.
        """
        if nutrient not in self.nutrition:
            return False

        belief = self.nutrition[nutrient]
        confidence = self.confidence_in_state[nutrient]

        is_critical = belief < threshold and confidence > self.MIN_CONFIDENCE_TO_ACT
        return is_critical

    def is_nutrient_adequate(self, nutrient: str, threshold: float = 0.7) -> bool:
        """Is this nutrient adequately present?"""
        if nutrient not in self.nutrition:
            return False
        return self.nutrition[nutrient] >= threshold

    def get_state_summary(self) -> Dict:
        """
        Get a human-readable summary of current state.
        No scores shown to user, but useful for logging/debugging.
        """
        return {
            "pregnancy_stage": self.pregnancy_stage,
            "breastfeeding": self.breastfeeding,
            "nutrition": self.nutrition.copy(),
            "confidence": self.confidence_in_state.copy(),
            "energy_level": self.energy_level,
            "hydration_level": self.hydration_level,
            "sleep_quality": self.sleep_quality,
            "stress_level": self.stress_level,
            "symptoms": list(self.symptoms),
            "last_action": self.last_action,
            "last_action_date": self.last_action_date,
            "updated_at": self.last_updated.isoformat(),
            "total_updates": self.update_count
        }

    def __repr__(self) -> str:
        nutrients_str = ", ".join(
            f"{k}={v:.2f}" for k, v in self.nutrition.items()
        )
        return (
            f"MaternalBrainState(stage={self.pregnancy_stage}, "
            f"energy={self.energy_level:.2f}, {nutrients_str})"
        )

    def to_dict(self) -> Dict:
        """Serialize state to a plain dict for persistence."""
        return {
            "nutrition": self.nutrition.copy(),
            "energy_level": self.energy_level,
            "hydration_level": self.hydration_level,
            "sleep_quality": self.sleep_quality,
            "stress_level": self.stress_level,
            "pregnancy_stage": self.pregnancy_stage,
            "breastfeeding": self.breastfeeding,
            "age": self.age,
            "symptoms": list(self.symptoms),
            "confidence_in_state": self.confidence_in_state.copy(),
            "last_action": self.last_action,
            "last_action_date": self.last_action_date.isoformat() if self.last_action_date else None,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "update_count": self.update_count
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "MaternalBrainState":
        """Deserialize state from dict."""
        obj = cls(pregnancy_stage=data.get("pregnancy_stage"), breastfeeding=data.get("breastfeeding", False), age=data.get("age"))
        obj.nutrition = data.get("nutrition", obj.nutrition)
        obj.energy_level = data.get("energy_level", obj.energy_level)
        obj.hydration_level = data.get("hydration_level", obj.hydration_level)
        obj.sleep_quality = data.get("sleep_quality", obj.sleep_quality)
        obj.stress_level = data.get("stress_level", obj.stress_level)
        obj.symptoms = set(data.get("symptoms", []))
        obj.confidence_in_state = data.get("confidence_in_state", obj.confidence_in_state)
        obj.last_action = data.get("last_action")
        import datetime

        lad = data.get("last_action_date")
        if lad:
            try:
                obj.last_action_date = datetime.datetime.fromisoformat(lad)
            except Exception:
                obj.last_action_date = None

        obj.created_at = datetime.datetime.fromisoformat(data.get("created_at")) if data.get("created_at") else obj.created_at
        obj.last_updated = datetime.datetime.fromisoformat(data.get("last_updated")) if data.get("last_updated") else obj.last_updated
        obj.update_count = data.get("update_count", obj.update_count)
        return obj
