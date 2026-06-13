"""
Fetches Toronto restaurant data using the NEW Google Places API (v1).
Enriches each restaurant with GPT-4o-generated tags and occasion scores,
then writes to SQLite + ChromaDB.

Usage:
    cd "Taste Toronto"
    python -m backend.data.fetch_restaurants

Requires in .env:
    OPENAI_API_KEY
    GOOGLE_PLACES_API_KEY
"""

from __future__ import annotations

import io
import json
import os
import sys
import time

# Force UTF-8 console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import hashlib
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.db.models import init_db
from backend.db.chroma_client import get_collection
from backend.db import restaurant_repo
from backend.models.restaurant import RestaurantRecord
from backend.services.openai_client import chat_completion, get_embedding

PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "")
PLACES_BASE = "https://places.googleapis.com/v1"

# ── Field masks ──────────────────────────────────────────────────────────────
# Text Search: ID + basic fields only (Essentials SKU = $5/1k, 10k free/month)
TEXT_SEARCH_FIELDS = ",".join([
    "places.id",
    "places.displayName",
    "places.rating",
    "places.userRatingCount",
    "places.formattedAddress",
    "places.priceLevel",
    "places.types",
    "places.primaryType",
    "places.businessStatus",
])

# Place Details: full fields including atmosphere (Enterprise+Atmosphere = $25/1k)
DETAIL_FIELDS = ",".join([
    "id", "displayName", "formattedAddress", "shortFormattedAddress",
    "nationalPhoneNumber", "websiteUri", "googleMapsUri",
    "rating", "userRatingCount", "priceLevel", "priceRange",
    "regularOpeningHours", "businessStatus",
    "photos",
    "reviews",
    "reviewSummary",
    "editorialSummary",
    # Atmosphere fields — these trigger Enterprise+Atmosphere SKU
    "outdoorSeating", "liveMusic", "reservable",
    "goodForGroups", "goodForChildren",
    "servesWine", "servesCocktails", "servesBeer",
    "servesVegetarianFood", "servesDessert",
    "servesBreakfast", "servesLunch", "servesDinner", "servesBrunch",
    "dineIn", "delivery", "takeout", "curbsidePickup",
])

# Toronto bounding box for locationBias
TORONTO_RECTANGLE = {
    "rectangle": {
        "low": {"latitude": 43.5810, "longitude": -79.6393},
        "high": {"latitude": 43.8554, "longitude": -79.1168},
    }
}

# Queries covering all 4 occasion types + neighborhoods + cuisine diversity
SEARCH_QUERIES = [
    # Date night
    "romantic restaurant Toronto downtown",
    "intimate fine dining Toronto",
    "best date night restaurant King West Toronto",
    "romantic restaurant Yorkville Toronto",
    "wine bar date night Toronto",
    "candlelit dinner Toronto",
    # Birthday
    "best birthday dinner restaurant Toronto",
    "special occasion restaurant Toronto",
    "birthday celebration restaurant Distillery District",
    "upscale birthday restaurant Toronto",
    # Family gathering
    "best dim sum Toronto",
    "family restaurant Toronto Scarborough",
    "large group dining Toronto",
    "Korean BBQ Toronto",
    "best Chinese restaurant Toronto North York",
    "best buffet restaurant Toronto",
    # Hidden gems
    "hidden gem restaurant Toronto Leslieville",
    "underrated restaurant Toronto Parkdale",
    "local favourite restaurant Little Portugal Toronto",
    "neighbourhood gem restaurant Kensington Market",
    "best kept secret restaurant Toronto East End",
    # Cuisine diversity
    "best Japanese restaurant Toronto",
    "best Italian restaurant Toronto",
    "best ramen Toronto",
    "best sushi omakase Toronto",
    "best steak restaurant Toronto",
    "best French restaurant Toronto",
    "best Thai restaurant Toronto",
    "best Indian restaurant Toronto",
    "best Mexican restaurant Toronto",
    "best Mediterranean restaurant Toronto",
    "best seafood restaurant Toronto",
    # Neighbourhood coverage
    "best restaurant Queen West Toronto",
    "best restaurant Greektown Toronto Danforth",
    "best restaurant Little Italy Toronto",
    "best restaurant Etobicoke Toronto",
    "best restaurant Mississauga",
    "best restaurant Markham",
    "best restaurant North York",
]

ENRICH_SYSTEM = """You are a Toronto restaurant expert. Given real restaurant data from the Google Places API,
generate semantic tags and occasion scores. Use the provided data — especially amenity booleans,
review summary, and editorial summary — rather than guessing.

Respond with valid JSON only.

Schema:
{
  "semantic_tags": [string],
  "occasion_scores": {
    "date_night": 0-100,
    "birthday": 0-100,
    "family_gathering": 0-100,
    "hidden_gem": 0-100
  },
  "noise_level": "quiet" | "moderate" | "lively",
  "description": "2-3 sentence description highlighting atmosphere, best dishes, and what makes it special"
}

Semantic tag selection guide (pick all that apply):
romantic, intimate, trendy, upscale, casual, cozy, lively, loud, quiet, rooftop, patio,
date_night, birthday, family_gathering, hidden_gem, brunch, late_night,
italian, japanese, chinese, korean, french, canadian, american, mexican, indian, thai,
mediterranean, seafood, steakhouse, vegetarian_friendly, vegan_friendly,
cocktails, wine_bar, sake, beer, byob, tasting_menu, omakase, dim_sum, bbq,
outdoor_seating, live_music, reservable, good_for_groups, good_for_children,
downtown, yorkville, king_west, queen_west, distillery, kensington, leslieville,
parkdale, little_italy, greektown, scarborough, north_york, etobicoke, markham, mississauga

Occasion scoring rules:
- date_night: romantic atmosphere + quiet/moderate noise + wine/cocktails → high score
- birthday: wow-factor + group-friendly + festive → high score
- family_gathering: good_for_groups + good_for_children + parking + large menu → high score
- hidden_gem: rating ≥ 4.3 AND review_count < 500 → high score. Cap at 35 if rating < 4.3.
"""

PRICE_LEVEL_MAP = {
    "PRICE_LEVEL_FREE": "$",
    "PRICE_LEVEL_INEXPENSIVE": "$",
    "PRICE_LEVEL_MODERATE": "$$",
    "PRICE_LEVEL_EXPENSIVE": "$$$",
    "PRICE_LEVEL_VERY_EXPENSIVE": "$$$$",
}

CUISINE_TYPE_MAP = {
    "japanese_restaurant": "Japanese",
    "chinese_restaurant": "Chinese",
    "korean_restaurant": "Korean",
    "italian_restaurant": "Italian",
    "french_restaurant": "French",
    "mexican_restaurant": "Mexican",
    "indian_restaurant": "Indian",
    "thai_restaurant": "Thai",
    "mediterranean_restaurant": "Mediterranean",
    "seafood_restaurant": "Seafood",
    "steak_house": "Steakhouse",
    "sushi_restaurant": "Japanese",
    "ramen_restaurant": "Japanese",
    "pizza_restaurant": "Italian",
    "vietnamese_restaurant": "Vietnamese",
    "greek_restaurant": "Greek",
    "middle_eastern_restaurant": "Middle Eastern",
    "american_restaurant": "American",
    "barbecue_restaurant": "BBQ",
    "fine_dining_restaurant": "Canadian",
    "brunch_restaurant": "Brunch",
    "breakfast_restaurant": "Brunch",
}

NEIGHBORHOOD_KEYWORDS = [
    "Yorkville", "King West", "Queen West", "Distillery", "Kensington",
    "Leslieville", "Parkdale", "Little Italy", "Little Portugal", "Greektown",
    "Chinatown", "Scarborough", "North York", "Etobicoke", "Markham",
    "Richmond Hill", "Mississauga", "Vaughan", "Brampton", "Oakville",
    "Rosedale", "Forest Hill", "The Annex", "Danforth", "Riverdale",
    "Liberty Village", "Corktown", "St. Lawrence", "Harbourfront",
    "Entertainment District", "Financial District", "Bloor West",
]


def _headers(field_mask: str) -> dict:
    return {
        "X-Goog-Api-Key": PLACES_API_KEY,
        "X-Goog-FieldMask": field_mask,
        "Content-Type": "application/json",
    }


def text_search(query: str, max_results: int = 20) -> list[dict]:
    resp = httpx.post(
        f"{PLACES_BASE}/places:searchText",
        headers=_headers(TEXT_SEARCH_FIELDS),
        json={
            "textQuery": query,
            "maxResultCount": max_results,
            "locationBias": TORONTO_RECTANGLE,
            "languageCode": "en",
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("places", [])


def place_details(place_id: str) -> dict:
    resp = httpx.get(
        f"{PLACES_BASE}/places/{place_id}",
        headers=_headers(DETAIL_FIELDS),
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def extract_neighborhood(address: str) -> str:
    for kw in NEIGHBORHOOD_KEYWORDS:
        if kw.lower() in address.lower():
            return kw
    return "Downtown Toronto"


def extract_cuisine(types: list[str]) -> str:
    for t in types:
        if t in CUISINE_TYPE_MAP:
            return CUISINE_TYPE_MAP[t]
    return "Canadian"


def extract_bool_amenities(details: dict) -> dict:
    """Pull the new boolean amenity fields straight from the API response."""
    return {
        "outdoor_seating": details.get("outdoorSeating"),
        "live_music": details.get("liveMusic"),
        "reservable": details.get("reservable"),
        "good_for_groups": details.get("goodForGroups"),
        "good_for_children": details.get("goodForChildren"),
        "serves_wine": details.get("servesWine"),
        "serves_cocktails": details.get("servesCocktails"),
        "serves_beer": details.get("servesBeer"),
        "serves_vegetarian": details.get("servesVegetarianFood"),
        "serves_dessert": details.get("servesDessert"),
        "serves_breakfast": details.get("servesBreakfast"),
        "serves_lunch": details.get("servesLunch"),
        "serves_dinner": details.get("servesDinner"),
        "serves_brunch": details.get("servesBrunch"),
        "dine_in": details.get("dineIn"),
        "delivery": details.get("delivery"),
        "takeout": details.get("takeout"),
    }


def enrich_with_gpt(basic: dict, amenities: dict, review_summary: str, editorial: str) -> dict:
    """Use GPT-4o to generate tags, scores, noise level, and description."""
    prompt = json.dumps({
        "restaurant_data": basic,
        "amenities": {k: v for k, v in amenities.items() if v is True},
        "google_review_summary": review_summary,
        "google_editorial_summary": editorial,
    }, indent=2)
    raw = chat_completion(ENRICH_SYSTEM, [{"role": "user", "content": prompt}], json_mode=True, max_tokens=512)
    return json.loads(raw)


def make_id(place_id: str) -> str:
    return hashlib.md5(place_id.encode()).hexdigest()[:12]


def fetch_and_seed(max_per_query: int = 10, total_cap: int = 200) -> None:
    if not PLACES_API_KEY:
        print("ERROR: GOOGLE_PLACES_API_KEY not set in .env")
        sys.exit(1)

    init_db()
    collection = get_collection()

    seen_place_ids: set[str] = set()
    processed = 0

    for query in SEARCH_QUERIES:
        if processed >= total_cap:
            break

        print(f"\n-> Searching: {query}")
        try:
            results = text_search(query, max_results=max_per_query)
        except Exception as e:
            print(f"  Search failed: {e}")
            continue

        for result in results:
            if processed >= total_cap:
                break

            place_id = result.get("id", "")
            if not place_id or place_id in seen_place_ids:
                continue
            seen_place_ids.add(place_id)

            name = result.get("displayName", {}).get("text", "")
            rating = result.get("rating", 0.0)
            review_count = result.get("userRatingCount", 0)
            business_status = result.get("businessStatus", "")

            if rating < 3.8 or review_count < 20:
                continue
            if business_status == "CLOSED_PERMANENTLY":
                continue

            print(f"  Fetching details: {name} ({rating}*, {review_count} reviews)")

            try:
                details = place_details(place_id)
                time.sleep(0.1)
            except Exception as e:
                print(f"  Details failed: {e}")
                details = result

            address = details.get("formattedAddress") or result.get("formattedAddress", "Toronto")
            neighborhood = extract_neighborhood(address)
            types = result.get("types", [])
            cuisine = extract_cuisine(types)
            price_symbol = PRICE_LEVEL_MAP.get(
                details.get("priceLevel", ""), "$$"
            )

            # Pull new API fields
            amenities = extract_bool_amenities(details)

            review_summary = ""
            rs = details.get("reviewSummary", {})
            if rs and isinstance(rs, dict):
                review_summary = rs.get("text", {}).get("text", "") if isinstance(rs.get("text"), dict) else ""

            editorial = ""
            ed = details.get("editorialSummary", {})
            if ed and isinstance(ed, dict):
                editorial = ed.get("text", "")

            website = details.get("websiteUri", "")
            phone = details.get("nationalPhoneNumber", "")
            maps_uri = details.get("googleMapsUri", "")

            basic_info = {
                "name": name,
                "address": address,
                "neighborhood": neighborhood,
                "cuisine": cuisine,
                "price_range": price_symbol,
                "rating": rating,
                "review_count": review_count,
                "google_maps_url": maps_uri,
            }

            try:
                enriched = enrich_with_gpt(basic_info, amenities, review_summary, editorial)
                time.sleep(0.05)
            except Exception as e:
                print(f"  GPT enrichment failed: {e}")
                enriched = {
                    "semantic_tags": [],
                    "occasion_scores": {"date_night": 50, "birthday": 50, "family_gathering": 50, "hidden_gem": 30},
                    "noise_level": "moderate",
                    "description": f"{name} is a {cuisine} restaurant in {neighborhood}, Toronto.",
                }

            record = RestaurantRecord(
                id=make_id(place_id),
                name=name,
                address=address,
                neighborhood=neighborhood,
                cuisine=cuisine,
                price_range=price_symbol,
                rating=rating,
                review_count=review_count,
                phone=phone or None,
                website=website or None,
                reservation_url=None,
                noise_level=enriched.get("noise_level"),
                parking=None,
                semantic_tags=enriched.get("semantic_tags", []),
                occasion_scores=enriched.get("occasion_scores", {}),
                description=enriched.get("description", ""),
            )

            restaurant_repo.upsert(record)

            try:
                from backend.data.reembed import build_embed_text
                embedding = get_embedding(build_embed_text(record))
                collection.upsert(
                    ids=[record.id],
                    embeddings=[embedding],
                    documents=[build_embed_text(record)],
                    metadatas=[{
                        "name": record.name,
                        "neighborhood": record.neighborhood,
                        "cuisine": record.cuisine,
                        "price_range": record.price_range,
                        "rating": record.rating,
                        "review_count": record.review_count,
                    }],
                )
            except Exception as e:
                print(f"  Embedding failed: {e}")

            processed += 1
            print(f"  OK {record.name} | {neighborhood} | {cuisine} | {price_symbol} | tags: {len(record.semantic_tags)} ({processed}/{total_cap})")

    print(f"\nDone. Total restaurants in DB: {restaurant_repo.count()}")


if __name__ == "__main__":
    fetch_and_seed()
