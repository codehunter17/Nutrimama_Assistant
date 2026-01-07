# app/models/predictors.py
"""
ML Predictors: Models as SENSORS, not decision makers.

These models are trained on historical nutrition data.
They output signals (0-1) about nutrient adequacy.

CRITICAL: State does NOT directly use model outputs.
Model signals are DAMPED and merged with memory and user feedback.

This file wraps CatBoost and other models.
Models live in models/registry.py
"""

from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class NutrientPredictor:
    """
    Generic nutrient predictor interface.
    Wraps ML models (CatBoost, etc.)
    """

    def __init__(self, model_name: str, model_version: str):
        self.model_name = model_name
        self.model_version = model_version
        self.model = None  # Will be loaded from registry
        self.accuracy = 0.0
        self.last_used = None

    def predict(
        self,
        age: int,
        pregnancy_stage: Optional[str],
        breastfeeding: bool,
        recent_symptoms: list,
        days_since_last_check: int,
        **kwargs
    ) -> Tuple[float, float]:
        """
        Predict nutrient adequacy.
        
        Input features come from user data (age, pregnancy, symptoms, etc.)
        NOT from state (we're generating state signals, not using it).
        
        Args:
            age: Mother's age
            pregnancy_stage: Current stage
            breastfeeding: Is breastfeeding?
            recent_symptoms: List of recent symptoms
            days_since_last_check: How many days since last assessment?
            **kwargs: Other model-specific features
            
        Returns:
            (prediction, confidence)
            prediction: 0-1 float (adequacy level)
            confidence: 0-1 float (model's confidence in this prediction)
        """
        if self.model is None:
            logger.warning(f"Model {self.model_name} not loaded. Returning neutral signal.")
            return 0.5, 0.0

        try:
            # Prepare input features
            features = self._prepare_features(
                age, pregnancy_stage, breastfeeding, recent_symptoms, days_since_last_check, **kwargs
            )

            # Get prediction
            raw_prediction = self.model.predict(features)
            
            # Get confidence (from model's probability if available, else use accuracy)
            confidence = self._estimate_confidence(raw_prediction)

            logger.debug(
                f"{self.model_name}: prediction={raw_prediction:.2f}, "
                f"confidence={confidence:.2f}"
            )

            return float(raw_prediction), float(confidence)

        except Exception as e:
            logger.error(f"Prediction error in {self.model_name}: {e}")
            return 0.5, 0.0

    def _prepare_features(
        self,
        age: int,
        pregnancy_stage: Optional[str],
        breastfeeding: bool,
        recent_symptoms: list,
        days_since_last_check: int,
        **kwargs
    ) -> list:
        """
        Convert user data into model input features.
        This is data preprocessing, not state management.
        """
        # Map pregnancy stage to numeric
        pregnancy_map = {
            None: 0,
            "planning": 1,
            "first_trimester": 2,
            "second_trimester": 3,
            "third_trimester": 4,
        }

        features = [
            age,
            pregnancy_map.get(pregnancy_stage, 0),
            1 if breastfeeding else 0,
            len(recent_symptoms),  # Number of symptoms
            days_since_last_check,
        ]

        # Add any additional kwargs as features
        features.extend(kwargs.values())

        return [features]  # Wrap in list for sklearn-like API

    def _estimate_confidence(self, prediction: float) -> float:
        """
        Estimate model confidence in this prediction.
        
        Simple heuristic: 
        - Predictions near 0.5 = uncertain
        - Predictions near 0 or 1 = certain
        """
        distance_from_neutral = abs(prediction - 0.5)
        confidence = min(1.0, distance_from_neutral * 2)
        
        # Multiply by model's accuracy
        confidence *= self.accuracy
        
        return confidence

    def load_model(self, model_obj, accuracy: float):
        """Load a trained model."""
        self.model = model_obj
        self.accuracy = accuracy
        logger.info(f"Loaded {self.model_name} v{self.model_version} (accuracy: {accuracy:.2f})")

    def __repr__(self) -> str:
        status = "loaded" if self.model else "not_loaded"
        return f"NutrientPredictor({self.model_name} v{self.model_version}, {status})"


class DummyNutrientPredictor(NutrientPredictor):
    """
    Dummy predictor for testing (when real models aren't available).
    """

    def predict(self, **kwargs) -> Tuple[float, float]:
        """Return neutral signal for testing."""
        import random
        # Random signal between 0.3 and 0.7 (stays in middle range)
        prediction = 0.3 + random.random() * 0.4
        confidence = 0.5
        return prediction, confidence


class PredictorSuite:
    """
    Collection of all nutrient predictors.
    Manages model versioning and fallbacks.
    """

    def __init__(self):
        self.predictors: Dict[str, NutrientPredictor] = {}

    def register_predictor(self, nutrient: str, predictor: NutrientPredictor):
        """Register a predictor for a nutrient."""
        self.predictors[nutrient] = predictor
        logger.info(f"Registered predictor for {nutrient}: {predictor}")

    def predict_all(
        self,
        age: int,
        pregnancy_stage: Optional[str],
        breastfeeding: bool,
        recent_symptoms: list,
        days_since_last_check: int
    ) -> Dict[str, Tuple[float, float]]:
        """
        Get predictions for all nutrients.
        
        Returns:
            {
                "iron": (prediction, confidence),
                "protein": (prediction, confidence),
                ...
            }
        """
        results = {}

        for nutrient, predictor in self.predictors.items():
            prediction, confidence = predictor.predict(
                age=age,
                pregnancy_stage=pregnancy_stage,
                breastfeeding=breastfeeding,
                recent_symptoms=recent_symptoms,
                days_since_last_check=days_since_last_check
            )
            results[nutrient] = (prediction, confidence)

        return results

    def has_predictor(self, nutrient: str) -> bool:
        """Check if predictor exists for nutrient."""
        return nutrient in self.predictors

    def get_predictor(self, nutrient: str) -> Optional[NutrientPredictor]:
        """Get specific predictor."""
        return self.predictors.get(nutrient)

    def __repr__(self) -> str:
        return f"PredictorSuite({len(self.predictors)} predictors)"
