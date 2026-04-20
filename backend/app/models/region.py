from pydantic import BaseModel
from typing import List


class Region(BaseModel):
    id: str
    name: str
    country: str
    coordinates: List[float]  # [lat, lng] — centre point
    zoom_level: int
    recipe_ids: List[str]
