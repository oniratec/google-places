from sqlalchemy import create_engine, text

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS places (
    place_id TEXT PRIMARY KEY,
    name TEXT,
    address TEXT,
    website TEXT,
    phone TEXT,
    lat REAL,
    lng REAL
);
"""

UPSERT_SQL = """
INSERT INTO places (place_id, name, address, website, phone, lat, lng)
VALUES (:place_id, :name, :address, :website, :phone, :lat, :lng)
ON CONFLICT(place_id) DO UPDATE SET
    name=excluded.name,
    address=excluded.address,
    website=excluded.website,
    phone=excluded.phone,
    lat=excluded.lat,
    lng=excluded.lng;
"""

class SQLiteStorage:
    def __init__(self, path="places.db"):
        self.engine = create_engine(f"sqlite:///{path}")
        with self.engine.begin() as conn:
            conn.execute(text(SCHEMA_SQL))

    def upsert(self, row: dict):
        with self.engine.begin() as conn:
            conn.execute(text(UPSERT_SQL), row)

    def close(self):
        self.engine.dispose()
