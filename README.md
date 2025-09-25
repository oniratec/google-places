# Google Places Collector + Email Scraper

Collect local businesses using **Google Places API**, enrich each result with a simple
**email scraper** (via `mailto:` links), and store everything in **SQLite**.

> Google Places does **not** provide emails. This project fetches `website` from Place Details,
then visits the business website (home and contact page) to find a `mailto:` address.

---

## Features

- **Search** with Places *Text Search* or by *location + radius + type* (e.g., `hair_salon`, `restaurant`).
- **Details** via Place Details: name, formatted address, website, phone, coordinates.
- **Email scraping**: parse `mailto:` links on the homepage and up to 3 contact pages.
- **SQLite storage** with **UPSERT** using `place_id` as the primary key.
- Optional quality tooling: **Ruff** (lint/format) and **mypy** (type checking).

---

## Project Structure

```
.
├─ .env                      # API key (do not commit)
├─ README.md
├─ .gitignore
└─ src/
   ├─ main.py                # CLI entry point
   ├─ google_places.py       # Google Places client (Text Search + Details)
   ├─ storage.py             # SQLite repository (schema + upsert + email column)
   └─ email_scraper.py       # Scrapes website to find mailto emails
```

---

## Requirements

- **Python 3.10+**
- A **Google Cloud** project with **Places API** enabled
- A **Google Maps Platform API key** with Places access

### Google Cloud (quick steps)
1. Create a project in Google Cloud Console.
2. Enable **Places API**.
3. Create an **API key** under *APIs & Services → Credentials*.
4. **Restrict** your key (HTTP referrers, IPs, or app restrictions as needed).
5. Put the key in your `.env` file (see below).

> Review Google Maps Platform pricing and quotas to avoid surprises. For small usage,
free tiers are usually enough; at scale, costs apply.

---

## Setup

### 1) Create and activate a virtual environment
```bash
python -m venv .venv
# mac/linux
source .venv/bin/activate
# windows
.\.venv\Scriptsctivate
```

### 2) Install dependencies
If you use `pyproject.toml`:
```bash
pip install -e .
```

Or, if you have `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 3) Environment variables
Create **`.env`** in the project root:
```ini
GOOGLE_MAPS_API_KEY=YOUR_GOOGLE_MAPS_API_KEY
```

> The app loads `.env` at startup from the project root. Make sure you run commands from the root.

---

## Usage

### Text Search example
```bash
python -m src.main --query "hair salon in malasana" --max 80
```

### Location + radius + type example
```bash
python -m src.main --location "40.4203,-3.7045" --radius 1500 --type hair_salon --max 100
```

**What happens:**
1. Uses Text Search (or your location+type) to collect candidate `place_id`s.
2. Calls Place Details for each to get: `name`, `formatted_address`, `website`, `phone`, `lat`, `lng`.
3. If `website` exists, runs the scraper:
   - Parses homepage `mailto:` links.
   - If none, follows up to **3** contact-like links (e.g., `contact`, `contacto`) and searches again.
4. Upserts into **SQLite** (`places.db`) with a simple migration to add `email` column if missing.

---

## Database (SQLite)

Default DB file: **`places.db`**. Table schema (`places`):

| column     | type | notes                                     |
|------------|------|-------------------------------------------|
| place_id   | TEXT | **PRIMARY KEY** (stable Google Place ID)  |
| name       | TEXT | business name                             |
| address    | TEXT | formatted address                         |
| website    | TEXT | business website (if any)                 |
| phone      | TEXT | phone (if any)                            |
| lat        | REAL | latitude                                  |
| lng        | REAL | longitude                                 |
| email      | TEXT | email found via `mailto:` (if any)        |

### Inspect with SQLite CLI
```bash
sqlite3 places.db
.tables
.schema places

.headers on
.mode column

SELECT COUNT(*) FROM places;
SELECT name, website, email FROM places WHERE email IS NOT NULL LIMIT 20;
SELECT name, website FROM places WHERE website IS NOT NULL LIMIT 20;

.quit
```

### Export to CSV (quick method)
```bash
sqlite3 places.db <<'SQL'
.headers on
.mode csv
.output places.csv
SELECT * FROM places;
.output stdout
SQL
```

---

## CLI Options

```
--query    "search text", e.g. "barbers in lavapies"
--location "lat,lng"      e.g. "40.4203,-3.7045"
--radius   N (meters)     e.g. 1500
--type     place type     e.g. hair_salon, restaurant, barber_shop
--max      result limit   default 120
--dbpath   SQLite path    default places.db
```

Use either `--query` **or** (`--location` + `--radius` + `--type`).

---

## Quality Tooling (optional but recommended)

### Ruff (lint & format) + mypy (types)
Add to your `pyproject.toml`:
```toml
[tool.ruff]
line-length = 100
target-version = "py310"
lint.select = ["E","F","I","UP","B","SIM","C4","RET","RUF"]
lint.ignore = ["ANN101","ANN102"]
exclude = [".venv",".mypy_cache",".ruff_cache","build","dist","__pycache__"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.mypy]
python_version = "3.10"
ignore_missing_imports = true
strict_optional = true
disallow_untyped_defs = true
```

Install and enable pre-commit hooks:
```bash
pip install pre-commit ruff mypy
pre-commit install
```

`.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.2
    hooks:
      - id: mypy
```

---

## Troubleshooting

- **`ModuleNotFoundError` importing your modules**  
  Run from project root and use module form: `python -m src.main`. Ensure `src/__init__.py` exists.

- **`RuntimeError: Missing GOOGLE_MAPS_API_KEY`**  
  Ensure `.env` exists at the project root and is loaded before API calls.

- **`REQUEST_DENIED` / API not authorized**  
  Verify Places API is enabled and API key restrictions are correct.

- **Quota / rate issues**  
  Reduce `--max`, add backoff/rate-limiting, or enable billing for higher quotas.

---

## Legal & Ethics

- Respect **robots.txt** and site terms when scraping.
- Do not use collected emails for spam; comply with **GDPR/PECR/local laws**.
- Follow **Google Maps Platform ToS** (avoid prohibited caching/redistribution).

---

## License

MIT (or choose your preferred license).
