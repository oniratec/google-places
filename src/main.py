import argparse

from dotenv import load_dotenv

from src.google_places import place_details, text_search
from src.storage import SQLiteStorage


def parse_args():
    ap = argparse.ArgumentParser(description="Colector de empresas (Places API → SQLite)")
    ap.add_argument("--query", help='Texto, ej. "peluquería en Malasaña"', default=None)
    ap.add_argument("--location", help='Coordenadas "lat,lng", ej. "40.425,-3.703"', default=None)
    ap.add_argument("--radius", type=int, help="Radio en metros", default=None)
    ap.add_argument(
        "--type", dest="type_", help='Tipo de lugar, ej. "hair_salon","restaurant"', default=None
    )
    ap.add_argument("--max", type=int, default=120, help="Límite de resultados")
    ap.add_argument("--dbpath", default="places.db")
    return ap.parse_args()


def main():
    load_dotenv()
    args = parse_args()

    storage = SQLiteStorage(args.dbpath)
    try:
        # 1) Buscar candidatos
        hits = text_search(
            query=args.query,
            location=args.location,
            radius=args.radius,
            type_=args.type_,
            max_results=args.max,
        )
        print(f"Encontrados {len(hits)} candidatos. Enriqueciendo con Place Details...")

        # 2) Enriquecer y guardar en SQLite
        for h in hits:
            if not h.get("place_id"):
                continue
            d = place_details(h["place_id"])
            storage.upsert(d)
            print(f"OK: {d['name']} | {d.get('website') or '-'}")

        print("Datos guardados en", args.dbpath)
    finally:
        storage.close()


if __name__ == "__main__":
    main()
