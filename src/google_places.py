import os
import time

import backoff
import requests

BASE = "https://maps.googleapis.com/maps/api/place"


def _get(url, params):
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise RuntimeError("Falta GOOGLE_MAPS_API_KEY en el entorno (.env).")
    params["key"] = api_key
    return requests.get(url, params=params, timeout=20)


@backoff.on_exception(backoff.expo, (requests.RequestException,), max_time=60)
def text_search(query=None, location=None, radius=None, type_=None, max_results=120):
    """
    Devuelve place_id básicos usando Text Search (o Nearby si quieres).
    """
    url = f"{BASE}/textsearch/json"
    params = {}
    if query:
        params["query"] = query
    if location and radius:
        params["location"] = location  # "lat,lng"
        params["radius"] = int(radius)  # metros
    if type_:
        params["type"] = type_

    collected = []
    next_page_token = None

    while True:
        if next_page_token:
            # Google dice esperar un poco antes de usar next_page_token
            time.sleep(2)
            resp = _get(url, {"pagetoken": next_page_token})
        else:
            resp = _get(url, params)

        data = resp.json()
        status = data.get("status")
        if status not in ("OK", "ZERO_RESULTS"):
            raise RuntimeError(
                f"Google Places Text Search status: {status}. {data.get('error_message', '')}"
            )

        results = data.get("results", [])
        for r in results:
            collected.append(
                {
                    "place_id": r.get("place_id"),
                    "name": r.get("name"),
                    "formatted_address": r.get("formatted_address"),
                }
            )
            if len(collected) >= max_results:
                return collected

        next_page_token = data.get("next_page_token")
        if not next_page_token:
            return collected


@backoff.on_exception(backoff.expo, (requests.RequestException,), max_time=60)
def place_details(place_id):
    """
    Pide campos concretos para no gastar de más.
    """
    url = f"{BASE}/details/json"
    fields = "name,formatted_address,website,formatted_phone_number,international_phone_number,geometry/location"
    resp = _get(url, {"place_id": place_id, "fields": fields})
    data = resp.json()
    status = data.get("status")
    if status != "OK":
        raise RuntimeError(f"Place Details status: {status}. {data.get('error_message', '')}")
    r = data["result"]
    return {
        "place_id": place_id,
        "name": r.get("name"),
        "address": r.get("formatted_address"),
        "website": r.get("website"),
        "phone": r.get("formatted_phone_number") or r.get("international_phone_number"),
        "lat": (r.get("geometry", {}) or {}).get("location", {}).get("lat"),
        "lng": (r.get("geometry", {}) or {}).get("location", {}).get("lng"),
    }
