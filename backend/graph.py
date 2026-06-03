from typing import TypedDict
from langgraph.graph import StateGraph, END

from .agents.intent_extractor import intent_extractor_node
from .agents.restaurant_retriever import retriever_node
from .agents.scoring_agent import scoring_node
from .agents.response_generator import response_generator_node


class TasteState(TypedDict, total=False):
    session_id: str
    user_message: str
    history: list[dict]
    intent: dict | None
    candidates: list[dict]
    scored: list[dict]
    response: str
    needs_followup: bool


def _route_after_intent(state: TasteState) -> str:
    if state.get("needs_followup"):
        return END
    return "restaurant_retriever"


def build_graph() -> StateGraph:
    g = StateGraph(TasteState)

    g.add_node("intent_extractor", intent_extractor_node)
    g.add_node("restaurant_retriever", retriever_node)
    g.add_node("scoring_agent", scoring_node)
    g.add_node("response_generator", response_generator_node)

    g.set_entry_point("intent_extractor")
    g.add_conditional_edges("intent_extractor", _route_after_intent)
    g.add_edge("restaurant_retriever", "scoring_agent")
    g.add_edge("scoring_agent", "response_generator")
    g.add_edge("response_generator", END)

    return g


taste_graph = build_graph().compile()
