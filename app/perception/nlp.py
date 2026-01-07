# app/perception/nlp.py
"""
NLP Perception: Parse user input to extract intent, sentiment, symptoms.

NOT a full NLP model. Simple pattern matching + keyword extraction.
Fast, explainable, low-latency.
"""

from typing import Dict, List, Optional, Literal
import re
import logging

logger = logging.getLogger(__name__)


class NLPParser:
    """
    Simple NLP for understanding user input.
    """

    # Symptoms keywords
    SYMPTOM_KEYWORDS = {
        "tired|fatigue|exhausted|sleepy": "fatigue",
        "nausea|vomiting|sick|queasy": "nausea",
        "headache|migraine|head pain": "headache",
        "dizzy|dizziness|vertigo|lightheaded": "dizziness",
        "stomach pain|abdominal pain|belly ache": "stomach_pain",
        "constipation|constipated": "constipation",
        "heartburn|acidity|acid reflux": "heartburn",
        "swelling|swollen|edema": "swelling",
        "cramps|cramping": "cramps",
        "shortness of breath|breathless|can't breathe": "shortness_of_breath",
        "bleeding|bleed|blood": "bleeding",
        "weakness|weak": "weakness"
    }

    # Sentiment indicators
    POSITIVE_WORDS = {
        "good", "great", "better", "best", "feeling good", "improved",
        "energetic", "happy", "glad", "thank you", "thanks",
        "working", "helped", "excellent", "wonderful", "nice"
    }

    NEGATIVE_WORDS = {
        "bad", "worse", "worst", "not good", "terrible", "awful",
        "upset", "sad", "angry", "frustrated", "didn't help", "useless",
        "hate", "dislike", "can't", "unable", "poor", "horrible"
    }

    # Nutrient-related keywords
    NUTRIENT_KEYWORDS = {
        "iron": ["iron", "spinach", "red meat", "blood", "hemoglobin"],
        "protein": ["protein", "meat", "chicken", "eggs", "milk", "strong"],
        "calcium": ["calcium", "milk", "bones", "teeth", "dairy"],
        "folic": ["folic", "spinach", "vegetables", "greens"],
        "vitamin_b12": ["b12", "energy", "meat", "eggs"],
        "iodine": ["iodine", "salt", "thyroid"]
    }

    def __init__(self):
        self.last_parsed = None

    def parse(self, user_input: str) -> Dict:
        """
        Parse user input and extract structured information.
        
        Returns:
            {
                "text": original text,
                "symptoms": [list of detected symptoms],
                "sentiment": "positive" / "negative" / "neutral",
                "nutrients_mentioned": [nutrients user talked about],
                "intent": "report_symptom" / "give_feedback" / "ask_question" / "general_chat",
                "confidence": 0-1 (how confident are we in this parsing?)
            }
        """
        text_lower = user_input.lower().strip()

        symptoms = self._extract_symptoms(text_lower)
        sentiment = self._detect_sentiment(text_lower)
        nutrients = self._extract_nutrients(text_lower)
        intent = self._detect_intent(text_lower, symptoms, nutrients)

        result = {
            "text": user_input,
            "symptoms": symptoms,
            "sentiment": sentiment,
            "nutrients_mentioned": nutrients,
            "intent": intent,
            "confidence": self._calculate_confidence(symptoms, sentiment, nutrients)
        }

        self.last_parsed = result
        logger.debug(f"Parsed: {intent} (confidence: {result['confidence']:.2f})")

        return result

    def _extract_symptoms(self, text: str) -> List[str]:
        """Find symptoms in the text."""
        symptoms = []
        
        for pattern, symptom_name in self.SYMPTOM_KEYWORDS.items():
            if re.search(pattern, text, re.IGNORECASE):
                symptoms.append(symptom_name)
        
        return list(set(symptoms))  # Remove duplicates

    def _detect_sentiment(self, text: str) -> Literal["positive", "negative", "neutral"]:
        """Simple sentiment analysis."""
        positive_score = sum(1 for word in self.POSITIVE_WORDS if word in text)
        negative_score = sum(1 for word in self.NEGATIVE_WORDS if word in text)

        if positive_score > negative_score:
            return "positive"
        elif negative_score > positive_score:
            return "negative"
        else:
            return "neutral"

    def _extract_nutrients(self, text: str) -> List[str]:
        """Find nutrient mentions in the text (return list of nutrient keys)."""
        nutrients = []

        for nutrient, keywords in self.NUTRIENT_KEYWORDS.items():
            for keyword in keywords:
                if re.search(rf"\b{re.escape(keyword.lower())}\b", text):
                    nutrients.append(nutrient)
                    break

        return nutrients

    def _detect_intent(self, text: str, symptoms: List[str], nutrients: List[str]) -> str:
        """Infer user intent with more granular categories."""

        # Feedback/outcome reporting
        if re.search(r"\b(tried|had|ate|took|drank)\b", text) and re.search(r"\b(great|good|better|helped|didn't|did not|worse|bad)\b", text):
            if re.search(r"\b(great|good|better|helped|helpful)\b", text):
                return "give_feedback_positive"
            else:
                return "give_feedback_negative"

        # Symptoms mentioned → reporting symptoms
        if symptoms:
            return "report_symptom"

        # Requesting a suggestion explicitly
        if re.search(r"\b(can you suggest|suggest|recommend|what should i|what can i)\b", text):
            return "request_suggestion"

        # Asking question
        if re.search(r"\b(what|why|how|do you|can you|should|could|is it)\b", text):
            return "ask_question"

        # Nutrients mentioned → discussing nutrition
        if nutrients:
            return "discuss_nutrition"

        # Greetings / small talk
        if re.match(r"\s*(hi|hello|hey|good morning|good evening)\b", text):
            return "greeting"

        # Default
        return "general_chat"

    def _calculate_confidence(self, symptoms: List[str], sentiment: str, nutrients: List[str]) -> float:
        """
        How confident are we in this parsing?
        More signals = higher confidence.
        """
        confidence = 0.5

        if symptoms:
            confidence += 0.25
        if sentiment != "neutral":
            confidence += 0.15
        if nutrients:
            confidence += 0.15

        # Cap confidence to 0.95 to leave room for uncertainty in rule-based parsing
        return min(0.95, confidence)

    def extract_feedback_target(self, user_input: str) -> Optional[str]:
        """
        If user says "The spinach suggestion was great", extract the food target.
        Supports multi-word food names.
        """
        # Look for common patterns around feedback
        patterns = [
            r"\b(?:the )?(?P<food>[a-z\s_\-]+?) (?:suggestion|idea|tip|recommendation|food|drink)\b",
            r"\b(?:i tried|i had|i ate|i took|i tried) (?P<food>[a-z\s_\-]+?) (?:and|,|\.| )",
            r"\b(?:tried|ate|had) (?P<food>[a-z\s_\-]+?) and .*?(great|good|better|helped|didn't|did not|worse|bad)\b",
        ]

        text = user_input.lower()
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                food = m.group("food").strip()
                # sanitize: keep only alpha/space/hyphen
                return re.sub(r"[^a-z\s\-]", "", food)

        return None

    def get_action_history_intent(self, user_input: str) -> Optional[Dict]:
        """
        Parse outcome reports such as "I tried spinach yesterday and felt great".

        Returns a dict with keys: action (food), outcome (positive/negative), when (optional phrase)
        """
        pattern = r"(?:i (?:tried|had|ate|took|drank)|tried) (?P<food>[a-z\s_\-]+?)(?: (?:yesterday|today|this morning|last night))?(?: .*? (?P<outcome>great|good|better|helped|didn't|did not|worse|bad|poor|terrible))"
        m = re.search(pattern, user_input.lower())
        if m:
            food = re.sub(r"[^a-z\s\-]", "", m.group("food")).strip()
            outcome_text = m.group("outcome")
            outcome = "positive" if outcome_text in ["great", "good", "better", "helped"] else "negative"
            when = None
            if re.search(r"yesterday|today|this morning|last night", user_input.lower()):
                when = re.search(r"(yesterday|today|this morning|last night)", user_input.lower()).group(0)
            return {"action": food, "outcome": outcome, "when": when}

        return None

    def __repr__(self) -> str:
        return f"NLPParser(symptoms={len(self.SYMPTOM_KEYWORDS)}, confidence_ready)"
