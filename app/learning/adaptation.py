# app/learning/adaptation.py
"""
Adaptation: How Nutrimama learns from outcomes WITHOUT retraining models.

Key insight: User-specific learning is FAST and SAFE.
We don't retrain global ML models (expensive, risky).
We learn what works for THIS user (cheap, personal).

Mechanism:
1. Action suggested (e.g., spinach)
2. Outcome reported (user felt better / worse / neutral)
3. Memory updated (this worked / didn't work for this user)
4. State adjusted based on outcomes
5. Future decisions avoid what failed, repeat what worked
"""

from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class AdaptationEngine:
    """
    Fast learning from user feedback.
    Does NOT retrain ML models. Updates state and memory only.
    """

    def __init__(self, memory):
        """
        Args:
            memory: Memory object to learn from
        """
        self.memory = memory
        self.adaptation_log = []

    def learn_from_outcome(
        self,
        action_id: str,
        outcome: str,  # "positive", "negative", "neutral"
        outcome_text: Optional[str] = None,
        state=None  # MaternalBrainState to update
    ) -> bool:
        """
        Process user feedback on an action.
        
        This is the core learning mechanism.
        
        Args:
            action_id: Which action are we evaluating?
            outcome: How did the user respond?
            outcome_text: What did they say?
            state: Optional state to update based on outcome
            
        Returns:
            True if successfully learned
        """
        # Step 1: Record outcome in memory
        success = self.memory.record_outcome(action_id, outcome, outcome_text)
        if not success:
            logger.warning(f"Failed to record outcome for action {action_id}")
            return False

        # Step 2: Update state if provided
        if state:
            self._update_state_from_outcome(action_id, outcome, state)

        # Step 3: Log the adaptation
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action_id": action_id,
            "outcome": outcome,
            "outcome_text": outcome_text
        }
        self.adaptation_log.append(log_entry)

        logger.info(f"Learned: {action_id} → {outcome}")
        return True

    def _update_state_from_outcome(self, action_id: str, outcome: str, state):
        """
        Update state based on action outcome.
        
        Example:
        - Suggested spinach (targets iron)
        - User reported feeling better
        - Increase iron belief + increase confidence
        """
        action = self.memory.get_action_by_id(action_id)
        if not action:
            return

        nutrients_targeted = action.nutrients_targeted

        if outcome == "positive":
            # Action helped! Boost confidence in targeted nutrients
            for nutrient in nutrients_targeted:
                state.confidence_in_state[nutrient] = min(
                    1.0,
                    state.confidence_in_state[nutrient] + 0.1
                )
                # Slightly boost nutrient belief
                state.nutrition[nutrient] = min(
                    1.0,
                    state.nutrition[nutrient] + 0.05
                )

        elif outcome == "negative":
            # Action didn't help. Reduce confidence in our assessment.
            for nutrient in nutrients_targeted:
                state.confidence_in_state[nutrient] = max(
                    0.3,  # Don't go too low
                    state.confidence_in_state[nutrient] - 0.1
                )

        state.last_updated = datetime.utcnow()
        logger.debug(f"State updated based on outcome: {outcome}")

    def detect_pattern_failure(self) -> Optional[Dict]:
        """
        Detect when we're repeatedly failing at something.
        
        Example: "We've suggested spinach 4 times, maa rejected it 3 times"
        
        Returns:
            {"suggestion": "spinach", "failure_rate": 0.75, "should_stop": True}
            or None if no pattern failure detected
        """
        failed = self.memory.get_failed_patterns()

        for suggestion, failure_count in failed:
            # Find how many times we suggested this
            times_suggested = sum(
                1 for action in self.memory.actions
                if suggestion.lower() in action.action_text.lower()
            )

            if times_suggested >= 3:  # Only after multiple attempts
                failure_rate = failure_count / times_suggested
                
                if failure_rate > 0.5:  # More than 50% failure
                    return {
                        "suggestion": suggestion,
                        "failure_rate": failure_rate,
                        "times_suggested": times_suggested,
                        "should_stop": True
                    }

        return None

    def detect_successful_pattern(self) -> Optional[Dict]:
        """
        Detect when something is consistently working.
        
        Example: "Spinach worked 4 out of 5 times for iron"
        
        Returns:
            {"suggestion": "spinach", "success_rate": 0.8, "should_repeat": True}
        """
        successful = self.memory.get_successful_patterns()

        for suggestion, success_count in successful:
            # Find total suggestions
            times_suggested = sum(
                1 for action in self.memory.actions
                if suggestion.lower() in action.action_text.lower()
            )

            if times_suggested >= 2:  # After a couple of tries
                success_rate = success_count / times_suggested
                
                if success_rate > 0.7:  # More than 70% success
                    return {
                        "suggestion": suggestion,
                        "success_rate": success_rate,
                        "times_suggested": times_suggested,
                        "should_repeat": True
                    }

        return None

    def get_learning_insights(self) -> Dict:
        """
        Generate insights about what the system has learned.
        """
        insights = {
            "successful_patterns": dict(self.memory.get_successful_patterns()),
            "failed_patterns": dict(self.memory.get_failed_patterns()),
            "pattern_failure": self.detect_pattern_failure(),
            "pattern_success": self.detect_successful_pattern(),
            "dislikes": list(self.memory.dislikes),
            "allergies": list(self.memory.allergies),
            "total_actions_taken": len(self.memory.actions),
            "successful_actions": len([a for a in self.memory.actions if a.outcome == "positive"]),
            "failed_actions": len([a for a in self.memory.actions if a.outcome == "negative"]),
        }
        return insights

    def should_retrain_ml_model(self) -> bool:
        """
        Decide if ML models need retraining.
        
        This is EXPENSIVE, so we're very selective.
        
        Triggers:
        - Concept drift detected (data patterns changed)
        - Model predictions frequently wrong
        - Too many days since last training
        """
        # For now, return False (no automatic retraining)
        # This would integrate with model registry and monitoring
        return False

    def __repr__(self) -> str:
        insights = self.get_learning_insights()
        return (
            f"AdaptationEngine(learned={insights['total_actions_taken']}, "
            f"success_rate={insights['successful_actions']}/{insights['total_actions_taken']})"
        )
