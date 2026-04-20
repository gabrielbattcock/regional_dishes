from fastapi import APIRouter, HTTPException
from typing import List
from app.models.region import Region
from app.services.data_loader import load_regions

router = APIRouter()


@router.get("/", response_model=List[Region])
def list_regions():
    """Return all regions available on the map."""
    return load_regions()


@router.get("/{region_id}", response_model=Region)
def get_region(region_id: str):
    """Return a single region by ID."""
    regions = load_regions()
    region = next((r for r in regions if r.id == region_id), None)
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    return region
