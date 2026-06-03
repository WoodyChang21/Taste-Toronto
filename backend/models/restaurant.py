from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class RestaurantRecord(BaseModel):
    id: str
    name: str
    address: str
    neighborhood: str
    cuisine: str
    price_range: str
    rating: float
    review_count: int
    phone: str | None = None
    website: str | None = None
    reservation_url: str | None = None
    noise_level: Literal["quiet", "moderate", "lively"] | None = None
    parking: bool | None = None
    semantic_tags: list[str] = []
    occasion_scores: dict[str, int] = {}
    description: str = ""
    latitude: float | None = None
    longitude: float | None = None
    google_maps_url: str | None = None


class ScoredRestaurant(RestaurantRecord):
    final_score: int = 0
    score_reasoning: str = ""
