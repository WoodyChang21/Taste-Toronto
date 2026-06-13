"""Test 4: Database layer — SQLite restaurant count and ChromaDB vector count."""
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")


def test_sqlite_has_restaurants():
    from backend.db import restaurant_repo
    count = restaurant_repo.count()
    print(f"\n  SQLite restaurant count: {count}")
    assert count > 0, "SQLite has no restaurants — run backend/data/fetch_restaurants.py"


def test_sqlite_get_by_ids():
    from backend.db import restaurant_repo
    # Fetch all IDs, pick first 3
    import sqlite3
    db_path = ROOT / "backend" / "data" / "taste_toronto.db"
    conn = sqlite3.connect(str(db_path))
    ids = [row[0] for row in conn.execute("SELECT id FROM restaurants LIMIT 3").fetchall()]
    conn.close()

    print(f"\n  testing get_by_ids with: {ids}")
    results = restaurant_repo.get_by_ids(ids)
    print(f"  returned: {[r.name for r in results]}")
    assert len(results) == len(ids), f"Expected {len(ids)} results, got {len(results)}"


def test_chroma_has_vectors():
    from backend.db.chroma_client import get_collection
    collection = get_collection()
    count = collection.count()
    print(f"\n  ChromaDB vector count: {count}")
    assert count > 0, "ChromaDB is empty — run backend/data/reembed.py"


def test_chroma_query_works():
    from backend.db.chroma_client import get_collection
    from backend.services.openai_client import get_embedding

    collection = get_collection()
    embedding = get_embedding("romantic Italian dinner Toronto")
    results = collection.query(
        query_embeddings=[embedding],
        n_results=5,
        include=["distances"],
    )
    ids = results["ids"][0] if results["ids"] else []
    distances = results["distances"][0] if results["distances"] else []
    print(f"\n  top 5 vector results:")
    for rid, dist in zip(ids, distances):
        print(f"    {rid}  distance={dist:.4f}")
    assert len(ids) > 0, "ChromaDB query returned no results"
    assert all(d < 2.0 for d in distances), f"Distances seem too high: {distances}"
