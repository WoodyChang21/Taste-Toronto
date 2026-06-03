import json
from ..services.openai_client import chat_completion
from ..models.restaurant import RestaurantRecord, ScoredRestaurant

SCORING_SYSTEM = """You are a restaurant scoring engine for Toronto. Score each restaurant 0–100 based on how well it fits the user's specific request.

Scoring signals (apply all that are relevant):
- Cuisine match: if the user specified a cuisine, treat it as a strong preference. A non-matching cuisine should lose 40–50 points — a Japanese restaurant should not beat a Korean restaurant when the user asked for Korean, even if the Japanese restaurant has better occasion scores
- Occasion/vibe fit: use the pre-computed occasion_scores (date_night, birthday, family_gathering, hidden_gem) as a meaningful signal — these are 0–100 and reflect restaurant character
- Budget fit: restaurants outside the user's budget range lose 20–30 points
- Group size fit: if the user has a large group and the restaurant is intimate/small, reduce score
- Neighborhood match: if the user specified a neighborhood, boost nearby restaurants
- Hidden gem: if the user wants something undiscovered — fewer reviews + high rating = higher score

Respond with valid JSON only — an array:
[{"id": "...", "score": 0-100, "reasoning": "one sentence max"}]
"""


def scoring_node(state: dict) -> dict:
    intent = state["intent"]
    candidates_data = state.get("candidates", [])

    if not candidates_data:
        return {**state, "scored": []}

    candidates = [RestaurantRecord(**r) for r in candidates_data]
    scored = score_restaurants(candidates, intent)
    return {**state, "scored": [r.model_dump() for r in scored]}


def score_restaurants(
    candidates: list[RestaurantRecord], intent: dict
) -> list[ScoredRestaurant]:
    summary = [
        {
            "id": r.id,
            "name": r.name,
            "cuisine": r.cuisine,
            "price_range": r.price_range,
            "rating": r.rating,
            "review_count": r.review_count,
            "noise_level": r.noise_level,
            "parking": r.parking,
            "semantic_tags": r.semantic_tags,
            "occasion_scores": r.occasion_scores,
        }
        for r in candidates
    ]

    occasion_desc = intent.get("occasion") or "general dining"
    prompt = (
        f"User request: {occasion_desc}\n"
        f"Group size: {intent.get('group_size')}\n"
        f"Budget: {intent.get('budget')}\n"
        f"Vibe preferences: {intent.get('vibe')}\n"
        f"Cuisine preferences: {intent.get('cuisine')}\n"
        f"Neighborhood: {intent.get('neighborhood')}\n\n"
        f"Restaurants:\n{json.dumps(summary, indent=2)}"
    )

    raw = chat_completion(
        SCORING_SYSTEM,
        [{"role": "user", "content": prompt}],
        json_mode=True,
        max_tokens=2048,
    )
    scores_data = json.loads(raw)

    if isinstance(scores_data, dict):
        scores_list = next(iter(scores_data.values()))
    else:
        scores_list = scores_data

    score_map = {s["id"]: s for s in scores_list}
    scored: list[ScoredRestaurant] = []
    for r in candidates:
        entry = score_map.get(r.id)
        if entry:
            scored.append(
                ScoredRestaurant(
                    **r.model_dump(),
                    final_score=entry["score"],
                    score_reasoning=entry.get("reasoning", ""),
                )
            )

    return sorted(scored, key=lambda x: x.final_score, reverse=True)[:5]
