from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.types import Command
from langgraph.graph import END

from ..db import restaurant_repo

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)


class _PivotIntent(BaseModel):
    budget: str | None = None
    neighborhood: str | None = None
    cuisine: list[str] | None = None
    vibe: list[str] | None = None
    occasion: str | None = None
    dietary: list[str] | None = None
    meal_type: str | None = None
    amenities: list[str] | None = None


class _ReactionOutput(BaseModel):
    response: str                    # conversational reply always shown to user
    is_pivot: bool                   # True = user wants different results now
    pivot_intent: _PivotIntent | None  # partial intent fields to merge (only when is_pivot)


_structured_llm = _llm.with_structured_output(_ReactionOutput)

SYSTEM = """You are Taste Toronto — a warm, opinionated local food guide.

The user is reacting to or questioning restaurant recommendations already shown to them.

1. Write a brief, warm conversational reply (2-3 sentences max, no markdown, no bullet points).
2. Decide if the user wants DIFFERENT results right now (is_pivot=true) or is just commenting/asking (is_pivot=false).

is_pivot=true when the user says things like:
- "too expensive", "cheaper options?", "something quieter", "different neighbourhood"
- "not really my style", "anything more casual", "show me something vegetarian"
- "hmm none of these feel right", "can you try again"

is_pivot=false when the user says things like:
- "interesting!", "thanks", "I'll check them out", "what makes X special?"
- asking about a specific restaurant already shown

When is_pivot=true, also fill pivot_intent with ONLY the fields the user explicitly changed
(e.g. {"budget": "$", "neighborhood": "Kensington"} — omit unchanged fields).
When is_pivot=false, set pivot_intent to null.

Useful pivots to mention in your response (pick 1-2 relevant ones):
- Try a different neighbourhood
- Open up or change the cuisine
- Adjust the budget up or down
- Change the vibe (quieter, livelier, more casual, more upscale)
"""


def reaction_responder_node(state: dict) -> dict | Command:
    intent = state.get("intent") or {}
    shown_ids = state.get("shown_restaurant_ids") or []

    shown_names: list[str] = []
    if shown_ids:
        restaurants = restaurant_repo.get_by_ids(shown_ids)
        shown_names = [r.name for r in restaurants]

    intent_summary = (
        f"cuisine={intent.get('cuisine') or 'any'}, "
        f"budget={intent.get('budget') or 'any'}, "
        f"neighborhood={intent.get('neighborhood') or 'anywhere in Toronto'}, "
        f"vibe={intent.get('vibe') or 'no preference'}"
    )
    context = (
        f"Results previously shown: {', '.join(shown_names) if shown_names else 'none yet'}.\n"
        f"Search filters active: {intent_summary}."
    )

    output: _ReactionOutput = _structured_llm.invoke([
        SystemMessage(content=SYSTEM),
        HumanMessage(content=f"{context}\n\nUser says: {state['user_message']}"),
    ])

    base_updates = {
        "response": output.response,
        "scored": [],
        "messages": [AIMessage(content=output.response)],
    }

    if output.is_pivot and output.pivot_intent:
        # Merge pivot fields into current intent; intent_mutator will refine further
        pivot_dict = {k: v for k, v in output.pivot_intent.model_dump().items() if v is not None}
        merged_intent = {**intent, **pivot_dict}
        return Command(
            goto="intent_mutator",
            update={**base_updates, "intent": merged_intent},
        )

    return Command(goto=END, update=base_updates)
