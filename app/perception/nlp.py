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
        """Find nutrient mentions in the text."""
        nutrients = []
        
        for nutrient, keywords in self.NUTRIENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    nutrients.append(nutrient)
                    break
        
        return nutrients

    def _detect_intent(self, text: str, symptoms: List[str], nutrients: List[str]) -> str:
        """Infer what the user is trying to communicate."""
        
        # Symptoms mentioned → reporting symptoms
        if symptoms:
            if "worked" in text or "helped" in text or "better" in text:
                return "give_feedback_positive"
            elif "didn't work" in text or "didn't help" in text or "worse" in text:
                return "give_feedback_negative"
            else:
                return "report_symptom"
        
        # "Did you mean..." or "what..." → asking question
        if re.search(r"(what|why|how|do you|can you|should|could)", text):
            return "ask_question"
        
        # Nutrients mentioned → discussing nutrition
        if nutrients:
            return "discuss_nutrition"
        
        # Default
        return "general_chat"

    def _calculate_confidence(self, symptoms: List[str], sentiment: str, nutrients: List[str]) -> float:
        """
        How confident are we in this parsing?
        More signals = higher confidence.
        """
        confidence = 0.5
        
        if symptoms:
            confidence += 0.2
        if sentiment != "neutral":
            confidence += 0.15
        if nutrients:
            confidence += 0.15
        
        return min(1.0, confidence)

    def extract_feedback_target(self, user_input: str) -> Optional[str]:
        """
        If user says "The spinach suggestion was great",
        extract "spinach" as the target of feedback.
        """
        # Look for: "the X suggestion", "eating X", "tried X", "X was...", "about X"
        pattern = r"(the |tried |eating |about |taking |having )?(\w+)( .*?(suggestion|idea|tip|recommendation|food|drink))?(.*(great|good|bad|terrible|didn't work|helped|worked))"
        
        match = re.search(pattern, user_input.lower())
        if match:
            return match.group(2)
        
        return None

    def get_action_history_intent(self, user_input: str) -> Optional[Dict]:
        """
        Parse if user is reporting outcome of a previous action.
        E.g., "I tried spinach yesterday and felt great"
        
        Returns:
            {"action": "spinach", "outcome": "positive", "when": "yesterday"}
            or None if not an outcome report
        """
        # Pattern: "I tried X and felt ..."
        pattern = r"(tried|had|ate|took|drank)\s+(\w+).*?(great|good|bad|worse|better|better|helpful|didn't help)"
        
        match = re.search(pattern, user_input.lower())
        if match:
            action = match.group(2)
            outcome_text = match.group(3)
            
            outcome = "positive" if outcome_text in ["great", "good", "better", "helpful"] else "negative"
            
            return {
                "action": action,
                "outcome": outcome,
                "outcome_text": outcome_text
            }
        
        return None

    def __repr__(self) -> str:
        return f"NLPParser(symptoms={len(self.SYMPTOM_KEYWORDS)}, confidence_ready)"
