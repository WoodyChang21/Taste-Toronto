from typing import Annotated
import operator

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from typing_extensions import TypedDict

from ..db.chroma_client import get_collection
from ..db import restaurant_repo
from ..services.openai_client import get_embedding

MAX_VECTOR_RESULTS = 20
MAX_CANDIDATES = 20


# ── Retrieval subgraph state ──────────────────────────────────────────────────

class _RetrieverState(TypedDict):
    intent: dict
    # Accumulated (id, distance) pairs from parallel workers — reducer required
    raw_results: Annotated[list[tuple[str, float]], operator.add]


# ── Worker node ───────────────────────────────────────────────────────────────

def _retrieval_worker(state: dict) -> dict:
    """Handles both 'vector' and 'metadata' branches depending on state['branch']."""
    intent: dict = state["intent"]
    branch: str = state["branch"]

    if branch == "vector":
        return {"raw_results": _vector_search(intent)}
    else:
        return {"raw_results": _metadata_filter(intent)}


def _vector_search(intent: dict) -> list[tuple[str, float]]:
    query_parts: list[str] = []
    if intent.get("occasion"):
        query_parts.append(intent["occasion"])
    for cuisine in intent.get("cuisine") or []:
        query_parts.append(cuisine)
    for vibe in intent.get("vibe") or []:
        query_parts.append(vibe)
    for dietary in intent.get("dietary") or []:
        query_parts.append(dietary)
    for amenity in intent.get("amenities") or []:
        query_parts.append(amenity)
    if intent.get("meal_type"):
        query_parts.append(intent["meal_type"])
    if intent.get("neighborhood"):
        query_parts.append(intent["neighborhood"])
    if intent.get("budget"):
        query_parts.append(intent["budget"])
    if not query_parts:
        query_parts.append("great restaurant")
    query_parts.append("Toronto restaurant")

    embedding = get_embedding(" ".join(query_parts))
    collection = get_collection()
    total = collection.count() or 1
    n_fetch = min(MAX_VECTOR_RESULTS, total)

    results = collection.query(
        query_embeddings=[embedding],
        n_results=n_fetch,
        include=["distances"],
    )
    ids = results["ids"][0] if results["ids"] else []
    distances = results["distances"][0] if results["distances"] else []
    return list(zip(ids, distances))


def _metadata_filter(intent: dict) -> list[tuple[str, float]]:
    """Exact metadata filter for cuisine and/or price_range."""
    collection = get_collection()
    filters: list[dict] = []

    cuisines = intent.get("cuisine") or []
    if cuisines:
        cuisine_val = cuisines[0].capitalize()
        filters.append({"cuisine": {"$eq": cuisine_val}})

    budget = intent.get("budget")
    if budget:
        filters.append({"price_range": {"$eq": budget}})

    if not filters:
        return []

    where = filters[0] if len(filters) == 1 else {"$and": filters}

    try:
        docs = collection.get(where=where, limit=999)
        # Assign a competitive synthetic distance so metadata matches surface
        return [(cid, 0.25) for cid in (docs["ids"] or [])]
    except Exception:
        return []


# ── Fan-out node ──────────────────────────────────────────────────────────────

def _fan_out(state: _RetrieverState) -> list:
    intent = state["intent"]
    sends = [Send("retrieval_worker", {"intent": intent, "branch": "vector"})]

    has_cuisine = bool(intent.get("cuisine"))
    has_budget = bool(intent.get("budget"))
    if has_cuisine or has_budget:
        sends.append(Send("retrieval_worker", {"intent": intent, "branch": "metadata"}))

    return sends


# ── Merge node ────────────────────────────────────────────────────────────────

def _merge_node(state: _RetrieverState) -> dict:
    # Deduplicate by ID — keep best (lowest) distance per restaurant
    dist_map: dict[str, float] = {}
    for rid, dist in state["raw_results"]:
        if rid not in dist_map or dist < dist_map[rid]:
            dist_map[rid] = dist

    ordered_ids = [rid for rid, _ in sorted(dist_map.items(), key=lambda x: x[1])]
    ordered_ids = ordered_ids[:MAX_CANDIDATES]

    restaurants = restaurant_repo.get_by_ids(ordered_ids)
    return {"candidates": [r.model_dump() for r in restaurants]}


# ── Compile retrieval subgraph ────────────────────────────────────────────────

class _SubgraphOutput(TypedDict):
    candidates: list[dict]


_retriever_builder = StateGraph(_RetrieverState, output=_SubgraphOutput)
_retriever_builder.add_node("retrieval_worker", _retrieval_worker)
_retriever_builder.add_node("merge", _merge_node)
_retriever_builder.add_conditional_edges(START, _fan_out, ["retrieval_worker"])
_retriever_builder.add_edge("retrieval_worker", "merge")
_retriever_builder.add_edge("merge", END)

_retriever_subgraph = _retriever_builder.compile()


# ── Public node (called from main graph) ──────────────────────────────────────

def retriever_node(state: dict) -> dict:
    result = _retriever_subgraph.invoke(
        {"intent": state["intent"], "raw_results": []},
    )
    return {"candidates": result["candidates"]}
