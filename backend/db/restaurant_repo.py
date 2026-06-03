import json
from .models import get_connection
from ..models.restaurant import RestaurantRecord


def get_by_ids(ids: list[str]) -> list[RestaurantRecord]:
    if not ids:
        return []
    placeholders = ",".join("?" * len(ids))
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT * FROM restaurants WHERE id IN ({placeholders})", ids
        ).fetchall()
    records = []
    id_order = {rid: i for i, rid in enumerate(ids)}
    for row in rows:
        r = dict(row)
        r["semantic_tags"] = json.loads(r["semantic_tags"] or "[]")
        r["occasion_scores"] = json.loads(r["occasion_scores"] or "{}")
        r["parking"] = bool(r["parking"]) if r["parking"] is not None else None
        place_id = r.pop("google_place_id", None)
        r.pop("photo_name", None)
        r.pop("created_at", None)
        if place_id:
            r["google_maps_url"] = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
        records.append(RestaurantRecord(**r))
    records.sort(key=lambda x: id_order.get(x.id, 999))
    return records


def upsert(record: RestaurantRecord) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO restaurants
            (id, name, address, neighborhood, cuisine, price_range, rating, review_count,
             phone, website, reservation_url, noise_level, parking, semantic_tags,
             occasion_scores, description)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                record.id, record.name, record.address, record.neighborhood,
                record.cuisine, record.price_range, record.rating, record.review_count,
                record.phone, record.website, record.reservation_url, record.noise_level,
                int(record.parking) if record.parking is not None else None,
                json.dumps(record.semantic_tags),
                json.dumps(record.occasion_scores),
                record.description,
            ),
        )
        conn.commit()


def get_photo_name(restaurant_id: str) -> str | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT photo_name FROM restaurants WHERE id = ?", (restaurant_id,)
        ).fetchone()
    return row["photo_name"] if row else None


def count() -> int:
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM restaurants").fetchone()[0]
