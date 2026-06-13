from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class Intent(BaseModel):
    occasion: str | None = None
    group_size: int | None = None
    budget: Literal["$", "$$", "$$$", "$$$$"] | None = None
    neighborhood: str | None = None
    vibe: list[str] = []
    cuisine: list[str] = []
    dietary: list[str] = []       # e.g. ["vegetarian", "vegan", "halal", "gluten_free"]
    meal_type: str | None = None  # "lunch" | "dinner" | "brunch" | "late_night"
    amenities: list[str] = []     # e.g. ["patio", "parking", "live_music", "reservable"]
    is_complete: bool = False
    needs_followup: bool = True
    followup_question: str | None = None
    missing_fields: list[str] = []
