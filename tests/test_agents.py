"""Test 2: Agent unit tests — each node in isolation."""
import sys
import os
from pathlib import Path
import pytest

# Add project root to sys.path so backend package is importable
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")


# ── Turn Classifier ───────────────────────────────────────────────────────────

def test_turn_classifier_new_search():
    from backend.agents.turn_classifier import turn_classifier_node
    result = turn_classifier_node({"user_message": "I want sushi for a date night", "messages": []})
    print(f"\n  turn_type: {result['turn_type']}")
    assert result["turn_type"] in {"new_search", "refinement", "reaction", "chitchat"}
    assert result["turn_type"] == "new_search"


def test_turn_classifier_chitchat():
    from backend.agents.turn_classifier import turn_classifier_node
    result = turn_classifier_node({"user_message": "thanks!", "messages": []})
    print(f"\n  turn_type: {result['turn_type']}")
    assert result["turn_type"] == "chitchat"


# ── Intent Extractor ──────────────────────────────────────────────────────────

def test_intent_extractor_basic():
    from backend.agents.intent_extractor import intent_extractor_node
    state = {
        "user_message": "I want ramen for 2 people, budget around $30 per person",
        "messages": [],
        "intent": None,
        "turn_type": "new_search",
    }
    result = intent_extractor_node(state)
    intent = result["intent"]
    print(f"\n  intent: {intent}")
    assert intent is not None
    assert intent.get("group_size") == 2
    assert intent.get("budget") in {"$", "$$"}
    assert intent.get("is_complete") is True


def test_intent_extractor_needs_followup():
    from backend.agents.intent_extractor import intent_extractor_node
    state = {
        "user_message": "looking for a nice dinner spot downtown",
        "messages": [],
        "intent": None,
        "turn_type": "new_search",
    }
    result = intent_extractor_node(state)
    intent = result["intent"]
    print(f"\n  intent: {intent}")
    assert intent is not None
    # Should ask for group_size or budget since neither is specified
    assert intent.get("needs_followup") is True or intent.get("group_size") is not None


# ── Restaurant Retriever ──────────────────────────────────────────────────────

def test_retriever_basic():
    from backend.agents.restaurant_retriever import retriever_node
    state = {
        "intent": {
            "occasion": "date night sushi",
            "group_size": 2,
            "budget": "$$",
            "neighborhood": None,
            "vibe": ["romantic"],
            "cuisine": ["Japanese"],
            "dietary": [],
            "meal_type": "dinner",
            "amenities": [],
            "is_complete": True,
            "needs_followup": False,
            "followup_question": None,
            "missing_fields": [],
        }
    }
    result = retriever_node(state)
    candidates = result.get("candidates", [])
    print(f"\n  candidates retrieved: {len(candidates)}")
    if candidates:
        print(f"  first candidate: {candidates[0].get('name')} ({candidates[0].get('cuisine')})")
    assert len(candidates) > 0, "Retriever returned zero candidates — check ChromaDB"


def test_retriever_no_cuisine_filter():
    from backend.agents.restaurant_retriever import retriever_node
    state = {
        "intent": {
            "occasion": "casual lunch",
            "group_size": 4,
            "budget": "$",
            "neighborhood": "Kensington Market",
            "vibe": [],
            "cuisine": [],
            "dietary": [],
            "meal_type": "lunch",
            "amenities": [],
            "is_complete": True,
            "needs_followup": False,
            "followup_question": None,
            "missing_fields": [],
        }
    }
    result = retriever_node(state)
    candidates = result.get("candidates", [])
    print(f"\n  candidates retrieved: {len(candidates)}")
    assert len(candidates) > 0, "Retriever returned zero candidates with no cuisine filter"


# ── Scoring Agent ─────────────────────────────────────────────────────────────

def test_scoring_agent():
    from backend.agents.restaurant_retriever import retriever_node
    from backend.agents.scoring_agent import scoring_node

    intent = {
        "occasion": "romantic dinner",
        "group_size": 2,
        "budget": "$$$",
        "neighborhood": None,
        "vibe": ["romantic", "quiet"],
        "cuisine": [],
        "dietary": [],
        "meal_type": "dinner",
        "amenities": [],
        "is_complete": True,
        "needs_followup": False,
        "followup_question": None,
        "missing_fields": [],
    }

    retrieval_result = retriever_node({"intent": intent})
    candidates = retrieval_result.get("candidates", [])
    print(f"\n  candidates going into scoring: {len(candidates)}")
    assert len(candidates) > 0, "No candidates to score"

    scoring_result = scoring_node({
        "intent": intent,
        "candidates": candidates,
        "user_feedback": {"liked": [], "disliked": []},
        "shown_restaurant_ids": [],
    })
    scored = scoring_result.get("scored", [])
    print(f"  scored results: {len(scored)}")
    for r in scored:
        print(f"    [{r.get('final_score')}] {r.get('name')} — {r.get('score_reasoning', '')[:80]}")
    assert len(scored) > 0, "Scoring returned zero results"
    assert all("score_reasoning" in r for r in scored), "Missing score_reasoning on some results"


# ── Response Generator ────────────────────────────────────────────────────────

def test_response_generator():
    from backend.agents.restaurant_retriever import retriever_node
    from backend.agents.scoring_agent import scoring_node
    from backend.agents.response_generator import response_generator_node

    intent = {
        "occasion": "birthday dinner",
        "group_size": 6,
        "budget": "$$",
        "neighborhood": None,
        "vibe": ["fun", "lively"],
        "cuisine": [],
        "dietary": [],
        "meal_type": "dinner",
        "amenities": [],
        "is_complete": True,
        "needs_followup": False,
        "followup_question": None,
        "missing_fields": [],
    }

    candidates = retriever_node({"intent": intent}).get("candidates", [])
    scored = scoring_node({
        "intent": intent, "candidates": candidates,
        "user_feedback": {"liked": [], "disliked": []},
        "shown_restaurant_ids": [],
    }).get("scored", [])

    result = response_generator_node({"intent": intent, "scored": scored})
    response = result.get("response", "")
    print(f"\n  response: {response}")
    assert len(response) > 10, "Response generator returned empty/too-short response"
