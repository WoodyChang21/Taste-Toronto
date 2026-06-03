from ..db.chroma_client import get_collection
from ..db import restaurant_repo
from ..services.openai_client import get_embedding

DISTANCE_THRESHOLD = 0.75
MIN_RESULTS = 3
MAX_RESULTS = 10


def retriever_node(state: dict) -> dict:
    intent = state["intent"]
    candidates = retrieve_candidates(intent)
    return {**state, "candidates": [r.model_dump() for r in candidates]}


def retrieve_candidates(intent: dict) -> list:
    query_parts: list[str] = []
    occasion = intent.get("occasion")
    if occasion:
        query_parts.append(occasion)
    for cuisine in intent.get("cuisine") or []:
        query_parts.append(cuisine)
    for vibe in intent.get("vibe") or []:
        query_parts.append(vibe)
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
    n_fetch = min(MAX_RESULTS * 2, total)

    # Vector search — no where filter (ChromaDB where in query() is unreliable)
    results = collection.query(
        query_embeddings=[embedding],
        n_results=n_fetch,
        include=["metadatas", "distances"],
    )
    ids = results["ids"][0] if results["ids"] else []
    distances = results["distances"][0] if results["distances"] else []
    dist_map = dict(zip(ids, distances))

    # If cuisine is specified, fetch all cuisine-matching IDs via get()
    # collection.query() where filter is unreliable; collection.get() works correctly
    cuisines = intent.get("cuisine") or []
    cuisine_set: set[str] = set()
    if cuisines:
        cuisine_val = cuisines[0].capitalize()
        try:
            cuisine_docs = collection.get(
                where={"cuisine": {"$eq": cuisine_val}},
                limit=999,
            )
            cuisine_set = set(cuisine_docs["ids"])
            # Merge cuisine IDs not already in vector results
            worst = max(dist_map.values(), default=0.5)
            for cid in cuisine_set:
                if cid not in dist_map:
                    dist_map[cid] = worst + 0.01
        except Exception:
            pass

    # Sort all candidates by distance (best first)
    ordered = sorted(dist_map.items(), key=lambda x: x[1])

    if cuisine_set:
        # All cuisine matches first so scoring agent sees them; fill rest with best vector matches
        cuisine_ordered = [id_ for id_, _ in ordered if id_ in cuisine_set]
        other_ordered = [id_ for id_, _ in ordered if id_ not in cuisine_set]
        combined = cuisine_ordered + other_ordered[:max(MAX_RESULTS - len(cuisine_ordered), MIN_RESULTS)]
        return restaurant_repo.get_by_ids(combined)

    # No cuisine filter: use distance threshold, guarantee MIN_RESULTS
    filtered_ids = [id_ for id_, d in ordered if d < DISTANCE_THRESHOLD]
    if len(filtered_ids) < MIN_RESULTS:
        filtered_ids = [id_ for id_, _ in ordered[:MIN_RESULTS]]
    filtered_ids = filtered_ids[:MAX_RESULTS]

    return restaurant_repo.get_by_ids(filtered_ids)
