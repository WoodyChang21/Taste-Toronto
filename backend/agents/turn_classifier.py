from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=10)

_VALID = {"new_search", "refinement", "reaction", "chitchat"}

SYSTEM = """Classify the user's message into exactly one of these words:

new_search  — a fresh restaurant recommendation request
refinement  — adjusting or narrowing the previous search (different area, cheaper, vegetarian, more upscale, etc.)
reaction    — commenting on, questioning, or complaining about results already shown
chitchat    — greeting, thanks, off-topic, or anything unclear

Reply with only the single classification word. No punctuation."""


def turn_classifier_node(state: dict) -> dict:
    history = state.get("messages", [])[-4:]
    result = _llm.invoke(
        [SystemMessage(content=SYSTEM)]
        + list(history)
        + [HumanMessage(content=state["user_message"])]
    )
    turn_type = result.content.strip().lower()
    if turn_type not in _VALID:
        turn_type = "new_search"
    return {"turn_type": turn_type}
