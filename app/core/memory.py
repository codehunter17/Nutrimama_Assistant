# app/core/memory.py
"""
Memory: Nutrimama's ground truth log of what actually happened.

NOT trained models. NOT predictions. Just facts:
- "On Jan 5, I suggested spinach, maa tried it, felt better"
- "On Jan 6, I suggested milk, maa said it upset her stomach"

This is how the system learns WITHOUT retraining models.
User-specific, fast, and explainable.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Literal
from dataclasses import dataclass, field, asdict
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class Action:
    """
    A single action taken by the system and its outcome.
    """
    action_id: str  # Unique identifier
    timestamp: datetime
    action_type: str  # "suggest_food", "ask_question", "observe", etc.
    action_text: str  # What was actually suggested/asked
    reason: str  # Why did we pick this action?
    nutrients_targeted: List[str] = field(default_factory=list)
    
    # Outcome - recorded after user response
    outcome: Optional[Literal["positive", "negative", "neutral", "unknown"]] = None
    outcome_text: Optional[str] = None  # User's feedback
    outcome_recorded_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """Serialize for storage."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        if self.outcome_recorded_at:
            data["outcome_recorded_at"] = self.outcome_recorded_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "Action":
        """Deserialize from storage."""
        if isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        if data.get("outcome_recorded_at") and isinstance(data["outcome_recorded_at"], str):
            data["outcome_recorded_at"] = datetime.fromisoformat(data["outcome_recorded_at"])
        return cls(**data)


class Memory:
    """
    User-specific memory system.
    
    Stores:
    1. All actions taken and their outcomes
    2. Failed suggestions (never repeat)
    3. Successful patterns (try again if conditions match)
    4. User preferences (dislikes, allergies, etc.)
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.actions: List[Action] = []
        
        # Fast lookups: actions that didn't work for THIS user
        self.failed_suggestions: Dict[str, int] = {}  # suggestion -> failure count
        
        # What worked: suggestion -> times it worked
        self.successful_suggestions: Dict[str, int] = {}
        
        # User-specific constraints
        self.dislikes: set = set()  # Foods/suggestions user didn't like
        self.allergies: set = set()  # Actual allergies
        self.contraindications: set = set()  # Cannot suggest these
        
        # Time-based: recently suggested (don't repeat)
        self.recent_action_window_days = 3  # Don't repeat same action within 3 days
        
        self.created_at = datetime.utcnow()
        self.last_updated = datetime.utcnow()

    def log_action(
        self,
        action_type: str,
        action_text: str,
        reason: str,
        nutrients_targeted: Optional[List[str]] = None
    ) -> str:
        """
        Log an action that the system took.
        
        Args:
            action_type: Type of action
            action_text: What was suggested/asked
            reason: Why this action was chosen
            nutrients_targeted: Which nutrients does this address?
            
        Returns:
            action_id: Unique identifier for this action
        """
        action_id = f"{self.user_id}_{len(self.actions)}_{datetime.utcnow().timestamp()}"
        
        action = Action(
            action_id=action_id,
            timestamp=datetime.utcnow(),
            action_type=action_type,
            action_text=action_text,
            reason=reason,
            nutrients_targeted=nutrients_targeted or []
        )
        
        self.actions.append(action)
        self.last_updated = datetime.utcnow()
        
        logger.info(f"Action logged: {action_type} - {action_text}")
        return action_id

    def record_outcome(
        self,
        action_id: str,
        outcome: Literal["positive", "negative", "neutral", "unknown"],
        outcome_text: Optional[str] = None
    ) -> bool:
        """
        Record the outcome of an action.
        
        User says "That spinach suggestion was great! I felt so much better"
        Or: "Milk made my stomach upset"
        
        Args:
            action_id: Which action?
            outcome: Was it positive/negative/neutral/unknown?
            outcome_text: What did the user say?
            
        Returns:
            True if successfully recorded, False if action not found
        """
        for action in self.actions:
            if action.action_id == action_id:
                action.outcome = outcome
                action.outcome_text = outcome_text
                action.outcome_recorded_at = datetime.utcnow()
                
                # Update failure/success tracking
                if outcome == "positive":
                    self.successful_suggestions[action.action_text] = \
                        self.successful_suggestions.get(action.action_text, 0) + 1
                    logger.info(f"✓ Success: {action.action_text}")
                    
                elif outcome == "negative":
                    self.failed_suggestions[action.action_text] = \
                        self.failed_suggestions.get(action.action_text, 0) + 1
                    self.dislikes.add(action.action_text)
                    logger.warning(f"✗ Failed: {action.action_text}")
                
                self.last_updated = datetime.utcnow()
                return True
        
        logger.warning(f"Action {action_id} not found in memory")
        return False

    def should_avoid_suggestion(self, suggestion: str) -> bool:
        """
        Should we avoid suggesting this?
        
        Returns True if:
        - It failed before (user reported negative)
        - It's in contraindications (safety)
        - It's in dislikes (user preference)
        """
        if suggestion in self.dislikes:
            return True
        if suggestion in self.contraindications:
            return True
        if suggestion in self.failed_suggestions:
            return True
        return False

    def was_recently_suggested(self, suggestion: str) -> bool:
        """
        Was this suggestion made in the last N days?
        Don't want to repeat the same thing too soon.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=self.recent_action_window_days)
        
        for action in reversed(self.actions):
            if action.timestamp < cutoff_date:
                break  # Older than window, stop checking
            
            if suggestion.lower() in action.action_text.lower():
                return True
        
        return False

    def get_successful_patterns(self) -> List[tuple]:
        """
        What suggestions have worked?
        Return as list of (suggestion, success_count).
        """
        return sorted(
            self.successful_suggestions.items(),
            key=lambda x: x[1],
            reverse=True
        )

    def get_failed_patterns(self) -> List[tuple]:
        """
        What suggestions have failed?
        Return as list of (suggestion, failure_count).
        """
        return sorted(
            self.failed_suggestions.items(),
            key=lambda x: x[1],
            reverse=True
        )

    def get_recent_actions(self, days: int = 7) -> List[Action]:
        """
        Get actions from last N days.
        Useful for understanding recent history.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return [a for a in self.actions if a.timestamp >= cutoff_date]

    def get_action_by_id(self, action_id: str) -> Optional[Action]:
        """Find an action by its ID."""
        for action in self.actions:
            if action.action_id == action_id:
                return action
        return None

    def add_contraindication(self, suggestion: str, reason: str) -> None:
        """
        Hard boundary: never suggest this.
        E.g., "raw_milk" (food safety), "aspirin" (pregnancy safety)
        """
        self.contraindications.add(suggestion.lower())
        logger.warning(f"Added contraindication: {suggestion} ({reason})")

    def add_allergy(self, allergen: str) -> None:
        """Record an allergy."""
        self.allergies.add(allergen.lower())
        self.contraindications.add(allergen.lower())
        logger.warning(f"Added allergy: {allergen}")

    def to_dict(self) -> Dict:
        """Serialize for storage."""
        return {
            "user_id": self.user_id,
            "actions": [a.to_dict() for a in self.actions],
            "failed_suggestions": self.failed_suggestions,
            "successful_suggestions": self.successful_suggestions,
            "dislikes": list(self.dislikes),
            "allergies": list(self.allergies),
            "contraindications": list(self.contraindications),
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Memory":
        """Reconstruct Memory object from persisted dict."""
        user_id = data.get("user_id", "unknown")
        m = cls(user_id)
        actions = data.get("actions", [])
        for a in actions:
            try:
                m.actions.append(Action.from_dict(a))
            except Exception:
                logger.exception("Failed to load action from dict")

        m.failed_suggestions = data.get("failed_suggestions", {})
        m.successful_suggestions = data.get("successful_suggestions", {})
        m.dislikes = set(data.get("dislikes", []))
        m.allergies = set(data.get("allergies", []))
        m.contraindications = set(data.get("contraindications", []))

        # Timestamps
        try:
            from datetime import datetime
            if data.get("created_at"):
                m.created_at = datetime.fromisoformat(data["created_at"])
            if data.get("last_updated"):
                m.last_updated = datetime.fromisoformat(data["last_updated"])
        except Exception:
            logger.exception("Failed to parse timestamps when loading memory")

        return m

    def get_summary(self) -> Dict:
        """Human-readable summary for debugging."""
        return {
            "user_id": self.user_id,
            "total_actions": len(self.actions),
            "successful_suggestions": dict(self.get_successful_patterns()),
            "failed_suggestions": dict(self.get_failed_patterns()),
            "dislikes": list(self.dislikes),
            "allergies": list(self.allergies),
            "recent_actions": [
                {
                    "type": a.action_type,
                    "text": a.action_text,
                    "outcome": a.outcome,
                    "date": a.timestamp.isoformat()
                }
                for a in self.get_recent_actions(7)
            ]
        }
