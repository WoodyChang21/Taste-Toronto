"""
Re-embeds all restaurants from SQLite into ChromaDB using richer text
(description + semantic_tags + cuisine + noise_level + top occasion scores).

No Google Places API calls — reads only from the local DB.

Usage:
    cd "Taste Toronto"
    python -m backend.data.reembed
"""

from __future__ import annotations

import io
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.db.models import init_db
from backend.db.chroma_client import get_collection
from backend.db import restaurant_repo
from backend.models.restaurant import RestaurantRecord
from backend.services.openai_client import get_embedding


def build_embed_text(record: RestaurantRecord) -> str:
    tags = ", ".join(record.semantic_tags) if record.semantic_tags else ""
    top_occasions = [k for k, v in record.occasion_scores.items() if v >= 70]
    parts = [record.description] if record.description else []
    if tags:
        parts.append(f"Tags: {tags}.")
    if record.cuisine:
        parts.append(f"Cuisine: {record.cuisine}.")
    if record.noise_level:
        parts.append(f"Noise level: {record.noise_level}.")
    if top_occasions:
        parts.append(f"Good for: {', '.join(top_occasions)}.")
    return " ".join(parts) or record.name


def reembed() -> None:
    init_db()
    collection = get_collection()

    # Read all restaurants from SQLite
    from backend.db.models import get_connection
    import json

    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM restaurants ORDER BY name").fetchall()

    print(f"Re-embedding {len(rows)} restaurants...")
    success = 0
    failed = 0

    for i, row in enumerate(rows):
        r = dict(row)
        r["semantic_tags"] = json.loads(r["semantic_tags"] or "[]")
        r["occasion_scores"] = json.loads(r["occasion_scores"] or "{}")
        r["parking"] = bool(r["parking"]) if r["parking"] is not None else None
        place_id = r.pop("google_place_id", None)
        r.pop("photo_name", None)
        r.pop("created_at", None)
        if place_id:
            r["google_maps_url"] = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
        record = RestaurantRecord(**r)

        embed_text = build_embed_text(record)
        print(f"[{i+1}/{len(rows)}] {record.name[:50]}", end=" ... ", flush=True)

        try:
            embedding = get_embedding(embed_text)
            collection.upsert(
                ids=[record.id],
                embeddings=[embedding],
                documents=[embed_text],
                metadatas=[{
                    "name": record.name,
                    "neighborhood": record.neighborhood,
                    "cuisine": record.cuisine,
                    "price_range": record.price_range,
                    "rating": record.rating,
                    "review_count": record.review_count,
                }],
            )
            print("OK")
            success += 1
        except Exception as e:
            print(f"FAILED: {e}")
            failed += 1

    print(f"\nDone. {success} re-embedded, {failed} failed.")


if __name__ == "__main__":
    reembed()
