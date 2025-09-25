# src/infrastructure/persistence/sqlite/db.py
from sqlalchemy import create_engine, text

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS places (
    place_id TEXT PRIMARY KEY,
    name     TEXT,
    address  TEXT,
    website  TEXT,
    phone    TEXT,
    lat      REAL,
    lng      REAL
);
"""

MIGRATIONS = [
    ("email", "ALTER TABLE places ADD COLUMN email TEXT;"),
    ("updated_at", "ALTER TABLE places ADD COLUMN updated_at TEXT;"),
    ("email_scraped_at", "ALTER TABLE places ADD COLUMN email_scraped_at TEXT;"),
]


def make_engine(path: str = "places.db"):
    engine = create_engine(f"sqlite:///{path}", future=True)
    with engine.begin() as conn:
        conn.execute(text(SCHEMA_SQL))

        # Add missing columns (no DEFAULT expressions!)
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info('places');")).all()}
        for col, sql in MIGRATIONS:
            if col not in cols:
                conn.execute(text(sql))
                if col == "updated_at":
                    # one-time backfill
                    conn.execute(
                        text(
                            "UPDATE places SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL;"
                        )
                    )

        # (optional) useful index for lookups
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_places_email ON places(email);"))

    return engine
