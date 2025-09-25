from sqlalchemy import text

from src.core.entities import Place
from src.core.ports import PlaceRepository

from .db import make_engine

UPSERT_SQL = """
INSERT INTO places (place_id, name, address, website, phone, lat, lng, email, updated_at, email_scraped_at)
VALUES (:place_id, :name, :address, :website, :phone, :lat, :lng, :email, datetime('now'), :email_scraped_at)
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
    END;
"""

SELECT_ONE_SQL = (
    "SELECT place_id,name,address,website,phone,lat,lng,email FROM places WHERE place_id=:place_id;"
)
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

    def upsert(self, place: Place) -> None:
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
        }
        with self.engine.begin() as conn:
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
