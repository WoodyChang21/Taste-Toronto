from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from ..models.restaurant import RestaurantRecord

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

RESPONSE_SYSTEM = """You are Taste Toronto — a knowledgeable, opinionated local food guide for the Greater Toronto Area.
The restaurant cards will be displayed separately with full details. Your job is to write ONLY a brief 1-2 sentence
intro that sets the scene and explains why these picks are right for this specific request.

Rules:
- Write 1-2 plain sentences maximum. No headers, no bullet points, no markdown formatting.
- Be warm and direct. Reference the specific request and what makes these picks right.
- Do NOT list restaurant names, prices, or details — the cards already show that.
- Do NOT use ** bold **, ## headers, or any markdown syntax.
- IMPORTANT: If the actual cuisines returned do not match what the user requested (e.g. user asked for Taiwanese
  but results are Chinese), be honest about it. Acknowledge the gap and explain what you found instead.
  Example: "I don't have dedicated Taiwanese restaurants in my database, but these Chinese spots offer similar
  flavours and are the closest match for your group."
- Example (exact match): "For a cozy date night that's actually quiet enough to talk, these are the spots I'd send you to."
"""


def response_generator_node(state: dict) -> dict:
    intent = state.get("intent") or {}
    scored_data = state.get("scored", [])

    restaurants = [RestaurantRecord(**r) for r in scored_data]

    # Summarise what was actually returned so the LLM can be honest about mismatches
    actual_cuisines = list(dict.fromkeys(r.cuisine for r in restaurants if r.cuisine))
    actual_summary = ", ".join(
        f"{r.name} ({r.cuisine})" for r in restaurants
    ) if restaurants else "none"

    occasion_desc = intent.get("occasion") or "dining out"
    requested_cuisine = ", ".join(intent.get("cuisine") or []) or "open to anything"
    user_prompt = (
        f"The user wants: {occasion_desc}. "
        f"Group size: {intent.get('group_size')}. "
        f"Budget: {intent.get('budget')}. "
        f"Location: {intent.get('neighborhood') or 'Toronto'}. "
        f"Vibe: {', '.join(intent.get('vibe') or []) or 'no preference'}. "
        f"Requested cuisine: {requested_cuisine}. "
        f"Actual restaurants returned: {actual_summary}. "
        f"Actual cuisines in results: {', '.join(actual_cuisines) if actual_cuisines else 'mixed'}. "
        f"Write the 1-2 sentence intro."
    )

    ai_msg = _llm.invoke(
        [SystemMessage(content=RESPONSE_SYSTEM), HumanMessage(content=user_prompt)]
    )
    response_text = ai_msg.content

    return {
        "response": response_text,
        "messages": [AIMessage(content=response_text)],
        "shown_restaurant_ids": [r.id for r in restaurants],
    }
