# app/knowledge/nutrition.py
"""
Nutrition Knowledge Base: Static facts about nutrition.

NOT learned from data. NOT from ML models. Static facts.
Why? Because nutrition science is well-established.

This is the "slow knowledge" that doesn't change.
In future, can become RAG (retrieval-augmented generation).
"""

from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class NutritionKnowledgeBase:
    """
    Static nutrition facts for pregnant and nursing women.
    
    Data structure:
    - Nutrients: what they do, deficiency symptoms, sources
    - Foods: nutritional content, safety info, recommendations
    - Recipes: simple combinations
    """

    # Nutrient details
    NUTRIENTS = {
        "iron": {
            "role": "Oxygen transport, prevents anemia",
            "daily_need_mg": {
                "planning": 18,
                "pregnant": 27,
                "breastfeeding": 10
            },
            "deficiency_symptoms": ["fatigue", "shortness_of_breath", "dizziness", "pale_skin"],
            "best_sources_vegetarian": ["spinach", "lentils", "beans", "fortified_cereals"],
            "best_sources_nonveg": ["red_meat", "chicken", "fish", "eggs"],
            "absorption_enhancers": ["vitamin_c", "citrus", "tomato"],
            "absorption_blockers": ["tea", "coffee", "calcium_excess"]
        },
        "protein": {
            "role": "Fetal growth, tissue repair, energy",
            "daily_need_grams": {
                "planning": 50,
                "pregnant": 70,
                "breastfeeding": 70
            },
            "deficiency_symptoms": ["weakness", "slow_healing", "low_energy"],
            "best_sources": ["eggs", "milk", "yogurt", "chicken", "fish", "beans", "nuts"],
            "tips": "Spread throughout the day"
        },
        "calcium": {
            "role": "Fetal bone development, mother's bone health, muscle function",
            "daily_need_mg": {
                "planning": 1000,
                "pregnant": 1000,
                "breastfeeding": 1000
            },
            "deficiency_symptoms": ["muscle_cramps", "weak_bones", "dental_problems"],
            "best_sources": ["milk", "yogurt", "cheese", "fortified_milk", "leafy_greens"],
            "tips": "Better absorbed with vitamin D"
        },
        "folic": {
            "role": "Neural tube development, prevents birth defects",
            "daily_need_mcg": {
                "planning": 400,
                "pregnant": 600,
                "breastfeeding": 500
            },
            "deficiency_symptoms": ["anemia", "birth_defects", "fatigue"],
            "best_sources": ["leafy_greens", "lentils", "asparagus", "broccoli", "fortified_grains"],
            "tips": "Critical in first trimester. Often supplemented."
        },
        "vitamin_b12": {
            "role": "Energy metabolism, nerve function, red blood cells",
            "daily_need_mcg": {
                "planning": 2.4,
                "pregnant": 2.6,
                "breastfeeding": 2.8
            },
            "deficiency_symptoms": ["fatigue", "numbness", "anemia"],
            "best_sources": ["eggs", "milk", "meat", "fish", "fortified_cereals"],
            "tips": "Only in animal products (vegetarians need supplements)"
        },
        "iodine": {
            "role": "Thyroid function, fetal brain development",
            "daily_need_mcg": {
                "planning": 150,
                "pregnant": 220,
                "breastfeeding": 290
            },
            "deficiency_symptoms": ["goiter", "fatigue", "brain_effects_in_fetus"],
            "best_sources": ["iodized_salt", "fish", "seaweed", "eggs", "dairy"],
            "tips": "Use iodized salt"
        },
        "vitamin_d": {
            "role": "Calcium absorption, immune function",
            "daily_need_iu": {
                "planning": 600,
                "pregnant": 600,
                "breastfeeding": 600
            },
            "deficiency_symptoms": ["weak_bones", "muscle_pain", "depression"],
            "best_sources": ["sunlight", "fatty_fish", "eggs", "fortified_milk"],
            "tips": "15-20 minutes daily sun exposure helps"
        }
    }

    # Common foods for pregnant/nursing women
    FOODS = {
        "spinach": {
            "nutrients": {"iron": "high", "folic": "high", "calcium": "medium"},
            "cautions": None,
            "safe_during": ["planning", "pregnant", "breastfeeding"],
            "taste": "Cooked spinach is mild. Raw in salads too."
        },
        "lentils": {
            "nutrients": {"protein": "high", "iron": "medium", "folic": "high"},
            "cautions": None,
            "safe_during": ["planning", "pregnant", "breastfeeding"],
            "taste": "Earthy, pairs well with rice and vegetables"
        },
        "eggs": {
            "nutrients": {"protein": "high", "choline": "high", "iron": "medium"},
            "cautions": "Must be cooked (not raw)",
            "safe_during": ["planning", "pregnant", "breastfeeding"],
            "taste": "Versatile, easy to cook"
        },
        "milk": {
            "nutrients": {"calcium": "high", "protein": "high", "vitamin_d": "medium"},
            "cautions": "Must be pasteurized",
            "safe_during": ["planning", "pregnant", "breastfeeding"],
            "taste": "Drink warm or cold, or use in cooking"
        },
        "yogurt": {
            "nutrients": {"calcium": "high", "protein": "medium", "probiotics": "high"},
            "cautions": "Must be pasteurized",
            "safe_during": ["planning", "pregnant", "breastfeeding"],
            "taste": "Creamy, can add fruits"
        },
        "red_meat": {
            "nutrients": {"iron": "high", "protein": "high", "vitamin_b12": "high"},
            "cautions": "Must be cooked thoroughly",
            "safe_during": ["planning", "pregnant", "breastfeeding"],
            "taste": "Rich, satisfying"
        },
        "chicken": {
            "nutrients": {"protein": "high", "iron": "medium", "b_vitamins": "high"},
            "cautions": "Must be cooked thoroughly",
            "safe_during": ["planning", "pregnant", "breastfeeding"],
            "taste": "Mild, versatile"
        },
        "fish": {
            "nutrients": {"omega3": "high", "protein": "high", "vitamin_d": "medium"},
            "cautions": "Avoid high-mercury fish (shark, swordfish). Low mercury fish OK.",
            "safe_during": ["planning", "pregnant", "breastfeeding"],
            "taste": "Varies by type"
        },
        "jaggery": {
            "nutrients": {"iron": "medium", "minerals": "medium"},
            "cautions": None,
            "safe_during": ["planning", "pregnant", "breastfeeding"],
            "taste": "Sweet, molasses-like flavor"
        },
        "dates": {
            "nutrients": {"iron": "medium", "fiber": "high", "minerals": "medium"},
            "cautions": None,
            "safe_during": ["planning", "pregnant", "breastfeeding"],
            "taste": "Sweet, sticky"
        },
        "almonds": {
            "nutrients": {"protein": "medium", "calcium": "medium", "healthy_fats": "high"},
            "cautions": None,
            "safe_during": ["planning", "pregnant", "breastfeeding"],
            "taste": "Nutty"
        },
        "broccoli": {
            "nutrients": {"calcium": "medium", "folic": "medium", "fiber": "high"},
            "cautions": None,
            "safe_during": ["planning", "pregnant", "breastfeeding"],
            "taste": "Mild when cooked"
        }
    }

    # Simple meal ideas
    MEAL_IDEAS = {
        "iron_boosting": [
            "Spinach + jaggery + almonds",
            "Lentil soup with tomatoes (vitamin C enhances iron)",
            "Red meat with rice and greens",
            "Egg omelette with spinach"
        ],
        "protein_rich": [
            "Egg curry with roti",
            "Lentil dal with rice",
            "Grilled chicken with vegetables",
            "Yogurt with nuts and fruit"
        ],
        "calcium_rich": [
            "Milk with turmeric and nuts",
            "Paneer (cottage cheese) with vegetables",
            "Yogurt parfait with granola",
            "Cheese and whole grain bread"
        ],
        "quick_snacks": [
            "Almonds or walnuts",
            "Dates",
            "Yogurt",
            "Milk-based drink",
            "Hard-boiled egg"
        ]
    }

    def get_nutrient_info(self, nutrient: str) -> Optional[Dict]:
        """Get detailed information about a nutrient."""
        return self.NUTRIENTS.get(nutrient)

    def get_daily_need(self, nutrient: str, pregnancy_stage: Optional[str]) -> Optional[float]:
        """Get daily recommended amount for a nutrient."""
        nutrient_info = self.get_nutrient_info(nutrient)
        if not nutrient_info:
            return None

        # Try different unit names
        for unit_key in ["daily_need_mg", "daily_need_grams", "daily_need_mcg", "daily_need_iu"]:
            if unit_key in nutrient_info:
                return nutrient_info[unit_key].get(pregnancy_stage or "planning")

        return None

    def get_food_info(self, food: str) -> Optional[Dict]:
        """Get information about a food."""
        return self.FOODS.get(food)

    def is_food_safe(
        self,
        food: str,
        pregnancy_stage: Optional[str] = None
    ) -> bool:
        """Is this food safe during this stage?"""
        food_info = self.get_food_info(food)
        if not food_info:
            return False

        safe_stages = food_info.get("safe_during", [])
        stage = pregnancy_stage or "planning"
        
        return stage in safe_stages

    def get_food_caution(self, food: str) -> Optional[str]:
        """Get any cautions about a food."""
        food_info = self.get_food_info(food)
        if food_info:
            return food_info.get("cautions")
        return None

    def suggest_for_nutrient(self, nutrient: str) -> List[Dict]:
        """
        Suggest foods rich in this nutrient.
        Returns list of {food, nutrients, tips}
        """
        suggestions = []
        
        nutrient_info = self.get_nutrient_info(nutrient)
        if not nutrient_info:
            return suggestions

        # Find foods that contain this nutrient
        for food, food_info in self.FOODS.items():
            nutrients = food_info.get("nutrients", {})
            if nutrient in nutrients:
                suggestions.append({
                    "food": food,
                    "richness": nutrients[nutrient],
                    "caution": food_info.get("cautions"),
                    "safe": self.is_food_safe(food, "pregnant")
                })

        return sorted(suggestions, key=lambda x: x["richness"] == "high", reverse=True)

    def __repr__(self) -> str:
        return (
            f"NutritionKnowledgeBase("
            f"{len(self.NUTRIENTS)} nutrients, "
            f"{len(self.FOODS)} foods)"
        )
