from __future__ import annotations

import logging
import math
import os
import time
from typing import Any

import backoff
import requests

from src.core.entities import Place
from src.core.ports import PlacesProvider

BASE_V1 = "https://places.googleapis.com/v1"
API_KEY_ENV = "GOOGLE_MAPS_API_KEY"


def _api_key() -> str:
    k = os.getenv(API_KEY_ENV)
    if not k:
        raise RuntimeError(f"Missing {API_KEY_ENV} in environment (.env).")
    return k


def _headers(field_mask: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": _api_key(),
        "X-Goog-FieldMask": field_mask,
    }


def _pid(name: str | None) -> str | None:
    return name.split("/", 1)[1] if name and "/" in name else name


def _deg_lat(m):
    return m / 111_320.0


def _deg_lng(m, lat):
    return m / (111_320.0 * max(0.2, math.cos(math.radians(lat))))


class PlacesV1Client(PlacesProvider):
    logger = logging.getLogger(__name__)
    
    @backoff.on_exception(backoff.expo, (requests.RequestException,), max_time=60)
    def text_search(
        self,
        *,
        query: str,
        location: str | None,
        radius_m: int | None,
        types: list[str] | None,
        max_results: int = 120,
    ) -> list[Place]:
        url = f"{BASE_V1}/places:searchText"
        field_mask = "places.name,places.displayName,places.formattedAddress,places.types"
        body: dict[str, Any] = {"textQuery": query, "pageSize": 20}
        if types:
            body["includedTypes"] = types
        if location and radius_m:
            lat, lng = map(float, location.split(","))
            body["locationBias"] = {
                "circle": {"center": {"latitude": lat, "longitude": lng}, "radius": int(radius_m)}
            }

        out: list[Place] = []
        token: str | None = None
        while True:
            payload = dict(body)
            if token:
                payload["pageToken"] = token
            r = requests.post(url, headers=_headers(field_mask), json=payload, timeout=30)
            data = r.json()
            if r.status_code >= 400 or "places" not in data:
                raise RuntimeError(f"Text Search v1 error: {data}")
            for p in data["places"]:
                out.append(
                    Place(
                        place_id=_pid(p.get("name")) or "",
                        name=(p.get("displayName") or {}).get("text") or "",
                        address=p.get("formattedAddress"),
                        types=p.get("types", []),
                    )
                )
                if len(out) >= max_results:
                    return out
            token = data.get("nextPageToken")
            if not token:
                return out
            time.sleep(1.6)

    @backoff.on_exception(backoff.expo, (requests.RequestException,), max_time=60)
    def place_details(self, place_id: str) -> Place:
        url = f"{BASE_V1}/places/{place_id}"
        field_mask = (
            "name,displayName,formattedAddress,websiteUri,internationalPhoneNumber,location,types"
        )
        r = requests.get(url, headers=_headers(field_mask), timeout=30)
        d = r.json()
        if r.status_code >= 400:
            raise RuntimeError(f"Place Details v1 error: {d}")
        loc = d.get("location") or {}
        return Place(
            place_id=place_id,
            name=(d.get("displayName") or {}).get("text") or "",
            address=d.get("formattedAddress"),
            website=d.get("websiteUri"),
            phone=d.get("internationalPhoneNumber"),
            lat=loc.get("latitude"),
            lng=loc.get("longitude"),
            types=d.get("types", []),
        )

    @backoff.on_exception(backoff.expo, (requests.RequestException,), max_time=60)
    def _nearby_circle(
        self,
        *,
        center_lat: float,
        center_lng: float,
        radius_m: int,
        types: list[str],
        excluded_types: list[str] | None = None,
        rank_preference: str = "DISTANCE",
    ) -> list[Place]:
        url = f"{BASE_V1}/places:searchNearby"
        field_mask = (
            "places.name,places.displayName,places.formattedAddress,places.location,places.types"
        )
        body = {
            "includedTypes": types,
            "excludedTypes": excluded_types or [],
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": center_lat, "longitude": center_lng},
                    "radius": int(radius_m),
                }
            },
            "maxResultCount": 20,
            "rankPreference": rank_preference,
        }
        out: list[Place] = []
        token: str | None = None
        while True:
            payload = dict(body)
            if token:
                payload["pageToken"] = token
            r = requests.post(url, headers=_headers(field_mask), json=payload, timeout=30)
            data = r.json()
            if r.status_code >= 400:
                raise RuntimeError(f"Nearby v1 error: {data}")

            if "places" not in data:
                break

            for p in data["places"]:
                loc = p.get("location") or {}
                out.append(
                    Place(
                        place_id=_pid(p.get("name")) or "",
                        name=(p.get("displayName") or {}).get("text") or "",
                        address=p.get("formattedAddress"),
                        lat=loc.get("latitude"),
                        lng=loc.get("longitude"),
                        types=p.get("types", []),
                    )
                )
            token = data.get("nextPageToken")
            if not token:
                break
            time.sleep(1.5)
        return out

    def _grid_centers(
        self, *, center_lat: float, center_lng: float, radius_m: int, cell_radius_m: int
    ) -> list[tuple[float, float]]:
        step_m = cell_radius_m * 1.4  # ~30% solape
        lat_step = _deg_lat(step_m)
        lng_step = _deg_lng(step_m, center_lat)
        rings = max(1, math.ceil(radius_m / step_m))
        centers = []
        for dy in range(-rings, rings + 1):
            for dx in range(-rings, rings + 1):
                centers.append((center_lat + dy * lat_step, center_lng + dx * lng_step))
        return centers

    def nearby_grid_search(
        self,
        *,
        center_lat: float,
        center_lng: float,
        radius_m: int,
        types: list[str],
        cell_radius_m: int = 600,
        overall_max: int = 2000,
        excluded_types: list[str] | None = None,
        rank_preference: str = "DISTANCE",
    ) -> list[Place]:
        centers = self._grid_centers(
            center_lat=center_lat,
            center_lng=center_lng,
            radius_m=radius_m,
            cell_radius_m=cell_radius_m,
        )
        seen, out = set(), []
        for lat, lng in centers:
            batch = self._nearby_circle(
                center_lat=lat,
                center_lng=lng,
                radius_m=cell_radius_m,
                types=types,
                excluded_types=excluded_types,
                rank_preference=rank_preference,
            )
            
            for p in batch:
                self.logger.info(f"[BATCH] {p.name} -> {p.website}")
                if p.place_id and p.place_id not in seen:
                    seen.add(p.place_id)
                    out.append(p)
                    if len(out) >= overall_max:
                        return out
            time.sleep(0.2)  # cortesía
        return out
