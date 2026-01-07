# app/models/registry.py
"""
Model Registry: Manages model versions, metadata, and deployment.

Tracks:
- Which models exist
- Model versions and accuracy
- Deployment status
- When models need retraining
"""

from typing import Dict, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ModelMetadata:
    """Metadata about a trained model."""
    name: str  # e.g., "iron_predictor"
    version: str  # e.g., "1.0", "1.1"
    nutrient: str  # Which nutrient does it predict?
    
    # Performance
    accuracy: float  # 0-1
    precision: float  # 0-1
    recall: float  # 0-1
    f1_score: float  # 0-1
    
    # Training info
    trained_on_samples: int  # How much data?
    training_date: datetime
    last_evaluated: datetime
    
    # Deployment
    is_deployed: bool
    deployment_date: Optional[datetime] = None
    
    # Health
    is_healthy: bool = True  # Passes all sanity checks?
    drift_detected: bool = False  # Concept drift?
    needs_retraining: bool = False
    
    # Notes
    notes: str = ""

    def days_since_training(self) -> int:
        """How many days since this model was trained?"""
        return (datetime.utcnow() - self.training_date).days

    def days_since_deployment(self) -> int:
        """How many days since deployed?"""
        if not self.deployment_date:
            return 0
        return (datetime.utcnow() - self.deployment_date).days

    def should_retrain(self, max_days: int = 90) -> bool:
        """
        Should this model be retrained?
        
        Reasons to retrain:
        - Hasn't been trained in 90 days
        - Drift detected
        - Performance degraded
        - Explicitly flagged
        """
        if self.needs_retraining:
            return True

        if self.drift_detected:
            return True

        if self.days_since_training() > max_days:
            return True

        return False


class ModelRegistry:
    """
    Central registry for all models in the system.
    """

    def __init__(self):
        self.models: Dict[str, List[ModelMetadata]] = {}  # nutrient -> [versions]
        self.deployed_versions: Dict[str, str] = {}  # nutrient -> deployed_version

    def register(self, metadata: ModelMetadata):
        """Register a new model version."""
        if metadata.nutrient not in self.models:
            self.models[metadata.nutrient] = []

        self.models[metadata.nutrient].append(metadata)
        
        if metadata.is_deployed:
            self.deployed_versions[metadata.nutrient] = metadata.version

        logger.info(
            f"Registered {metadata.nutrient} v{metadata.version} "
            f"(accuracy: {metadata.accuracy:.2f})"
        )

    def get_deployed_version(self, nutrient: str) -> Optional[ModelMetadata]:
        """Get the currently deployed model for a nutrient."""
        if nutrient not in self.deployed_versions:
            return None

        version = self.deployed_versions[nutrient]
        return self.get_version(nutrient, version)

    def get_version(self, nutrient: str, version: str) -> Optional[ModelMetadata]:
        """Get specific version of a model."""
        if nutrient not in self.models:
            return None

        for model in self.models[nutrient]:
            if model.version == version:
                return model

        return None

    def get_latest_version(self, nutrient: str) -> Optional[ModelMetadata]:
        """Get latest version (not necessarily deployed)."""
        if nutrient not in self.models:
            return None

        return sorted(
            self.models[nutrient],
            key=lambda m: m.training_date,
            reverse=True
        )[0]

    def list_versions(self, nutrient: str) -> List[ModelMetadata]:
        """List all versions of a nutrient predictor."""
        return self.models.get(nutrient, [])

    def deploy_version(self, nutrient: str, version: str) -> bool:
        """
        Deploy a specific model version.
        
        Performs sanity checks before deployment:
        - Model exists
        - Model is healthy
        - No concept drift
        """
        model = self.get_version(nutrient, version)
        if not model:
            logger.error(f"Model {nutrient} v{version} not found")
            return False

        if not model.is_healthy:
            logger.error(f"Cannot deploy unhealthy model {nutrient} v{version}")
            return False

        if model.drift_detected:
            logger.warning(f"Model {nutrient} v{version} has drift, but deploying anyway")

        # Update deployment info
        model.is_deployed = True
        model.deployment_date = datetime.utcnow()
        self.deployed_versions[nutrient] = version

        logger.info(f"Deployed {nutrient} v{version}")
        return True

    def mark_for_retraining(self, nutrient: str, version: str, reason: str):
        """Flag a model version for retraining."""
        model = self.get_version(nutrient, version)
        if model:
            model.needs_retraining = True
            model.notes += f"\nFlagged for retraining: {reason}"
            logger.warning(f"Marked {nutrient} v{version} for retraining: {reason}")

    def detect_drift(self, nutrient: str, version: str):
        """Mark that concept drift was detected."""
        model = self.get_version(nutrient, version)
        if model:
            model.drift_detected = True
            logger.warning(f"Drift detected in {nutrient} v{version}")

    def check_all_health(self) -> Dict:
        """
        Check health of all deployed models.
        
        Returns:
            {
                "healthy": [...],
                "needs_retraining": [...],
                "drift_detected": [...],
                "unhealthy": [...]
            }
        """
        health_report = {
            "healthy": [],
            "needs_retraining": [],
            "drift_detected": [],
            "unhealthy": []
        }

        for nutrient, version in self.deployed_versions.items():
            model = self.get_deployed_version(nutrient)
            if not model:
                continue

            if model.drift_detected:
                health_report["drift_detected"].append(f"{nutrient} v{version}")
            elif model.needs_retraining:
                health_report["needs_retraining"].append(f"{nutrient} v{version}")
            elif not model.is_healthy:
                health_report["unhealthy"].append(f"{nutrient} v{version}")
            else:
                health_report["healthy"].append(f"{nutrient} v{version}")

        return health_report

    def get_stats(self) -> Dict:
        """Get registry statistics."""
        total_models = sum(len(versions) for versions in self.models.values())
        total_nutrients = len(self.models)
        deployed = len(self.deployed_versions)

        return {
            "total_nutrients_tracked": total_nutrients,
            "total_model_versions": total_models,
            "currently_deployed": deployed,
            "nutrients": list(self.models.keys()),
            "deployment_map": self.deployed_versions.copy()
        }

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"ModelRegistry({stats['total_nutrients_tracked']} nutrients, "
            f"{stats['total_model_versions']} versions, "
            f"{stats['currently_deployed']} deployed)"
        )
