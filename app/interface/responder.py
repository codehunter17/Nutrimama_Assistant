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


from app.llm_client import LLMClient
from app.core.safety import SafetyChecker


class Responder:
    """
    Converts system decisions into family-like, empathetic responses.

    Must follow Nutrimama rules: never perform logic, never give medical
    advice, always mirror user's language and tone when possible, and
    follow the mandated structure:
      1) emotional connection
      2) simple reason (baby-first, plain words)
      3) one gentle suggestion (if any)
      4) choice + comfort
    """

    def __init__(self):
        self.responses_generated = 0
        self.response_log = []
        self._llm = LLMClient.from_env()
        self._safety = SafetyChecker()

    def _detect_language(self, user_message: Optional[str]) -> str:
        """Very small heuristic language detection.
        Returns: 'hi' (Hindi), 'hinglish', 'en' (English)
        """
        if not user_message:
            return "en"
        # Devanagari characters -> Hindi
        if any("\u0900" <= ch <= "\u097F" for ch in user_message):
            return "hi"
        lower = user_message.lower()
        # Simple Hinglish indicators (common romanized Hindi words)
        hinglish_tokens = ["kya", "hi", "haan", "nahin", "nahi", "acha", "theek", "tum", "maa", "bhai", "beta", "badi"]
        if any(tok in lower for tok in hinglish_tokens):
            return "hinglish"
        return "en"

    def _mirror_tone(self, user_message: Optional[str], default_short: bool = False) -> str:
        """Decide message verbosity based on user's message length and punctuation."""
        if not user_message:
            return "normal"
        if len(user_message.strip()) < 20:
            return "short"
        if user_message.strip().endswith("!") or user_message.strip().endswith("!!"):
            return "soft"
        return "normal"

    def _family_phrase(self, lang: str, key: str) -> str:
        """Return small family phrases in different languages.
        key: emotional, comfort, choice, reassurance
        """
        phrases = {
            "emotional": {
                "en": "Hey,",
                "hi": "Sunna,",
                "hinglish": "Sun na,"
            },
            "comfort": {
                "en": "It's okay. I'm here.",
                "hi": "Koi baat nahi. Main hoon na.",
                "hinglish": "Koi baat nahi, main hoon na."
            },
            "choice": {
                "en": "Do it only if you want to. I'm with you.",
                "hi": "Sirf agar tum chaaho to. Main tumhare saath hoon.",
                "hinglish": "Bas jab tum chaaho, theek hai. Main hoon na."
            },
            "soft_reassure": {
                "en": "Take it easy, okay?",
                "hi": "Aaram se, theek hai?",
                "hinglish": "Aaram se, theek hai?"
            }
        }
        return phrases.get(key, {}).get(lang, phrases[key]["en"])

    def _compose_message(self, emotional: str, reason: str, suggestion: Optional[str], lang: str, include_choice: bool = True) -> str:
        """Compose final message using mandated structure, with simple line breaks.

        include_choice: whether to add a choice+comfort closing line. If False,
        append a simple comfort phrase instead (useful for observe/alert cases).
        """
        parts = []
        parts.append(emotional)  # First line: emotional connection
        parts.append(reason)     # Second line: simple reason
        if suggestion:
            parts.append(suggestion)
        if include_choice:
            parts.append(self._family_phrase(lang, "choice"))
        else:
            parts.append(self._family_phrase(lang, "comfort"))
        return "\n\n".join(parts)

    def _safe_suggestion(self, suggestion_text: str, suggestion_type: str = "food", pregnancy_stage: Optional[str] = None, breastfeeding: bool = False) -> Optional[str]:
        """Return suggestion if safe according to SafetyChecker, otherwise None.

        Also treat medication-like suggestions specially by delegating to
        `check_medication_safety` when the suggestion looks like a drug.
        """
        text = suggestion_text.lower()
        # Quick medication detection
        meds = set(getattr(self._safety, "UNSAFE_MEDICATIONS", []))
        if any(m in text for m in meds) or any(w in text for w in ["pill", "tablet", "aspirin", "ibuprofen", "paracetamol"]):
            ok, _ = self._safety.check_medication_safety(suggestion_text)
            if not ok:
                return None
            # Conservative: even if medication passes, we avoid suggesting meds
            return None

        ok, reason = self._safety.check_suggestion_validity(suggestion_text, suggestion_type, pregnancy_stage, breastfeeding)
        if ok:
            return suggestion_text
        # If not safe, return None so responder avoids giving the suggestion
        return None

    def respond_to_action(
        self,
        action_type: str,
        action_details: Dict,
        state=None,
        user_message: Optional[str] = None,
        perception: Optional[Dict] = None,
        use_llm: bool = True
    ) -> str:
        """
        Generate a family-like response for an action. Must not perform logic.

        user_message: optional text from user to mirror language/tone
        perception: optional parsed result from NLP to guide mirroring (intent/sentiment)
        use_llm: whether to attempt LLM phrasing (still subject to safety)
        """
        lang = self._detect_language(user_message)
        tone = self._mirror_tone(user_message)

        # Map action types to simple reason and suggestion
        emotional_line = self._family_phrase(lang, "emotional")
        reason_line = ""
        suggestion_line = None

        # Handle special cases first
        if action_type == "alert_medical":
            # Calm, clear, familial
            alert_text = action_details.get("alert") or action_details.get("symptom") or "We need medical help."
            # Compose: emotional, simple reason (calm), suggestion: seek medical help, choice+comfort
            reason_line = {
                "en": f"I’m worried — you mentioned: {alert_text}.",
                "hi": f"Mujhe chinta ho rahi hai — aapne bataya: {alert_text}.",
                "hinglish": f"Mujhe thoda fikr ho rahi hai — tumne bataya: {alert_text}."
            }[lang]

            suggestion_line = {
                "en": "Please contact a doctor or go to the nearest emergency service now. If it’s urgent, call your local emergency number.",
                "hi": "Kripya doctor se sampark karein ya turant aspataal jaiye. Yeh zaruri ho to apna local emergency number dial karein.",
                "hinglish": "Please doctor ko batao ya turant hospital chalo. Emergency ho to local number pe call karo."
            }[lang]

            # Always include final comfort (no choice in emergencies)
            return self._compose_message(emotional_line, reason_line, suggestion_line, lang, include_choice=False)

        if action_type == "observe" or action_type == "no_action":
            # No new advice; just emotional support
            reason_line = {
                "en": "Nothing urgent right now.",
                "hi": "Abhi kuch zaruri nahin hai.",
                "hinglish": "Abhi koi khas baat nahin hai."
            }[lang]
            suggestion_line = None
            return self._compose_message(emotional_line, reason_line, suggestion_line, lang, include_choice=False)

        # For suggestion types, create simple reason and gentle suggestion
        if action_type == "suggest_food":
            food = action_details.get("food") or "something nutritious"
            nutrient = action_details.get("nutrient") or "good nutrients"

            # Ensure suggestion is safe
            safe_food = self._safe_suggestion(food, "food", state.pregnancy_stage if state else None, state.breastfeeding if state else False)
            if not safe_food:
                # If unsafe, avoid suggesting and instead offer to check with doctor
                reason_line = {
                    "en": f"I think something needs attention with {nutrient}.",
                    "hi": f"Mujhe lagta hai kuch dhyaan dene ki zarurat hai — {nutrient}.",
                    "hinglish": f"Mujhe lagta hai thoda dhyaan chahiye — {nutrient}."
                }[lang]
                suggestion_line = {
                    "en": "I can help find safe options, or we can check with a doctor if you'd prefer.",
                    "hi": "Main surakshit vikalp dhoondh kar de sakti hoon, ya aap doctor se puch sakti hain.",
                    "hinglish": "Main safe options dhoondh sakti hoon, ya chahoge to doctor se puch lete hain."
                }[lang]
                return self._compose_message(emotional_line, reason_line, suggestion_line, lang)

            # Normal family phrasing
            reason_line = {
                "en": f"I think your {nutrient} could use a little boost.",
                "hi": f"Mujhe lagta hai aapke {nutrient} ko thoda boost chahiye.",
                "hinglish": f"Lagta hai thoda {nutrient} kam hai, thoda boost kar dete hain."
            }[lang]

            suggestion_line = {
                "en": f"A small serving of {safe_food} could help — just a little, whenever you feel like it.",
                "hi": f"Thoda sa {safe_food} khaana madad karega — jab man kare, bas thoda hi.",
                "hinglish": f"Ek choti si serving {safe_food} ka try karo — jab mann ho, bas halka sa."
            }[lang]

        elif action_type == "suggest_water":
            glasses = action_details.get("glasses", 3)
            reason_line = {
                "en": "You might be a bit dehydrated.",
                "hi": "Aap thodi dehydrated ho sakti hain.",
                "hinglish": "Lagta hai thoda pani kam hai."
            }[lang]
            suggestion_line = {
                "en": f"Try sipping {glasses} glasses of water across the day — small sips are fine.",
                "hi": f"Din bhar mein {glasses} glass paani peene ki koshish karein — chhote chhote ghut bhi theek hain.",
                "hinglish": f"Poore din mein {glasses} glass pani peena accha rahega — chhote ghut chalte hain."
            }[lang]

        elif action_type == "suggest_rest":
            suggestion = action_details.get("suggestion", "rest")
            reason_line = {
                "en": "You look tired — rest might help.",
                "hi": "Aap thak gayi lag rahi hain — aaram karna madad karega.",
                "hinglish": "Tum thak gayi lag rahi ho — thoda aaram kar lo."
            }[lang]
            suggestion_line = {
                "en": f"Try to rest or nap if you can. I’ll be here when you wake up.",
                "hi": f"Jab mauka mile toh thoda aaram karo ya nap kar lo. Main yahin hoon.",
                "hinglish": f"Thoda rest kar lo ya nap kar lo, main yahin hoon."
            }[lang]

        elif action_type == "ask_question" or action_type == "check_in":
            question = action_details.get("question", "How are you feeling today?")
            reason_line = {
                "en": question,
                "hi": question,
                "hinglish": question
            }[lang]
            suggestion_line = None

        else:
            # Fallback
            reason_line = {
                "en": "I’m here with you.",
                "hi": "Main tumhare saath hoon.",
                "hinglish": "Main hoon na, tumhare saath hoon."
            }[lang]
            suggestion_line = None

        # Final assembly
        message = self._compose_message(emotional_line, reason_line, suggestion_line, lang)

        # Optionally run LLM to polish phrasing, but only if prompt safe and adapter allowed
        if use_llm:
            prompt = f"Polish the following message while keeping it familial, short, and non-medical:\n\n{message}"
            if self._safety.is_prompt_safe(prompt):
                try:
                    polished = self._llm.generate_response(prompt, max_tokens=80)
                    # Validate polished output: it must be a family-like polish and not just an echo of the prompt
                    if polished and "polish the following" not in polished.lower() and "polish" not in polished.lower():
                        # Accept any non-echo polished response (no strict blank-line requirement)
                        return polished
                except Exception:
                    logger.exception("LLM polishing failed; using template response")

        return message
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
        """Respond when user gives feedback on a suggestion. Prefer LLM phrasing."""
        prompt = (
            f"Write a short empathetic response to user feedback. Suggestion: {suggestion}. Outcome: {outcome}."
            "Keep it concise and supportive."
        )

        if self._safety.is_prompt_safe(prompt):
            try:
                resp = self._llm.generate_response(prompt, max_tokens=40)
                if resp:
                    return resp
            except Exception:
                pass

        # Fallback templates
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
        """Quick acknowledgment of user input; try LLM for empathetic phrasing."""
        prompt = f"Short empathetic acknowledgement for: {user_message}. Keep under 30 words."
        if self._safety.is_prompt_safe(prompt):
            try:
                resp = self._llm.generate_response(prompt, max_tokens=30)
                if resp:
                    return resp
            except Exception:
                pass

        # Fallback template
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
