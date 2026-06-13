from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from ..models.intent import Intent

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
_structured_llm = _llm.with_structured_output(Intent)

SYSTEM_PROMPT = """You are an intent extraction engine for Taste Toronto, a restaurant recommendation app for the Greater Toronto Area.
Extract structured intent from the user's message given the full conversation history.

Rules:
- "occasion" is a free-form string capturing what the user wants (e.g. "birthday dinner", "work team lunch", "late night spot", "casual hangout", "hidden gem"). Can be null.
- CRITICAL: is_complete=true and needs_followup=false only when BOTH group_size AND budget are non-null.
- CRITICAL: needs_followup=true only when group_size OR budget is still null.
- Ask for ONE missing field at a time: group_size first, then budget. NEVER ask about vibe, cuisine, neighborhood, occasion, dietary, meal_type, or amenities.
- followup_question must be warm and conversational, never robotic.
- Budget mapping: under $30/person → "$", $30–60 → "$$", $60–100 → "$$$", over $100 → "$$$$"
- "cheap" / "casual" → "$", "mid-range" → "$$", "date night" without budget → assume "$$$"
- "splurge" / "special occasion" / "fine dining" → "$$$$"
- If the user says "just the two of us" or implies a couple/date → group_size=2
- If a user sends something specific enough (e.g. "best ramen in Kensington") with implied group/budget — infer them and set is_complete=true.
- Carry forward context from earlier turns (the history is provided).
- Vibe/cuisine/neighborhood are optional enrichment — extract if mentioned, never ask.
- dietary: extract if mentioned (e.g. "vegetarian", "vegan", "halal", "gluten_free"). Never ask.
- meal_type: extract if mentioned ("lunch", "dinner", "brunch", "late_night"). Never ask.
- amenities: extract if mentioned (e.g. "patio", "parking", "live_music", "reservable"). Never ask.
"""


def intent_extractor_node(state: dict) -> dict:
    # For new searches, start fresh — don't carry forward old cuisine/filters
    turn_type = state.get("turn_type", "new_search")
    existing_intent = state.get("intent") if turn_type != "new_search" else None
    messages = state.get("messages", [])
    user_message = state["user_message"]

    existing_context = ""
    if existing_intent:
        filled = {
            k: v
            for k, v in existing_intent.items()
            if v and k not in ("needs_followup", "is_complete", "followup_question", "missing_fields")
        }
        if filled:
            existing_context = (
                f"\n\nFields already confirmed from prior turns "
                f"(preserve these, do not re-ask): {filled}"
            )

    intent: Intent = _structured_llm.invoke(
        [SystemMessage(content=SYSTEM_PROMPT + existing_context)]
        + list(messages[-10:])
        + [HumanMessage(content=user_message)]
    )

    return {
        "messages": [HumanMessage(content=user_message)],
        "intent": intent.model_dump(),
    }
