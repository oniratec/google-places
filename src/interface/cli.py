import argparse
import logging
import time

from src.app.use_cases.collect_places import CollectPlacesUseCase
from src.app.use_cases.enrich_emails import EnrichEmailsUseCase
from src.infrastructure.persistence.sqlite.place_repository import SQLitePlaceRepository
from src.infrastructure.providers.places.client import PlacesV1Client
from src.infrastructure.scrapers.email_scraper import MailtoScraper
from src.utils.config import load_env
from src.utils.logging import setup_logging


def build_container(dbpath: str):
    load_env()
    repo = SQLitePlaceRepository(dbpath)
    provider = PlacesV1Client()
    scraper = MailtoScraper()
    return repo, provider, scraper


def main():
    setup_logging()
    ap = argparse.ArgumentParser(description="Places collector (v1) + email scraper")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("collect-text")
    p1.add_argument("--query", required=True)
    p1.add_argument("--location", default=None)
    p1.add_argument("--radius", type=int, default=None)
    p1.add_argument("--type", default=None)
    p1.add_argument("--max", type=int, default=120)
    p1.add_argument("--dbpath", default="places.db")

    p2 = sub.add_parser("collect-nearby")
    p2.add_argument("--location", required=True, help="lat,lng")
    p2.add_argument("--radius", type=int, required=True)
    p2.add_argument("--types", required=True)
    p2.add_argument("--cell-radius", type=int, default=600)
    p2.add_argument("--max", type=int, default=1000)
    p2.add_argument("--dbpath", default="places.db")

    p3 = sub.add_parser("enrich-missing")
    p3.add_argument("--place-id", required=False)
    p3.add_argument("--dbpath", default="places.db")

    args = ap.parse_args()

    repo, provider, scraper = build_container(args.dbpath)
    cli_types = [t.strip() for t in (args.types or "").split(",") if t.strip()]

    try:
        if args.cmd == "collect-text":
            uc = CollectPlacesUseCase(repo, provider)
            places = uc.run_text(
                query=args.query,
                location=args.location,
                radius_m=args.radius,
                types_=cli_types,
                max_results=args.max,
            )
            # Scraping “al vuelo”
            enr = EnrichEmailsUseCase(repo, scraper)
            for p in places:
                if p.website:
                    email = enr.run_for_place(p)
                    if email:
                        print(f"[EMAIL] {p.name} -> {email}")
                    time.sleep(0.05)

        elif args.cmd == "collect-nearby":
            lat, lng = map(float, args.location.split(","))
            uc = CollectPlacesUseCase(repo, provider)
            places = uc.run_nearby_grid(
                center_lat=lat,
                center_lng=lng,
                radius_m=args.radius,
                types=cli_types,
                cell_radius_m=args.cell_radius,
                overall_max=args.max,
            )
            enr = EnrichEmailsUseCase(repo, scraper)
            for p in places:
                if p.website:
                    email = enr.run_for_place(p)
                    if email:
                        print(f"[EMAIL] {p.name} -> {email}")
                    time.sleep(0.05)

        elif args.cmd == "enrich-missing":
            # enriquecimiento puntual por place_id si lo pasas (rápido)
            if args.place_id:
                p = repo.get_by_id(args.place_id)
                if p:
                    email = EnrichEmailsUseCase(repo, scraper).run_for_place(p)
                    print(f"[EMAIL] {p.name} -> {email or '-'}")
            else:
                print("Pass --place-id (or implement a repo method to iterate missing emails).")

    finally:
        repo.close()


if __name__ == "__main__":
    main()
