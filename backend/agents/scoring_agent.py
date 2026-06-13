from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import json

from ..models.restaurant import RestaurantRecord, ScoredRestaurant

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


class _RankedResult(BaseModel):
    id: str
    rank: int
    reasoning: str  # 1-2 sentences shown on the card


class _RerankerOutput(BaseModel):
    results: list[_RankedResult]


_structured_llm = _llm.with_structured_output(_RerankerOutput)

RERANKER_SYSTEM = """You are a Toronto restaurant expert ranking candidates for a user's specific request.

Given the user's intent and a list of candidate restaurants, select and rank the TOP 5 best matches.
Return exactly 5 results (or fewer if fewer candidates exist).

Rules:
- Rank by overall fit: occasion, budget, cuisine, neighborhood, noise level, group size, dietary needs, amenities
- If dietary restrictions are specified (vegetarian, vegan, halal, gluten_free), EXCLUDE restaurants that don't support them unless semantic_tags explicitly include the restriction
- If shown_restaurant_ids is non-empty, down-rank those restaurants unless no better options exist
- If liked_ids is non-empty, favor restaurants with similar cuisine/vibe/neighborhood
- If disliked_ids is non-empty, avoid restaurants with similar characteristics
- reasoning must be 1-2 sentences: specific, warm, and reference WHY this place fits THIS request
- Never use generic phrases like "great choice" — always name a concrete detail (dish, atmosphere, feature)
"""


def scoring_node(state: dict) -> dict:
    intent = state.get("intent") or {}
    candidates_data = state.get("candidates", [])

    if not candidates_data:
        return {"scored": []}

    feedback = state.get("user_feedback") or {}
    shown_ids = state.get("shown_restaurant_ids") or []
    liked_ids = feedback.get("liked", [])
    disliked_ids = feedback.get("disliked", [])

    candidates = [RestaurantRecord(**r) for r in candidates_data]

    candidate_summaries = []
    for r in candidates:
        candidate_summaries.append({
            "id": r.id,
            "name": r.name,
            "cuisine": r.cuisine,
            "price_range": r.price_range,
            "neighborhood": r.neighborhood,
            "noise_level": r.noise_level,
            "rating": r.rating,
            "review_count": r.review_count,
            "semantic_tags": r.semantic_tags,
            "description": r.description,
        })

    user_prompt = json.dumps({
        "intent": {
            "occasion": intent.get("occasion"),
            "group_size": intent.get("group_size"),
            "budget": intent.get("budget"),
            "neighborhood": intent.get("neighborhood"),
            "vibe": intent.get("vibe") or [],
            "cuisine": intent.get("cuisine") or [],
            "dietary": intent.get("dietary") or [],
            "meal_type": intent.get("meal_type"),
            "amenities": intent.get("amenities") or [],
        },
        "shown_restaurant_ids": shown_ids,
        "liked_ids": liked_ids,
        "disliked_ids": disliked_ids,
        "candidates": candidate_summaries,
    }, ensure_ascii=False, indent=2)

    output: _RerankerOutput = _structured_llm.invoke([
        SystemMessage(content=RERANKER_SYSTEM),
        HumanMessage(content=user_prompt),
    ])

    ranked_ids = {r.id: r for r in output.results}
    scored: list[ScoredRestaurant] = []
    for r in candidates:
        ranked = ranked_ids.get(r.id)
        if ranked is None:
            continue
        scored.append(ScoredRestaurant(
            **r.model_dump(),
            final_score=max(0, 100 - (ranked.rank - 1) * 15),
            score_reasoning=ranked.reasoning,
        ))

    scored.sort(key=lambda x: x.final_score, reverse=True)
    return {"scored": [r.model_dump() for r in scored[:5]]}
