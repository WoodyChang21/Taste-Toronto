import json
from ..services.openai_client import chat_completion

SYSTEM_PROMPT = """You are an intent extraction engine for Taste Toronto, a restaurant recommendation app for the Greater Toronto Area.
Extract structured intent from the user's message given the full conversation history. Respond with valid JSON only.

JSON schema:
{
  "occasion": string | null,
  "group_size": integer | null,
  "budget": "$" | "$$" | "$$$" | "$$$$" | null,
  "neighborhood": string | null,
  "vibe": [string],
  "cuisine": [string],
  "is_complete": boolean,
  "needs_followup": boolean,
  "followup_question": string | null,
  "missing_fields": [string]
}

Rules:
- "occasion" is a free-form string capturing what the user wants (e.g. "birthday dinner", "work team lunch", "late night spot", "casual hangout", "hidden gem"). Can be null.
- CRITICAL: is_complete=true and needs_followup=false when BOTH group_size AND budget are non-null. No other conditions.
- CRITICAL: needs_followup=true only when group_size OR budget is still null.
- Ask for ONE missing field at a time: group_size first, then budget. NEVER ask about vibe, cuisine, neighborhood, or occasion.
- followup_question must be warm and conversational, never robotic.
- Budget mapping: under $30/person → "$", $30–60 → "$$", $60–100 → "$$$", over $100 → "$$$$"
- "cheap" / "casual" → "$", "mid-range" → "$$", "date night" without budget → assume "$$$", set budget="$$$"
- "splurge" / "special occasion" / "fine dining" → "$$$$"
- If the user says "just the two of us" or implies a couple/date → group_size=2
- If a user sends something specific enough (e.g. "best ramen in Kensington") with implied group/budget — infer them and set is_complete=true.
- Carry forward context from earlier turns (the history is provided).
- Vibe/cuisine/neighborhood are optional enrichment — extract them if mentioned but never ask for them.
"""


def intent_extractor_node(state: dict) -> dict:
    history = state.get("history", [])
    user_message = state["user_message"]

    messages = history + [{"role": "user", "content": user_message}]
    raw = chat_completion(SYSTEM_PROMPT, messages, json_mode=True, max_tokens=512)
    intent_data = json.loads(raw)

    # Normalize list fields — GPT occasionally returns null/0/string instead of []
    for field in ("vibe", "cuisine", "missing_fields"):
        val = intent_data.get(field)
        if not isinstance(val, list):
            intent_data[field] = [str(val)] if val else []

    return {**state, "intent": intent_data, "needs_followup": intent_data.get("needs_followup", True)}
