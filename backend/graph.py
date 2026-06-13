from pathlib import Path
from typing import Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, RetryPolicy

from .agents.turn_classifier import turn_classifier_node
from .agents.intent_extractor import intent_extractor_node
from .agents.intent_mutator import intent_mutator_node
from .agents.reaction_responder import reaction_responder_node
from .agents.chitchat_responder import chitchat_responder_node
from .agents.restaurant_retriever import retriever_node
from .agents.scoring_agent import scoring_node
from .agents.response_generator import response_generator_node

_DB_PATH = str(Path(__file__).parent / "data" / "taste_toronto.db")


class TasteState(TypedDict):
    user_message: str
    messages: Annotated[list[BaseMessage], add_messages]
    intent: dict | None
    candidates: list[dict]
    scored: list[dict]
    response: str
    turn_type: str | None
    shown_restaurant_ids: list[str]
    user_feedback: dict  # {"liked": [...ids], "disliked": [...ids]}


def followup_node(state: TasteState) -> dict:
    question = (state.get("intent") or {}).get(
        "followup_question", "Could you tell me a bit more?"
    )
    answer = interrupt({"question": question})
    return {"user_message": answer}


def _route_by_turn(state: TasteState) -> str:
    turn = state.get("turn_type") or "new_search"
    return {
        "new_search": "intent_extractor",
        "refinement": "intent_mutator",
        "reaction": "reaction_responder",
        "chitchat": "chitchat_responder",
    }.get(turn, "intent_extractor")


def _route_after_intent(state: TasteState) -> str:
    intent = state.get("intent") or {}
    if intent.get("needs_followup"):
        return "followup"
    return "restaurant_retriever"


def build_graph() -> StateGraph:
    g = StateGraph(TasteState)

    g.add_node("turn_classifier", turn_classifier_node)
    g.add_node(
        "intent_extractor",
        intent_extractor_node,
        retry_policy=RetryPolicy(max_attempts=3),
    )
    g.add_node("intent_mutator", intent_mutator_node)
    g.add_node("followup", followup_node)
    g.add_node("reaction_responder", reaction_responder_node)
    g.add_node("chitchat_responder", chitchat_responder_node)
    g.add_node("restaurant_retriever", retriever_node)
    g.add_node("scoring_agent", scoring_node)
    g.add_node(
        "response_generator",
        response_generator_node,
        retry_policy=RetryPolicy(max_attempts=3),
    )

    g.add_edge(START, "turn_classifier")
    g.add_conditional_edges(
        "turn_classifier",
        _route_by_turn,
        ["intent_extractor", "intent_mutator", "reaction_responder", "chitchat_responder"],
    )

    g.add_conditional_edges(
        "intent_extractor",
        _route_after_intent,
        ["followup", "restaurant_retriever"],
    )
    g.add_edge("followup", "intent_extractor")

    g.add_edge("intent_mutator", "restaurant_retriever")
    g.add_edge("restaurant_retriever", "scoring_agent")
    g.add_edge("scoring_agent", "response_generator")
    g.add_edge("response_generator", END)

    # reaction_responder uses Command to route dynamically (pivot → intent_mutator, else END)
    # No static edge needed — Command handles routing

    g.add_edge("chitchat_responder", END)

    return g


checkpointer = MemorySaver()
taste_graph = build_graph().compile(checkpointer=checkpointer)
