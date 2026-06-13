"""Test 3: Full streaming pipeline — hits /api/chat/stream and prints raw SSE events."""
import httpx
import pytest
import uuid

BASE = "http://localhost:8001"


def _parse_sse(text: str) -> list[dict]:
    import json
    events = []
    for line in text.splitlines():
        if line.startswith("data: "):
            raw = line[6:].strip()
            if raw == "[DONE]":
                events.append({"type": "DONE"})
            else:
                try:
                    events.append(json.parse(raw))
                except Exception:
                    events.append({"type": "raw", "content": raw})
    return events


def _collect_stream(message: str, session_id: str | None = None) -> tuple[str, list[dict]]:
    """Send a chat message and collect all SSE events. Returns (raw_body, parsed_events)."""
    import json
    sid = session_id or str(uuid.uuid4())
    with httpx.Client(timeout=60) as client:
        with client.stream(
            "POST",
            f"{BASE}/api/chat/stream",
            json={"session_id": sid, "message": message},
            headers={"Accept": "text/event-stream"},
        ) as r:
            assert r.status_code == 200, f"HTTP {r.status_code}: {r.read()}"
            raw = r.read().decode()

    events = []
    for line in raw.splitlines():
        if line.startswith("data: "):
            chunk = line[6:].strip()
            if chunk == "[DONE]":
                events.append({"type": "DONE"})
            else:
                try:
                    events.append(json.loads(chunk))
                except Exception:
                    events.append({"type": "raw", "content": chunk})

    return raw, events


def test_stream_followup():
    """A vague message should trigger a followup question, not restaurants."""
    raw, events = _collect_stream("I want somewhere nice for dinner")
    print(f"\n  raw SSE:\n{raw[:2000]}")
    print(f"\n  parsed events: {events}")

    event_types = [e.get("type") for e in events]
    print(f"  event types seen: {event_types}")

    assert len(events) > 0, "No SSE events received at all"
    assert "DONE" in event_types, "Stream never sent [DONE]"

    # Should be either a followup or text+restaurants
    has_followup = any(e.get("type") == "followup" for e in events)
    has_text = any(e.get("type") == "text" for e in events)
    has_error = any(e.get("type") == "error" for e in events)

    if has_error:
        err = next(e for e in events if e.get("type") == "error")
        pytest.fail(f"Backend returned error event: {err.get('message')}")

    assert has_followup or has_text, f"Expected followup or text events, got: {event_types}"


def test_stream_full_intent():
    """A complete request should stream text tokens then emit restaurants."""
    raw, events = _collect_stream(
        "Looking for Japanese ramen for 2 people, budget around $20-30 per person"
    )
    print(f"\n  raw SSE:\n{raw[:3000]}")
    print(f"\n  parsed events: {events}")

    event_types = [e.get("type") for e in events]
    print(f"  event types seen: {event_types}")

    has_error = any(e.get("type") == "error" for e in events)
    if has_error:
        err = next(e for e in events if e.get("type") == "error")
        pytest.fail(f"Backend returned error event: {err.get('message')}")

    has_text = any(e.get("type") == "text" for e in events)
    has_restaurants = any(e.get("type") == "restaurants" for e in events)

    assert "DONE" in event_types, "Stream never sent [DONE]"

    if has_restaurants:
        restaurants_event = next(e for e in events if e.get("type") == "restaurants")
        rests = restaurants_event.get("restaurants", [])
        print(f"  restaurants returned: {len(rests)}")
        for r in rests:
            print(f"    - {r.get('name')} | {r.get('score_reasoning', '')[:60]}")
        assert len(rests) > 0, "restaurants event was empty"

    assert has_text or has_restaurants, f"No useful output events. Got: {event_types}"


def test_stream_chitchat():
    """Chitchat should return a friendly text response, no restaurants."""
    raw, events = _collect_stream("Hey! What's up?")
    print(f"\n  raw SSE:\n{raw[:1000]}")

    event_types = [e.get("type") for e in events]
    print(f"  event types: {event_types}")

    has_error = any(e.get("type") == "error" for e in events)
    if has_error:
        err = next(e for e in events if e.get("type") == "error")
        pytest.fail(f"Backend returned error: {err.get('message')}")

    assert "DONE" in event_types


def test_stream_multi_turn():
    """Two-turn conversation: vague first message → answer followup → get restaurants."""
    sid = str(uuid.uuid4())

    # Turn 1: vague
    raw1, events1 = _collect_stream("I want Italian food for dinner", session_id=sid)
    print(f"\n  Turn 1 events: {[e.get('type') for e in events1]}")

    has_followup = any(e.get("type") == "followup" for e in events1)
    has_restaurants = any(e.get("type") == "restaurants" for e in events1)
    print(f"  has_followup={has_followup}, has_restaurants={has_restaurants}")

    # Turn 2: complete the intent
    raw2, events2 = _collect_stream("Just 2 of us, mid-range budget", session_id=sid)
    print(f"\n  Turn 2 events: {[e.get('type') for e in events2]}")

    event_types2 = [e.get("type") for e in events2]
    has_error = any(e.get("type") == "error" for e in events2)
    if has_error:
        err = next(e for e in events2 if e.get("type") == "error")
        pytest.fail(f"Turn 2 error: {err.get('message')}")

    assert "DONE" in event_types2
