from sqlalchemy import text

from src.core.entities import Place
from src.core.ports import PlaceRepository

from .db import make_engine

UPSERT_SQL = """
INSERT INTO places (place_id, name, address, website, phone, lat, lng, email, updated_at, email_scraped_at, types)
VALUES (:place_id, :name, :address, :website, :phone, :lat, :lng, :email, datetime('now'), :email_scraped_at, :types)
ON CONFLICT(place_id) DO UPDATE SET
    name = COALESCE(excluded.name, places.name),
    address = COALESCE(excluded.address, places.address),
    website = COALESCE(excluded.website, places.website),
    phone = COALESCE(excluded.phone, places.phone),
    lat = COALESCE(excluded.lat, places.lat),
    lng = COALESCE(excluded.lng, places.lng),
    updated_at = datetime('now'),
    email = CASE
        WHEN excluded.email IS NOT NULL AND lower(excluded.email) NOT LIKE '%example%'
            THEN excluded.email
        ELSE places.email
    END,
    email_scraped_at = CASE
        WHEN excluded.email IS NOT NULL AND lower(excluded.email) NOT LIKE '%example%'
            THEN COALESCE(excluded.email_scraped_at, datetime('now'))
        ELSE places.email_scraped_at
    END,
    types = COALESCE(excluded.types, places.types)
"""

SELECT_ONE_SQL = "SELECT place_id,name,address,website,phone,lat,lng,email,types FROM places WHERE place_id=:place_id;"

SELECT_BY_TYPE_SQL = """
SELECT place_id,name,address,website,phone,lat,lng,email
FROM places
WHERE types LIKE :pattern
ORDER BY name;
"""

UPDATE_EMAIL_SQL = """
UPDATE places
SET email = :email,
    email_scraped_at = datetime('now'),
    updated_at = datetime('now')
WHERE place_id = :place_id AND :email IS NOT NULL AND lower(:email) NOT LIKE '%example%';
"""


class SQLitePlaceRepository(PlaceRepository):
    def __init__(self, path: str = "places.db"):
        self.engine = make_engine(path)

    @staticmethod
    def _types_to_set(s: str | None) -> set[str]:
        if not s:
            return set()
        return {t for t in s.strip("|").split("|") if t}

    @staticmethod
    def _set_to_types(ss: set[str]) -> str | None:
        if not ss:
            return None
        norm = sorted({t.strip() for t in ss if t and t.strip()})
        return "|" + "|".join(norm) + "|"

    @staticmethod
    def _merge_types(existing: str | None, new: list[str] | None) -> str | None:
        if not new:
            return existing
        s = SQLitePlaceRepository._types_to_set(existing)
        s.update([t.strip() for t in new if t and t.strip()])
        return SQLitePlaceRepository._set_to_types(s)

    def upsert(self, place: Place) -> None:
        with self.engine.begin() as conn:
            row = conn.execute(
                text("SELECT types FROM places WHERE place_id=:p"), {"p": place.place_id}
            ).one_or_none()
            merged = self._merge_types(row[0] if row else None, place.types)
            payload = {
                "place_id": place.place_id,
                "name": place.name,
                "address": place.address,
                "website": place.website,
                "phone": place.phone,
                "lat": place.lat,
                "lng": place.lng,
                "email": place.email,
                "email_scraped_at": None,
                "types": merged,
            }
            conn.execute(text(UPSERT_SQL), payload)

    def get_by_id(self, place_id: str):
        with self.engine.begin() as conn:
            row = conn.execute(text(SELECT_ONE_SQL), {"place_id": place_id}).one_or_none()
            if not row:
                return None
            d = dict(row._mapping)
            return Place(**d)

    def update_email(self, place_id: str, email: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(text(UPDATE_EMAIL_SQL), {"place_id": place_id, "email": email})

    def close(self):
        self.engine.dispose()
