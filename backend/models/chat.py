from __future__ import annotations
from pydantic import BaseModel
from .intent import Intent
from .restaurant import RestaurantRecord


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    message: str
    restaurants: list[RestaurantRecord] = []
    intent: Intent | None = None
    needs_followup: bool = False
