"""Test 1: Health endpoint — verifies DB is reachable and restaurant count is non-zero."""
import httpx
import pytest

BASE = "http://localhost:8001"


def test_health():
    r = httpx.get(f"{BASE}/api/health", timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    print(f"\n  status: {data.get('status')}")
    print(f"  restaurant_count: {data.get('restaurant_count')}")
    assert data.get("status") == "ok", f"Unexpected status: {data}"
    assert data.get("restaurant_count", 0) > 0, "No restaurants in DB — did fetch_restaurants.py run?"
