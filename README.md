# Google Places Collector + Email Scraper

A **Clean Architecture** application that collects local businesses using **Google Places API**, 
enriches each result with email addresses scraped from business websites, and stores everything in **SQLite**.

> Google Places does **not** provide emails directly. This project fetches the `website` from Place Details,
then visits the business website (home and contact pages) to find `mailto:` addresses.

---

## Features

- **Search** with Places *Text Search* or by *location + radius + type* (e.g., `hair_salon`, `restaurant`).
- **Details** via Place Details API: name, formatted address, website, phone, coordinates.
- **Email scraping**: intelligently parses `mailto:` links from homepages and contact pages.
- **SQLite storage** with **UPSERT** operations using `place_id` as the primary key.
- **Clean Architecture**: Well-structured codebase with clear separation of concerns.
- **Type safety**: Full type hints with **mypy** support.
- **Quality tooling**: **Ruff** (lint/format) and **mypy** (type checking).

---

## Architecture

This project follows **Clean Architecture** principles with clear separation of layers:

```
src/
├── app/                     # Application layer
│   └── use_cases/          # Business use cases
│       ├── collect_places.py
│       └── enrich_emails.py
├── core/                    # Domain layer
│   ├── entities.py         # Domain entities (Place)
│   ├── errors.py           # Domain exceptions
│   └── ports.py            # Abstract interfaces
├── infrastructure/         # Infrastructure layer
│   ├── persistence/
│   │   └── sqlite/         # SQLite implementation
│   ├── providers/
│   │   └── places/         # Google Places API client
│   └── scrapers/           # Email scraping implementation
├── interface/              # Interface layer
│   └── cli.py              # Command-line interface
└── utils/                  # Shared utilities
    ├── config.py
    └── logging.py
```

---

## Requirements

- **Python 3.10+**
- A **Google Cloud** project with **Places API** enabled
- A **Google Maps Platform API key** with Places access

### Dependencies

The project uses modern Python dependencies managed via `pyproject.toml`:

- **requests**: HTTP client for API calls and web scraping
- **python-dotenv**: Environment variable management
- **backoff**: Retry logic with exponential backoff
- **SQLAlchemy 2.0+**: Modern ORM for database operations
- **pydantic 2.0+**: Data validation and serialization

### Google Cloud (quick steps)
1. Create a project in Google Cloud Console.
2. Enable **Places API (New)**.
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
Install the project in development mode:
```bash
pip install -e .
```

This will install all required dependencies listed in `pyproject.toml`.

### 3) Environment variables
Create **`.env`** in the project root:
```ini
GOOGLE_MAPS_API_KEY=YOUR_GOOGLE_MAPS_API_KEY
```

> The app loads `.env` at startup from the project root. Make sure you run commands from the root.

---

## Usage

The application provides a command-line interface with different commands for various operations.

### Collect places by text search
```bash
python -m src.interface.cli collect-text --query "hair salon in malasana" --max 80
```

### Collect places by location and type
```bash
python -m src.interface.cli collect-nearby --location "40.4203,-3.7045" --radius 1500 --type hair_salon --max 100
```

### Enrich existing places with emails
```bash
python -m src.interface.cli enrich-emails --max 50
```

**What happens:**
1. **collect-text/collect-nearby**: Uses Google Places API to find businesses and store basic details.
2. **enrich-emails**: For places with websites, runs the email scraper:
   - Parses homepage `mailto:` links.
   - If none found, follows up to **3** contact-like links (e.g., `contact`, `contacto`) and searches again.
3. All data is stored in **SQLite** (`places.db`) with automatic schema management.

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

## CLI Commands & Options

### collect-text
Collect places using text search.
```bash
python -m src.interface.cli collect-text --query "SEARCH_TEXT" [OPTIONS]
```
- `--query`: Search text (required)
- `--location`: Optional location bias "lat,lng"
- `--radius`: Search radius in meters
- `--types`: Place type filters separated by commas
- `--max`: Maximum results (default: 120)
- `--dbpath`: SQLite database path (default: places.db)

### collect-nearby  
Collect places by location, radius, and type.
```bash
python -m src.interface.cli collect-nearby --location "LAT,LNG" --radius METERS --types TYPE [OPTIONS]
```
- `--location`: Center point "lat,lng" (required)
- `--radius`: Search radius in meters (required)
- `--types`: Place types (required, e.g., restaurant, hair_salon)
- `--max`: Maximum results (default: 120)
- `--dbpath`: SQLite database path (default: places.db)

### enrich-emails
Scrape emails from existing places with websites.
```bash
python -m src.interface.cli enrich-emails [OPTIONS]
```
- `--max`: Maximum places to process (default: 50)
- `--dbpath`: SQLite database path (default: places.db)

---

## Quality Tooling

The project includes comprehensive code quality tools configured in `pyproject.toml`:

### Ruff (linting & formatting)
```toml
[tool.ruff]
line-length = 100
target-version = "py310"
lint.select = ["E","F","I","UP","B","SIM","C4","RET","RUF"]
lint.ignore = ["ANN101","ANN102"]
```

### mypy (type checking)  
```toml
[tool.mypy]
python_version = "3.10"
strict_optional = true
disallow_untyped_defs = true
ignore_missing_imports = true
```

### Running quality checks
```bash
# Format code
ruff format

# Lint code  
ruff check

# Type check
mypy src/
```

---

## Troubleshooting

- **`ModuleNotFoundError` importing modules**  
  Run from project root: `python -m src.interface.cli`. Ensure all `__init__.py` files exist.

- **`RuntimeError: Missing GOOGLE_MAPS_API_KEY`**  
  Ensure `.env` exists at the project root with your API key.

- **`REQUEST_DENIED` / API authorization errors**  
  Verify Places API (New) is enabled and API key restrictions are correct.

- **Database connection issues**  
  The SQLite database is created automatically. Check file permissions if issues persist.

- **Email scraping timeouts**  
  Some websites may be slow or block requests. The scraper includes retry logic and timeouts.

---

## Development

### Running tests
```bash
# Add your test runner here when tests are implemented
pytest
```

### Project structure guidelines
- **Domain logic** goes in `src/core/`
- **Use cases** go in `src/app/use_cases/`  
- **External integrations** go in `src/infrastructure/`
- **User interfaces** go in `src/interface/`
- **Utilities** go in `src/utils/`

---

## Legal & Ethics

- Respect **robots.txt** and site terms when scraping.
- Do not use collected emails for spam; comply with **GDPR/PECR/local laws**.
- Follow **Google Maps Platform ToS** (avoid prohibited caching/redistribution).

---

## License

MIT (or choose your preferred license).
