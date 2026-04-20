from fastapi import APIRouter, HTTPException
from typing import List
from app.models.recipe import Recipe
from app.services.data_loader import load_recipes, get_recipe_by_id, get_recipes_by_region

router = APIRouter()


@router.get("/", response_model=List[Recipe])
def list_recipes():
    """Return all recipes."""
    return load_recipes()


@router.get("/{recipe_id}", response_model=Recipe)
def get_recipe(recipe_id: str):
    """Return a single recipe by ID."""
    recipe = get_recipe_by_id(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


@router.get("/region/{region_id}", response_model=List[Recipe])
def recipes_by_region(region_id: str):
    """Return all recipes for a given region."""
    return get_recipes_by_region(region_id)
