# app/interface/responder.py
"""
Responder: Communication interface.

This is where LLM (when integrated) converts cold logic into warm,
empathetic responses.

Currently: Template-based (simple)
Future: LLM-based (GPT, etc. for better tone)

Key: LLM ONLY formats the response. It does NOT make decisions.
The brain (reasoning.py) already decided. Responder just makes it warm.
"""

from typing import Dict, Optional, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ResponseTone(Enum):
    """Tone of response."""
    WARM = "warm"
    SUPPORTIVE = "supportive"
    INFORMATIVE = "informative"
    CONCERNED = "concerned"
    URGENT = "urgent"


class Responder:
    """
    Converts system decisions into human-friendly responses.
    """

    def __init__(self):
        self.responses_generated = 0
        self.response_log = []

    def respond_to_action(
        self,
        action_type: str,
        action_details: Dict,
        state=None,
        context: str = ""
    ) -> str:
        """
        Generate a warm response for an action.
        
        Args:
            action_type: Type of action from reasoning engine
            action_details: Details of the action
            state: MaternalBrainState for context
            context: Additional context
            
        Returns:
            Response text to show to user
        """
        if action_type == "suggest_food":
            return self._respond_suggest_food(action_details, state)

        elif action_type == "suggest_water":
            return self._respond_suggest_water(action_details, state)

        elif action_type == "suggest_rest":
            return self._respond_suggest_rest(action_details, state)

        elif action_type == "ask_question":
            return self._respond_ask_question(action_details, state)

        elif action_type == "observe":
            return self._respond_observe(action_details, state)

        elif action_type == "alert_medical":
            return self._respond_alert_medical(action_details)

        elif action_type == "check_in":
            return self._respond_check_in(action_details, state)

        else:
            return "I'm here to support you. How can I help?"

    def _respond_suggest_food(self, details: Dict, state=None) -> str:
        """Warm response for food suggestion."""
        food = details.get("food", "something nutritious")
        nutrient = details.get("nutrient", "")

        responses = [
            f"I've been thinking... you might feel better if you had some {food} today. "
            f"It's rich in {nutrient}, which your body could use right now. "
            f"Even a small serving would help! ❤️",

            f"How about trying some {food}? "
            f"It can help with your {nutrient} levels, and I think it'll make you feel better. "
            f"No pressure though—only if you feel like it. 🌱",

            f"I notice you could use a bit more {nutrient}. "
            f"{food.title()} is a wonderful source, and quite easy to prepare. "
            f"Would you like to give it a try? 💪"
        ]

        return self._pick_response(responses)

    def _respond_suggest_water(self, details: Dict, state=None) -> str:
        """Warm response for hydration."""
        glasses = details.get("glasses", 3)

        responses = [
            f"Your body's been working hard. Let's get some water in you—"
            f"aim for {glasses} glasses throughout the day, okay? "
            f"Small sips are fine. 💧",

            f"I'm noticing you might need more hydration. "
            f"Try drinking {glasses} glasses of water or warm milk today. "
            f"Stay well-hydrated, mama. 💙",

            f"How are you feeling hydration-wise? "
            f"Let's make sure you're drinking enough—{glasses} glasses spread through the day would be perfect. 🌊"
        ]

        return self._pick_response(responses)

    def _respond_suggest_rest(self, details: Dict, state=None) -> str:
        """Warm response for rest."""
        suggestion = details.get("suggestion", "rest")

        responses = [
            f"You deserve some rest. {suggestion.capitalize()}, and be kind to yourself. "
            f"Your body is doing amazing things. 😴",

            f"I think your body is asking for a break. {suggestion.capitalize()}. "
            f"You're doing so well, and rest is part of taking care of yourself. 💤",

            f"Listen to yourself right now. {suggestion.capitalize()} when you can. "
            f"You've earned it, mama. 🛌"
        ]

        return self._pick_response(responses)

    def _respond_ask_question(self, details: Dict, state=None) -> str:
        """Response when asking for information."""
        question = details.get("question", "How are you feeling?")

        responses = [
            f"{question}\n\nI care about how you're doing. Tell me what's on your mind. 💕",

            f"{question}\n\nI'm here to listen and support you. 👂",

            f"{question}\n\nYour feelings matter. I'm here to help. ❤️"
        ]

        return self._pick_response(responses)

    def _respond_check_in(self, details: Dict, state=None) -> str:
        """Regular check-in response."""
        question = details.get("question", "How are you feeling today?")

        responses = [
            f"{question}\n\nI'm thinking of you. How's your energy and mood today? "
            f"Anything bothering you, or just checking in. 🌟",

            f"{question}\n\nLet me know what's going on with you. "
            f"Any new symptoms, energy levels, or just how you're doing mentally? 💭",

            f"{question}\n\nI want to make sure you're taking care of yourself. "
            f"Tell me everything. 💌"
        ]

        return self._pick_response(responses)

    def _respond_observe(self, details: Dict, state=None) -> str:
        """Response when system is just observing."""
        reason = details.get("reason", "No urgent action needed")

        responses = [
            "You're doing great. I'm here when you need me. Keep being amazing! 💫",

            "Everything looks good from where I'm standing. You've got this! 💪",

            "No worries right now. But I'm always here if you need anything. 🌸"
        ]

        return self._pick_response(responses)

    def _respond_alert_medical(self, details: Dict) -> str:
        """URGENT: medical alert."""
        alert = details.get("alert", "We need medical help.")
        symptom = details.get("symptom", "")

        warning = f"⚠️ {alert}\n\n"

        if symptom:
            warning += f"You mentioned: {symptom}\n\n"

        warning += (
            "Please reach out to a doctor or nurse as soon as possible. "
            "Don't wait. Your safety is what matters most. 🚨\n\n"
            "If this is an emergency, call 112 (India) or your local emergency number."
        )

        return warning

    def _pick_response(self, responses: List[str]) -> str:
        """Pick a response from options (simple rotation for now)."""
        # In future, could use LLM to pick best one, or rotate randomly
        return responses[0]

    def respond_to_feedback(
        self,
        suggestion: str,
        outcome: str,  # "positive" or "negative"
        outcome_text: Optional[str] = None
    ) -> str:
        """
        Respond when user gives feedback on a suggestion.
        """
        if outcome == "positive":
            responses = [
                f"I'm so glad the {suggestion} helped! 🎉 "
                f"Your body is responding well. Keep it up, mama!",

                f"That's wonderful! {suggestion.title()} really worked for you. "
                f"I'll remember that. You know yourself best. 💕",

                f"Yes! See, you're amazing at listening to your body. "
                f"The {suggestion} made a real difference. I'm proud of you! ✨"
            ]

        else:  # negative
            responses = [
                f"Got it—{suggestion} didn't work for you. That's valuable info! "
                f"Let's try something different next time. 💭",

                f"Thank you for telling me. {suggestion.title()} isn't for you. "
                f"I won't suggest it again. We'll find what works! 🌟",

                f"I hear you. {suggestion} didn't feel right. "
                f"That's okay—everyone's different. Let me find a better option. 💪"
            ]

        return self._pick_response(responses)

    def acknowledge_user(self, user_message: str) -> str:
        """Quick acknowledgment of user input."""
        responses = [
            "I hear you. 💙",
            "Thank you for sharing. I'm listening. 👂",
            "Got it. I care about what you're saying. ❤️",
            "I understand. You matter. 🌟",
            "Thank you for telling me. I've got this. 💪"
        ]

        return self._pick_response(responses)

    def generate_summary(self, state, memory) -> str:
        """
        Generate a warm summary of current status.
        NOT shown to user normally, but useful for app views.
        """
        summary = "📋 Your Nutrimama Summary:\n\n"

        # Overall status
        avg_nutrition = sum(state.nutrition.values()) / len(state.nutrition)
        if avg_nutrition > 0.7:
            summary += "✨ You're doing wonderfully! Keep it up.\n\n"
        elif avg_nutrition > 0.5:
            summary += "💪 You're managing well. Small adjustments can help more.\n\n"
        else:
            summary += "🌱 Let's work together to boost your nutrition.\n\n"

        # Key stats
        successful = len([a for a in memory.actions if a.outcome == "positive"])
        total = len([a for a in memory.actions if a.outcome])

        if total > 0:
            success_rate = successful / total
            summary += f"📊 Things that worked for you: {success_rate:.0%}\n"

        summary += f"💭 Symptoms you mentioned: {', '.join(state.symptoms) if state.symptoms else 'None recently'}\n"

        return summary

    def __repr__(self) -> str:
        return f"Responder(responses_generated={self.responses_generated})"
