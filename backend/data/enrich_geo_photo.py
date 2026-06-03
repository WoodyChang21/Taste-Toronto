"""
One-time enrichment script: adds google_place_id, latitude, longitude, photo_name
to every restaurant in the DB that doesn't already have them.

Uses a single Places Text Search (New) call per restaurant with an Enterprise
field mask to get location + photos in one request (~$0.017/req).

Usage:
    cd "Taste Toronto"
    python -m backend.data.enrich_geo_photo

Requires in .env (two levels up):
    GOOGLE_PLACES_API_KEY
"""

from __future__ import annotations

import io
import json
import os
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

import httpx
import sqlite3

DB_PATH = Path(__file__).parent / "taste_toronto.db"
PLACES_BASE = "https://places.googleapis.com/v1"

# Enterprise field mask — gets location + photos in one Text Search call
FIELD_MASK = "places.id,places.displayName,places.location,places.photos"


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def fetch_place(name: str, api_key: str) -> dict | None:
    query = f"{name} Toronto restaurant"
    try:
        resp = httpx.post(
            f"{PLACES_BASE}/places:searchText",
            headers={
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": FIELD_MASK,
                "Content-Type": "application/json",
            },
            json={
                "textQuery": query,
                "locationBias": {
                    "circle": {
                        "center": {"latitude": 43.6532, "longitude": -79.3832},
                        "radius": 50000.0,
                    }
                },
                "languageCode": "en",
                "regionCode": "CA",
                "maxResultCount": 1,
            },
            timeout=10,
        )
        resp.raise_for_status()
        places = resp.json().get("places", [])
        return places[0] if places else None
    except Exception as e:
        print(f"  ERROR fetching {name}: {e}")
        return None


def enrich():
    api_key = os.getenv("GOOGLE_PLACES_API_KEY", "")
    if not api_key:
        print("ERROR: GOOGLE_PLACES_API_KEY not set in .env")
        sys.exit(1)

    conn = get_connection()

    # Migrate columns if needed
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(restaurants)").fetchall()}
    for col, typedef in [
        ("google_place_id", "TEXT"),
        ("latitude", "REAL"),
        ("longitude", "REAL"),
        ("photo_name", "TEXT"),
    ]:
        if col not in existing_cols:
            conn.execute(f"ALTER TABLE restaurants ADD COLUMN {col} {typedef}")
    conn.commit()

    rows = conn.execute(
        "SELECT id, name FROM restaurants WHERE google_place_id IS NULL ORDER BY name"
    ).fetchall()

    print(f"Enriching {len(rows)} restaurants...")
    success = 0
    failed = 0

    for i, row in enumerate(rows):
        rid, name = row["id"], row["name"]
        print(f"[{i+1}/{len(rows)}] {name[:50]}", end=" ... ", flush=True)

        place = fetch_place(name, api_key)
        if not place:
            print("NOT FOUND")
            failed += 1
            time.sleep(0.1)
            continue

        place_id = place.get("id", "")
        loc = place.get("location", {})
        lat = loc.get("latitude")
        lng = loc.get("longitude")
        photos = place.get("photos", [])
        photo_name = photos[0].get("name", "") if photos else ""

        conn.execute(
            """UPDATE restaurants
               SET google_place_id = ?, latitude = ?, longitude = ?, photo_name = ?
               WHERE id = ?""",
            (place_id, lat, lng, photo_name, rid),
        )
        conn.commit()

        print(f"lat={lat:.4f}, lng={lng:.4f}, photo={'yes' if photo_name else 'no'}")
        success += 1
        time.sleep(0.12)  # ~8 req/s, well under rate limit

    conn.close()
    print(f"\nDone. {success} enriched, {failed} not found.")


if __name__ == "__main__":
    enrich()
