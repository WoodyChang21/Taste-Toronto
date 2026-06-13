# Taste Toronto — Optimization Design

**Date:** 2026-06-13  
**Scope:** Retrieval accuracy, LangGraph state improvements, frontend reasoning display  
**Order of implementation:** B (Retrieval & Scoring) → A (State & Flow) → C (Frontend)

---

## Overview

Three coordinated improvements to the Taste Toronto restaurant discovery app:

- **B — Retrieval & Scoring:** richer embeddings, hybrid parallel retrieval via LangGraph `Send()`, LLM reranking replacing rule-based scorer, extended `Intent` model
- **A — State & Flow:** `SqliteSaver` for durable sessions, `reaction_responder` pivot auto-search, streaming via `astream_events()`
- **C — Frontend:** stream the intro text, show LLM reasoning per restaurant card

---

## B — Retrieval & Scoring

### B1. Re-embedding (data pipeline)

**Files:** `backend/data/reembed.py` (new), `backend/data/fetch_restaurants.py` (updated)

Write a standalone `backend/data/reembed.py` that reads all restaurants from SQLite and re-upserts ChromaDB vectors — no Google Places API calls, no API budget spent. Also add `build_embed_text` to `fetch_restaurants.py` so future ingestion runs use the same richer text.

```python
def build_embed_text(record: RestaurantRecord) -> str:
    tags = ", ".join(record.semantic_tags) if record.semantic_tags else ""
    top_occasions = [k for k, v in record.occasion_scores.items() if v >= 70]
    parts = [record.description]
    if tags:
        parts.append(f"Tags: {tags}.")
    if record.cuisine:
        parts.append(f"Cuisine: {record.cuisine}.")
    if record.noise_level:
        parts.append(f"Noise level: {record.noise_level}.")
    if top_occasions:
        parts.append(f"Good for: {', '.join(top_occasions)}.")
    return " ".join(parts)
```

Store this richer text as both the ChromaDB `document` and the embedding input so vector search matches against tags and vibe words directly. Run `reembed.py` once after implementation, before testing.

### B2. Extended Intent model

**File:** `backend/models/intent.py`

Add three optional fields:

```python
class Intent(BaseModel):
    # ... existing fields unchanged ...
    dietary: list[str] = []        # e.g. ["vegetarian", "halal", "gluten_free"]
    meal_type: str | None = None   # "lunch" | "dinner" | "brunch" | "late_night"
    amenities: list[str] = []      # e.g. ["patio", "parking", "live_music", "reservable"]
```

Update `intent_extractor.py` system prompt to extract these when mentioned. Rule: never ask for them, only extract if the user volunteers them (same pattern as `vibe` and `cuisine` today).

Update `intent_mutator.py` prompt to carry forward these fields on refinement turns.

### B3. Hybrid parallel retrieval

**File:** `backend/agents/restaurant_retriever.py`

Replace the current monolithic `retriever_node` with a compiled retrieval subgraph. `Send()` requires nodes at the graph level — parallel branches cannot live inside a single Python function. The subgraph is compiled separately and added to the main graph as a single node named `restaurant_retriever`.

**Retrieval subgraph structure:**

```
retriever_subgraph (START)
  └─ fan_out_node  →  Send("vector_search") → vector_search_node ──┐
                   →  Send("metadata_filter") → metadata_filter_node ┘
                                                                     ↓
                                                              merge_node (END)
```

`metadata_filter_node` is only dispatched via `Send()` when cuisine or price_range is present in intent; `fan_out_node` checks and conditionally emits only the relevant `Send()` calls.

**`vector_search_node`:** embeds the intent query (occasion + cuisine + vibe + neighborhood + budget concatenated), queries ChromaDB top 20 by cosine similarity, returns `(id, distance)` pairs.

**`metadata_filter_node`:** calls `collection.get()` with `where` filter on `cuisine` and/or `price_range` metadata. Returns matching IDs with a small synthetic distance (e.g. `0.3`) to ensure they surface in merge.

**`merge_node`:** deduplicates by ID (take best distance if duplicate), sorts by distance, caps at 20 candidates, fetches full records from SQLite via `restaurant_repo.get_by_ids()`.

**Deleted:** the entire dual-path cuisine workaround in the current `retrieve_candidates()` function (`cuisine_docs = collection.get(where=..., limit=999)` block and the `cuisine_set` logic).

### B4. LLM reranker replaces scoring_node

**File:** `backend/agents/scoring_agent.py` → replace entirely

New `reranker_node` using `gpt-4o-mini` with structured output:

```python
class RankedResult(BaseModel):
    id: str
    rank: int          # 1–5
    reasoning: str     # 1-2 sentences shown to user on the card

class RerankerOutput(BaseModel):
    results: list[RankedResult]
```

Prompt receives:
- Full intent (occasion, group_size, budget, neighborhood, vibe, cuisine, dietary, meal_type, amenities)
- All candidate restaurant summaries (name, cuisine, price_range, neighborhood, noise_level, rating, semantic_tags, description)
- `shown_restaurant_ids` — reranker instructed to down-rank these unless no better options exist

Output: top 5 ranked results with reasoning. The `reasoning` string maps to `score_reasoning` on `ScoredRestaurant`. The rule-based `scoring_node` and `_build_reasoning()` function are deleted.

**`ScoredRestaurant` model:** no schema change needed — `score_reasoning: str` already exists.

---

## A — State & Flow

### A1. SqliteSaver for durable sessions

**File:** `backend/graph.py`

```python
# Remove:
from langgraph.checkpoint.memory import InMemorySaver
checkpointer = InMemorySaver()

# Add:
from langgraph.checkpoint.sqlite import SqliteSaver
from pathlib import Path
_DB_PATH = str(Path(__file__).parent / "data" / "taste_toronto.db")
checkpointer = SqliteSaver.from_conn_string(f"sqlite:///{_DB_PATH}")
```

LangGraph creates its checkpoint tables (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`) in the existing SQLite DB on first run. No migration script needed — `SqliteSaver` self-initializes.

### A2. TasteState additions

**File:** `backend/graph.py`

```python
class TasteState(TypedDict):
    user_message: str
    messages: Annotated[list[BaseMessage], add_messages]
    intent: dict | None
    candidates: list[dict]
    scored: list[dict]
    response: str
    turn_type: str | None
    shown_restaurant_ids: list[str]
    user_feedback: dict   # {"liked": [id, ...], "disliked": [id, ...]}
```

`user_feedback` is initialized as `{"liked": [], "disliked": []}` on session start. The reranker prompt reads both lists. A new `/api/feedback` POST endpoint (request: `{session_id, restaurant_id, signal: "like"|"dislike"}`) updates state via `graph.update_state()`.

### A3. reaction_responder auto re-search

**File:** `backend/agents/reaction_responder.py`

Switch to structured output:

```python
class ReactionOutput(BaseModel):
    response: str            # conversational reply always shown
    is_pivot: bool           # True if user clearly wants different results
    pivot_intent: dict | None  # partial intent fields to merge (only if is_pivot)
```

**File:** `backend/graph.py`

Add conditional edge from `reaction_responder`:

```python
def _route_after_reaction(state: TasteState) -> str:
    # reaction_responder stores is_pivot in a temp state field
    if state.get("_reaction_is_pivot"):
        return "intent_mutator"
    return END

g.add_conditional_edges("reaction_responder", _route_after_reaction,
                         ["intent_mutator", END])
```

`reaction_responder_node` sets `intent: {**current_intent, **pivot_intent}` when `is_pivot=True` so `intent_mutator` has the pre-merged partial update to work from, then continues through `restaurant_retriever` → `reranker` → `response_generator`.

### A4. Streaming endpoint

**File:** `backend/main.py`

Add `/api/chat/stream` alongside the existing `/api/chat` (kept for compatibility):

```python
@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    async def generate():
        config = {"configurable": {"thread_id": req.session_id}}
        # ... same interrupt/resume logic as /api/chat ...
        final_state = None
        async for event in taste_graph.astream_events(input_state, config, version="v2"):
            if event["event"] == "on_chat_model_stream":
                # Only stream tokens from response_generator (filter by run name)
                if event.get("metadata", {}).get("langgraph_node") == "response_generator":
                    chunk = event["data"]["chunk"].content
                    if chunk:
                        yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"
            elif event["event"] == "on_chain_end" and event["name"] == "LangGraph":
                # Final graph output — contains the complete state including scored restaurants
                final_state = event["data"].get("output", {})
        if final_state:
            scored = final_state.get("scored", [])
            yield f"data: {json.dumps({'type': 'restaurants', 'restaurants': scored})}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
```

---

## C — Frontend

### C1. useChat streaming

**File:** `frontend/hooks/useChat.ts`

Replace the `fetch("/api/chat")` call with an SSE connection to `/api/chat/stream`. On receiving `{type: "text"}` events, append chunk to the current assistant message. On `{type: "restaurants"}`, attach the restaurant array to the message. On `[DONE]`, mark loading complete.

The `UIMessage` type and all other components are unchanged.

### C2. Reasoning callout in RestaurantCard

**File:** `frontend/components/RestaurantCard.tsx`

Add below the description paragraph (before the links row), only when `r.score_reasoning` is non-empty:

```tsx
{r.score_reasoning && (
  <p style={{
    fontSize: "0.78rem",
    color: "var(--ink-muted)",
    fontStyle: "italic",
    lineHeight: 1.6,
    borderLeft: "2px solid var(--border)",
    paddingLeft: "0.6rem",
    margin: "0.4rem 0 0.5rem",
  }}>
    ✦ {r.score_reasoning}
  </p>
)}
```

No changes to `ScoredRestaurant` type — `score_reasoning` already exists and is already returned in `ChatResponse.restaurants`.

---

## Files Changed Summary

| File | Change |
|------|--------|
| `backend/data/reembed.py` | **New** — re-embeds all restaurants from SQLite into ChromaDB with richer text; run once after implementation |
| `backend/data/fetch_restaurants.py` | Add `build_embed_text()` so future ingestion uses the same richer format |
| `backend/models/intent.py` | Add `dietary`, `meal_type`, `amenities` fields |
| `backend/agents/intent_extractor.py` | Prompt update: extract new Intent fields |
| `backend/agents/intent_mutator.py` | Prompt update: carry forward new fields |
| `backend/agents/restaurant_retriever.py` | Hybrid parallel retrieval via `Send()`, delete cuisine workaround |
| `backend/agents/scoring_agent.py` | Replace entirely with LLM `reranker_node` |
| `backend/agents/reaction_responder.py` | Structured output with `is_pivot` + `pivot_intent` |
| `backend/graph.py` | `SqliteSaver`, `user_feedback` in state, reaction pivot edge |
| `backend/main.py` | `/api/chat/stream` SSE endpoint, `/api/feedback` endpoint |
| `backend/requirements.txt` | Add `langgraph[sqlite]` if not already present |
| `frontend/hooks/useChat.ts` | Switch to SSE streaming |
| `frontend/components/RestaurantCard.tsx` | Add reasoning callout |

---

## What Is Not Changing

- `turn_classifier` — no changes
- `chitchat_responder` — no changes
- `followup_node` / `interrupt()` pattern — no changes
- `response_generator` — no changes
- `ChatResponse` API contract — no breaking changes (new fields added, nothing removed)
- All Google Places endpoints (`/api/autocomplete`, `/api/photo`) — untouched
- Frontend layout, map panel, message bubble structure — untouched
- Restaurant data in SQLite — untouched (only ChromaDB vectors are rebuilt)
