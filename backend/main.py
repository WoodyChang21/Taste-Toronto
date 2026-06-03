from pathlib import Path
from dotenv import load_dotenv

# Load .env from workspace root (two levels up from backend/)
load_dotenv(Path(__file__).parent.parent / ".env")

import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from .db.models import init_db
from .db import restaurant_repo
from .graph import taste_graph
from .models.chat import ChatRequest, ChatResponse
from .models.intent import Intent
from .models.restaurant import RestaurantRecord
from .conversation import memory

PLACES_BASE = "https://places.googleapis.com/v1"

# Toronto bounding box for autocomplete location bias
TORONTO_CIRCLE = {
    "circle": {
        "center": {"latitude": 43.6532, "longitude": -79.3832},
        "radius": 50000.0,  # 50km covers the full GTA
    }
}


class AutocompleteRequest(BaseModel):
    input: str
    session_token: str

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
        history = memory.get_history(req.session_id)
        initial_state = {
            "session_id": req.session_id,
            "user_message": req.message,
            "history": history,
            "intent": None,
            "candidates": [],
            "scored": [],
            "response": "",
            "needs_followup": False,
        }

        result = taste_graph.invoke(initial_state)

        intent_data = result.get("intent") or {}
        intent = Intent(**intent_data) if intent_data else None

        needs_followup = result.get("needs_followup", False)

        if needs_followup:
            response_text = intent_data.get("followup_question") or "Could you tell me a bit more?"
        else:
            response_text = result.get("response", "")

        scored_raw = result.get("scored") or []
        restaurants = [RestaurantRecord(**r) for r in scored_raw]

        memory.append(req.session_id, "user", req.message)
        memory.append(req.session_id, "assistant", response_text)

        return ChatResponse(
            session_id=req.session_id,
            message=response_text,
            restaurants=restaurants,
            intent=intent,
            needs_followup=needs_followup,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/autocomplete")
async def autocomplete(req: AutocompleteRequest):
    """
    Proxies Google Places Autocomplete (New) with Toronto location bias.
    Uses session tokens so all keystrokes in one search = 1 billing session.
    Returns up to 5 place suggestions (restaurants + neighborhoods).
    """
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
    # skipHttpRedirect=true returns JSON with photoUri; follow_redirects fetches the image directly
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
    memory.clear(session_id)
    return {"ok": True}
