from pathlib import Path
from dotenv import load_dotenv

# Load .env from workspace root (two levels up from backend/)
load_dotenv(Path(__file__).parent.parent / ".env")

import json
import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from langgraph.types import Command

from .db.models import init_db
from .db import restaurant_repo
from .graph import taste_graph
from .models.chat import ChatRequest, ChatResponse
from .models.intent import Intent
from .models.restaurant import RestaurantRecord

PLACES_BASE = "https://places.googleapis.com/v1"

TORONTO_CIRCLE = {
    "circle": {
        "center": {"latitude": 43.6532, "longitude": -79.3832},
        "radius": 50000.0,
    }
}

# Sessions flagged for reset — cleared on next chat invocation
_cleared_sessions: set[str] = set()


class AutocompleteRequest(BaseModel):
    input: str
    session_token: str


class FeedbackRequest(BaseModel):
    session_id: str
    restaurant_id: str
    signal: str  # "like" | "dislike"


app = FastAPI(title="Taste Toronto API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok", "restaurant_count": restaurant_repo.count()}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        config = {"configurable": {"thread_id": req.session_id}}

        is_reset = req.session_id in _cleared_sessions
        if is_reset:
            _cleared_sessions.discard(req.session_id)

        current_state = taste_graph.get_state(config)

        if not is_reset and current_state.next:
            # Graph is paused at a follow-up interrupt — resume with user's answer
            result = await taste_graph.ainvoke(Command(resume=req.message), config)
        else:
            # New turn (or first message after reset)
            input_state: dict = {
                "user_message": req.message,
                "candidates": [],
                "scored": [],
                "response": "",
                "turn_type": None,
            }
            if is_reset:
                input_state["intent"] = None
                input_state["shown_restaurant_ids"] = []
                input_state["user_feedback"] = {"liked": [], "disliked": []}
            result = await taste_graph.ainvoke(input_state, config)

        # Graph hit a follow-up interrupt this turn
        if result.get("__interrupt__"):
            question = result["__interrupt__"][0].value.get(
                "question", "Could you tell me a bit more?"
            )
            return ChatResponse(
                session_id=req.session_id,
                message=question,
                restaurants=[],
                needs_followup=True,
            )

        intent_data = result.get("intent") or {}
        intent = Intent(**intent_data) if intent_data else None
        scored_raw = result.get("scored") or []
        restaurants = [RestaurantRecord(**r) for r in scored_raw]

        return ChatResponse(
            session_id=req.session_id,
            message=result.get("response", ""),
            restaurants=restaurants,
            intent=intent,
            needs_followup=False,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    config = {"configurable": {"thread_id": req.session_id}}
    is_reset = req.session_id in _cleared_sessions
    if is_reset:
        _cleared_sessions.discard(req.session_id)

    current_state = taste_graph.get_state(config)

    if not is_reset and current_state.next:
        input_data = Command(resume=req.message)
    else:
        input_data = {
            "user_message": req.message,
            "candidates": [],
            "scored": [],
            "response": "",
            "turn_type": None,
        }
        if is_reset:
            input_data["intent"] = None
            input_data["shown_restaurant_ids"] = []
            input_data["user_feedback"] = {"liked": [], "disliked": []}

    async def generate():
        try:
            text_streamed = False
            async for event in taste_graph.astream_events(input_data, config, version="v2"):
                event_name = event.get("event", "")
                node_name = event.get("metadata", {}).get("langgraph_node", "")

                if event_name == "on_chat_model_stream" and node_name in (
                    "response_generator", "chitchat_responder"
                ):
                    chunk = event["data"]["chunk"].content
                    if chunk:
                        text_streamed = True
                        yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"

            # Inspect final graph state to detect interrupt or emit results
            final_state = taste_graph.get_state(config)

            if final_state.next:
                # Graph paused at a followup interrupt
                for task in final_state.tasks:
                    if task.interrupts:
                        question = task.interrupts[0].value.get(
                            "question", "Could you tell me a bit more?"
                        )
                        yield f"data: {json.dumps({'type': 'followup', 'question': question})}\n\n"
                        break
            else:
                # Graph completed — emit stored response if not already streamed (e.g. chitchat)
                if not text_streamed:
                    response = final_state.values.get("response", "")
                    if response:
                        yield f"data: {json.dumps({'type': 'text', 'content': response})}\n\n"

                scored = final_state.values.get("scored") or []
                if scored:
                    yield f"data: {json.dumps({'type': 'restaurants', 'restaurants': scored})}\n\n"

            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/feedback")
async def feedback(req: FeedbackRequest):
    config = {"configurable": {"thread_id": req.session_id}}
    try:
        current = taste_graph.get_state(config)
        feedback_state = (current.values.get("user_feedback") or {})
        liked = list(feedback_state.get("liked", []))
        disliked = list(feedback_state.get("disliked", []))

        if req.signal == "like" and req.restaurant_id not in liked:
            liked.append(req.restaurant_id)
            disliked = [r for r in disliked if r != req.restaurant_id]
        elif req.signal == "dislike" and req.restaurant_id not in disliked:
            disliked.append(req.restaurant_id)
            liked = [r for r in liked if r != req.restaurant_id]

        taste_graph.update_state(config, {"user_feedback": {"liked": liked, "disliked": disliked}})
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/autocomplete")
async def autocomplete(req: AutocompleteRequest):
    api_key = os.getenv("GOOGLE_PLACES_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="GOOGLE_PLACES_API_KEY not configured")

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.post(
                f"{PLACES_BASE}/places:autocomplete",
                headers={"X-Goog-Api-Key": api_key, "Content-Type": "application/json"},
                json={
                    "input": req.input,
                    "sessionToken": req.session_token,
                    "locationBias": TORONTO_CIRCLE,
                    "includedPrimaryTypes": [
                        "restaurant", "food", "neighborhood",
                        "sublocality", "locality",
                    ],
                    "languageCode": "en",
                    "regionCode": "CA",
                    "includeQueryPredictions": True,
                },
            )
        resp.raise_for_status()
        suggestions = resp.json().get("suggestions", [])

        results = []
        for s in suggestions[:5]:
            if "placePrediction" in s:
                pp = s["placePrediction"]
                results.append({
                    "type": "place",
                    "place_id": pp.get("placeId"),
                    "text": pp.get("text", {}).get("text", ""),
                    "main_text": pp.get("structuredFormat", {}).get("mainText", {}).get("text", ""),
                    "secondary_text": pp.get("structuredFormat", {}).get("secondaryText", {}).get("text", ""),
                })
            elif "queryPrediction" in s:
                qp = s["queryPrediction"]
                results.append({
                    "type": "query",
                    "place_id": None,
                    "text": qp.get("text", {}).get("text", ""),
                    "main_text": qp.get("text", {}).get("text", ""),
                    "secondary_text": "",
                })

        return {"suggestions": results}

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/photo/{restaurant_id}")
async def get_photo(restaurant_id: str):
    api_key = os.getenv("GOOGLE_PLACES_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="GOOGLE_PLACES_API_KEY not configured")
    photo_name = restaurant_repo.get_photo_name(restaurant_id)
    if not photo_name:
        raise HTTPException(status_code=404, detail="No photo available")
    url = f"{PLACES_BASE}/{photo_name}/media?maxWidthPx=600"
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(url, headers={"X-Goog-Api-Key": api_key})
        resp.raise_for_status()
        return Response(
            content=resp.content,
            media_type=resp.headers.get("content-type", "image/jpeg"),
            headers={"Cache-Control": "public, max-age=86400"},
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/session/{session_id}")
def clear_session(session_id: str):
    _cleared_sessions.add(session_id)
    return {"ok": True}
