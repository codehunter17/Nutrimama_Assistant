# app/main.py
"""
Nutrimama: AI Assistant for Maternal Nutrition

A caring, belief-driven system for pregnant and nursing mothers.
NOT a doctor. NOT a medical system.
Like a caring maa who remembers what helped you before.

Architecture:
1. Perception (NLP) - understand user input
2. State - current belief about mother's health
3. Memory - what actually happened
4. Reasoning - decide what to do
5. Safety - hard boundaries
6. Responder - warm communication

ML models are sensors, not decision makers.
"""

import logging
from datetime import datetime
from typing import Optional

from app.core.state import MaternalBrainState
from app.core.memory import Memory
from app.core.reasoning import ReasoningEngine
from app.core.safety import SafetyChecker
from app.perception.nlp import NLPParser
from app.learning.adaptation import AdaptationEngine
from app.knowledge.nutrition import NutritionKnowledgeBase
from app.models.predictors import PredictorSuite, DummyNutrientPredictor
from app.models.registry import ModelRegistry, ModelMetadata
from app.interface.responder import Responder
from app.storage import load_user_state, save_user_state


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Nutrimama:
    """
    Main Nutrimama assistant system.
    
    Orchestrates all subsystems:
    - State management
    - Memory and learning
    - Reasoning and decisions
    - Safety checks
    - Warm communication
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        logger.info(f"Initializing Nutrimama for user: {user_id}")

        # Core brain
        # Try to load persisted state & memory
        loaded = load_user_state(user_id)
        if loaded:
            self.state, self.memory = loaded
            logger.info(f"Loaded persisted state and memory for {user_id}")
        else:
            self.state = MaternalBrainState()
            self.memory = Memory(user_id)
        self.reasoning = ReasoningEngine()
        self.safety = SafetyChecker()

        # Perception
        self.nlp = NLPParser()

        # Learning
        self.adaptation = AdaptationEngine(self.memory)

        # Knowledge
        self.nutrition_kb = NutritionKnowledgeBase()

        # ML models (with dummy predictors for now)
        self.predictors = PredictorSuite()
        self._init_predictors()

        # Model registry
        self.model_registry = ModelRegistry()

        # Communication
        self.responder = Responder()

        logger.info("Nutrimama initialized successfully")

    def _init_predictors(self):
        """Initialize predictors with dummy models for testing."""
        nutrients = ["iron", "protein", "calcium", "folic", "vitamin_b12", "iodine"]

        for nutrient in nutrients:
            dummy = DummyNutrientPredictor(nutrient, "1.0")
            self.predictors.register_predictor(nutrient, dummy)

        logger.info(f"Initialized {len(nutrients)} nutrient predictors")

    def process_user_message(self, user_input: str) -> str:
        """
        Main entry point: Process user input and return response.
        
        Pipeline:
        1. Parse user input (NLP)
        2. Update state based on input
        3. Check safety
        4. Reasoning (decide action)
        5. Respond warmly
        """
        logger.info(f"Processing: {user_input}")

        # Step 1: Acknowledge user
        ack = self.responder.acknowledge_user(user_input)

        # Step 2: Parse input
        parsed = self.nlp.parse(user_input)
        logger.debug(f"Parsed intent: {parsed['intent']}")

        # Step 3: Update state based on parsed input
        self._update_state_from_input(parsed)

        # Step 4: Check for feedback on previous actions
        feedback = self.nlp.get_action_history_intent(user_input)
        if feedback:
            self._process_feedback(feedback)

        # Step 5: Get ML signals
        self._update_state_from_models()

        # Step 6: Safety check
        self.safety.clear_violations()
        self.safety.clear_alerts()

        # Step 7: Reasoning - decide action
        action_type, action_details, reasoning = self.reasoning.decide(
            self.state, self.memory, self.safety
        )

        # Step 8: Log action
        action_id = self.memory.log_action(
            action_type.value,
            action_details.get("food") or action_details.get("suggestion") or str(action_details),
            reasoning,
            nutrients_targeted=action_details.get("nutrients_targeted", [])
        )

        # Persist after logging an action
        try:
            save_user_state(self.user_id, self.state, self.memory)
        except Exception:
            logger.exception("Failed to save user state after logging action")

        # Step 9: Generate warm response
        response = self.responder.respond_to_action(
            action_type.value, action_details, self.state
        )

        # Step 10: Update state's last action
        self.state.last_action = action_type.value
        self.state.last_action_date = datetime.utcnow()

        return f"{ack}\n\n{response}"

    def _update_state_from_input(self, parsed: dict):
        """Update state based on NLP parsing."""
        # Report symptoms
        for symptom in parsed.get("symptoms", []):
            self.state.report_symptom(symptom)

        # Sentiment-based inference
        if parsed.get("sentiment") == "negative":
            self.state.energy_level = max(0.0, self.state.energy_level - 0.1)

        elif parsed.get("sentiment") == "positive":
            self.state.energy_level = min(1.0, self.state.energy_level + 0.1)

    def _update_state_from_models(self):
        """Get signals from ML models and damp them into state."""
        predictions = self.predictors.predict_all(
            age=self.state.age or 30,
            pregnancy_stage=self.state.pregnancy_stage,
            breastfeeding=self.state.breastfeeding,
            recent_symptoms=list(self.state.symptoms),
            days_since_last_check=1
        )

        for nutrient, (prediction, confidence) in predictions.items():
            self.state.apply_ml_signal(nutrient, prediction, confidence)

    def _process_feedback(self, feedback: dict):
        """Process user feedback on previous suggestions."""
        suggestion = feedback.get("action")
        outcome = feedback.get("outcome")

        response = self.responder.respond_to_feedback(suggestion, outcome)
        logger.info(f"Feedback processed: {suggestion} → {outcome}")

        # Find matching action in memory
        # For now, just record the feedback
        # In real system, would match to actual action_id
        action_id = feedback.get("action_id")
        outcome = feedback.get("outcome")
        if action_id and outcome:
            recorded = self.memory.record_outcome(action_id, outcome, feedback.get("text"))
            if recorded:
                try:
                    save_user_state(self.user_id, self.state, self.memory)
                except Exception:
                    logger.exception("Failed to save user state after recording feedback")

    def get_state_summary(self) -> dict:
        """Get current state summary (for UI/debugging)."""
        return {
            "state": self.state.get_state_summary(),
            "memory": self.memory.get_summary(),
            "learning": self.adaptation.get_learning_insights(),
            "model_health": self.model_registry.check_all_health()
        }

    def report_symptom(self, symptom: str):
        """User reports a symptom."""
        self.state.report_symptom(symptom)
        logger.info(f"Symptom reported: {symptom}")

    def reset_symptoms(self):
        """Clear symptom list."""
        self.state.clear_symptoms()

    def __repr__(self) -> str:
        return (
            f"Nutrimama(user={self.user_id}, "
            f"state_updates={self.state.update_count}, "
            f"actions={len(self.memory.actions)})"
        )


# Example usage
if __name__ == "__main__":
    # Initialize system
    nutrimama = Nutrimama("user_001")

    # Simulate conversation
    messages = [
        "I've been feeling very tired lately",
        "My energy is really low. I tried spinach yesterday and felt better",
        "But now I'm worried I'm not getting enough iron"
    ]

    for msg in messages:
        print(f"\n👤 User: {msg}")
        response = nutrimama.process_user_message(msg)
        print(f"\n🤱 Nutrimama: {response}")

    # Show summary
    print("\n" + "="*60)
    print("📊 SYSTEM SUMMARY")
    print("="*60)
    summary = nutrimama.get_state_summary()
    print(f"\nState: {summary['state']}")
    print(f"\nLearning: {summary['learning']}")
