from ..services.openai_client import chat_completion
from ..models.restaurant import RestaurantRecord

RESPONSE_SYSTEM = """You are Taste Toronto — a knowledgeable, opinionated local food guide for the Greater Toronto Area.
The restaurant cards will be displayed separately with full details. Your job is to write ONLY a brief 1-2 sentence
intro that sets the scene and explains why these picks are right for this specific request.

Rules:
- Write 1-2 plain sentences maximum. No headers, no bullet points, no markdown formatting.
- Be warm and direct. Reference the specific request and what makes these picks right.
- Do NOT list restaurant names, prices, or details — the cards already show that.
- Do NOT use ** bold **, ## headers, or any markdown syntax.
- Example: "For a cozy date night that's actually quiet enough to talk, these are the spots I'd send you to."
"""


def response_generator_node(state: dict) -> dict:
    intent = state["intent"]
    scored_data = state.get("scored", [])
    history = state.get("history", [])

    restaurants = [RestaurantRecord(**r) for r in scored_data]
    response = generate_response(restaurants, intent, history)
    return {**state, "response": response}


def generate_response(
    restaurants: list[RestaurantRecord],
    intent: dict,
    history: list[dict],
) -> str:
    occasion_desc = intent.get("occasion") or "dining out"
    user_prompt = (
        f"The user wants: {occasion_desc}. "
        f"Group size: {intent.get('group_size')}. "
        f"Budget: {intent.get('budget')}. "
        f"Location: {intent.get('neighborhood') or 'Toronto'}. "
        f"Vibe: {', '.join(intent.get('vibe') or []) or 'no preference'}. "
        f"Cuisine: {', '.join(intent.get('cuisine') or []) or 'open to anything'}. "
        f"Number of matches found: {len(restaurants)}. "
        f"Write the 1-2 sentence intro."
    )

    messages = history + [{"role": "user", "content": user_prompt}]
    return chat_completion(RESPONSE_SYSTEM, messages, max_tokens=120)
