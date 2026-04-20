from pydantic import BaseModel
from typing import List, Optional


class Ingredient(BaseModel):
    amount: str
    unit: Optional[str] = None
    item: str


class RecipeStep(BaseModel):
    step: int
    instruction: str


class Recipe(BaseModel):
    id: str
    name: str
    region: str
    country: str
    coordinates: List[float]  # [lat, lng]
    short_description: str
    history: str
    ingredients: List[Ingredient]
    steps: List[RecipeStep]
    prep_time_mins: int
    cook_time_mins: int
    serves: int
    image_url: Optional[str] = None
    tags: List[str] = []
