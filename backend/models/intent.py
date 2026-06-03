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
    is_complete: bool = False
    needs_followup: bool = True
    followup_question: str | None = None
    missing_fields: list[str] = []
