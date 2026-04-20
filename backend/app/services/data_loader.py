import json
import os
from typing import List, Optional
from app.models.recipe import Recipe
from app.models.region import Region

DATA_DIR = os.path.join(os.path.dirname(__file__), "../../data")


def load_recipes() -> List[Recipe]:
    path = os.path.join(DATA_DIR, "recipes.json")
    with open(path, "r") as f:
        raw = json.load(f)
    return [Recipe(**item) for item in raw]


def load_regions() -> List[Region]:
    path = os.path.join(DATA_DIR, "regions.json")
    with open(path, "r") as f:
        raw = json.load(f)
    return [Region(**item) for item in raw]


def get_recipe_by_id(recipe_id: str) -> Optional[Recipe]:
    recipes = load_recipes()
    return next((r for r in recipes if r.id == recipe_id), None)


def get_recipes_by_region(region_id: str) -> List[Recipe]:
    recipes = load_recipes()
    return [r for r in recipes if r.region == region_id]
