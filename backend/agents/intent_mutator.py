from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from ..models.intent import Intent

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
_structured = _llm.with_structured_output(Intent)

SYSTEM = """You are refining a restaurant search for Taste Toronto.

The user is adjusting — NOT replacing — their previous request.
Return the COMPLETE updated intent. Copy every field from the current intent, then modify
only what the user explicitly changed.

Current intent:
{current_intent}

Budget rules: under $30/person → "$", $30-60 → "$$", $60-100 → "$$$", over $100 → "$$$$"
is_complete=true only when both group_size AND budget are non-null.
If the user removes a filter (e.g. "any cuisine"), set that field to null or [].
Carry forward dietary, meal_type, and amenities from the current intent unless the user explicitly changes them.
"""


def intent_mutator_node(state: dict) -> dict:
    existing = state.get("intent") or {}
    updated: Intent = _structured.invoke([
        SystemMessage(content=SYSTEM.format(current_intent=existing)),
        HumanMessage(content=state["user_message"]),
    ])
    return {"intent": updated.model_dump()}
