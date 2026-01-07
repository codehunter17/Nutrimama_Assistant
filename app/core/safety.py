# app/core/safety.py
"""
Safety: Hard boundaries that NEVER get crossed.

These are NOT learned. NOT flexible. NOT negotiable.
Embedded domain knowledge about pregnancy, nutrition, and maternal health.

If any safety check fails, system stops and alerts medical professional.
"""

from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class SafetyChecker:
    """
    Enforces non-negotiable safety boundaries.
    
    Rules:
    1. Never prescribe medicine
    2. Never suggest medical treatment
    3. Never ignore critical symptoms
    4. Never suggest unsafe foods during pregnancy/breastfeeding
    5. Never ignore allergies
    """

    # Foods absolutely unsafe during pregnancy/breastfeeding
    UNSAFE_FOODS_PREGNANCY = {
        "raw_milk",
        "unpasteurized_cheese",
        "raw_eggs",
        "high_mercury_fish",
        "pâté",
        "undercooked_meat",
        "alcohol",
        "raw_sprouts",
        "unwashed_vegetables"
    }

    # Foods that may decrease milk supply during breastfeeding
    UNSAFE_FOODS_BREASTFEEDING = {
        "sage",
        "peppermint_tea_excess",
        "parsley_excess",
        "alcohol"
    }

    # Medications NEVER to suggest
    UNSAFE_MEDICATIONS = {
        "aspirin",
        "ibuprofen",
        "naproxen",
        "warfarin",
        "retinol_high_dose",
        "methotrexate",
        "lisinopril",
        "ace_inhibitors"
    }

    # Critical symptoms that require immediate medical attention
    CRITICAL_SYMPTOMS = {
        "severe_bleeding",
        "severe_abdominal_pain",
        "sudden_severe_headache",
        "vision_changes",
        "seizures",
        "loss_of_consciousness",
        "severe_allergic_reaction"
    }

    # Warning symptoms to monitor
    WARNING_SYMPTOMS = {
        "persistent_vomiting",
        "severe_dizziness",
        "swelling_with_headache",
        "chest_pain",
        "shortness_of_breath"
    }

    def __init__(self):
        self.violations = []
        self.alerts = []

    def check_food_safety(
        self,
        food: str,
        pregnancy_stage: Optional[str] = None,
        breastfeeding: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Is it safe to suggest this food?
        
        Returns:
            (is_safe, reason_if_unsafe)
        """
        food_lower = food.lower()

        if pregnancy_stage and pregnancy_stage != "planning":
            if food_lower in self.UNSAFE_FOODS_PREGNANCY:
                reason = f"⚠️ {food} is not safe during pregnancy"
                self.violations.append(reason)
                return False, reason

        if breastfeeding:
            if food_lower in self.UNSAFE_FOODS_BREASTFEEDING:
                reason = f"⚠️ {food} may affect milk supply during breastfeeding"
                self.violations.append(reason)
                return False, reason

        return True, None

    def check_medication_safety(self, medication: str) -> Tuple[bool, Optional[str]]:
        """
        Is it safe to suggest this medication?
        
        For pregnant/nursing women, most medications are risky.
        System should NEVER suggest medications - only food/lifestyle.
        """
        med_lower = medication.lower()

        if med_lower in self.UNSAFE_MEDICATIONS:
            reason = f"SAFETY VIOLATION: Cannot suggest {medication} to pregnant women"
            self.violations.append(reason)
            logger.critical(reason)
            return False, reason

        # General rule: don't suggest ANY medication
        reason = "System is not authorized to suggest medications. Recommend consulting doctor."
        logger.warning(f"Medication suggestion attempt: {medication}")
        return False, reason

    def check_critical_symptom(self, symptom: str) -> Tuple[bool, Optional[str]]:
        """
        Is the user reporting a critical symptom?
        
        If yes, system must alert and NOT take routine actions.
        """
        symptom_lower = symptom.lower()

        if symptom_lower in self.CRITICAL_SYMPTOMS:
            alert = f"🚨 CRITICAL: User reported {symptom}. ALERT MEDICAL PROFESSIONAL."
            self.alerts.append(alert)
            logger.critical(alert)
            return False, alert

        if symptom_lower in self.WARNING_SYMPTOMS:
            alert = f"⚠️ WARNING: User reported {symptom}. Monitor and suggest medical consultation."
            self.alerts.append(alert)
            logger.warning(alert)
            return True, alert  # Not critical, but warning

        return True, None

    def check_suggestion_validity(
        self,
        suggestion: str,
        suggestion_type: str,  # "food", "lifestyle", "water", "rest"
        pregnancy_stage: Optional[str] = None,
        breastfeeding: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Is this a valid suggestion?
        
        Args:
            suggestion: What are we suggesting?
            suggestion_type: Category of suggestion
            pregnancy_stage: Current pregnancy stage
            breastfeeding: Is user breastfeeding?
            
        Returns:
            (is_valid, reason_if_invalid)
        """
        # Rule 1: No medical advice
        medical_keywords = ["treat", "cure", "disease", "infection", "medicine"]
        if any(kw in suggestion.lower() for kw in medical_keywords):
            reason = "❌ Cannot suggest medical treatment. Recommend doctor consultation."
            self.violations.append(reason)
            return False, reason

        # Rule 2: Food suggestions must be food-safe
        if suggestion_type == "food":
            return self.check_food_safety(suggestion, pregnancy_stage, breastfeeding)

        # Rule 3: Lifestyle suggestions must be reasonable
        if suggestion_type == "lifestyle":
            # Don't suggest strenuous exercise to heavily pregnant women
            if "intense exercise" in suggestion.lower() and pregnancy_stage == "third_trimester":
                reason = "Intense exercise not recommended in third trimester"
                self.violations.append(reason)
                return False, reason

        return True, None

    def check_state_for_alerts(self, state) -> Optional[str]:
        """
        Look at the entire state and check for concerning patterns.
        
        Example: If iron is critically low for weeks, suggest blood test.
        """
        alerts = []

        # Check for critically low nutrients
        critical_nutrients = [
            n for n, v in state.nutrition.items()
            if v < 0.2 and state.confidence_in_state[n] > 0.8
        ]

        if critical_nutrients:
            alert = (
                f"Multiple critical nutrients detected: {', '.join(critical_nutrients)}. "
                f"Suggest blood test and doctor consultation."
            )
            alerts.append(alert)

        # Check for persistent fatigue with poor sleep
        if state.energy_level < 0.3 and state.sleep_quality < 0.3:
            alert = "Persistent fatigue with poor sleep. Suggest doctor consultation."
            alerts.append(alert)

        if alerts:
            combined = " | ".join(alerts)
            self.alerts.append(combined)
            logger.warning(f"State-based alert: {combined}")
            return combined

        return None

    def get_violations(self):
        """Return all safety violations."""
        return self.violations

    def get_alerts(self):
        """Return all alerts."""
        return self.alerts

    def clear_violations(self):
        """Clear recorded violations."""
        self.violations = []

    def clear_alerts(self):
        """Clear recorded alerts."""
        self.alerts = []

    def is_prompt_safe(self, prompt: str) -> bool:
        """Quick heuristic to ensure prompts sent to LLM won't request medical advice
        or contain risky instructions. This is intentionally conservative."""
        lower = prompt.lower()
        medical_kws = ["treat", "cure", "medicine", "dose", "prescribe", "diagnos"]
        if any(kw in lower for kw in medical_kws):
            return False
        return True

    def __repr__(self) -> str:
        return f"SafetyChecker(violations={len(self.violations)}, alerts={len(self.alerts)})"
