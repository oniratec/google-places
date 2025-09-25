from __future__ import annotations

from typing import Optional

from src.core.entities import Place
from src.core.ports import PlaceRepository, PlacesProvider


class CollectPlacesUseCase:
    def __init__(self, repo: PlaceRepository, provider: PlacesProvider):
        self.repo = repo
        self.provider = provider

    def run_text(
        self,
        *,
        query: str,
        location: Optional[str],
        radius_m: Optional[int],
        type_: Optional[str],
        max_results: int,
    ) -> list[Place]:
        hits = self.provider.text_search(
            query=query, location=location, radius_m=radius_m, type_=type_, max_results=max_results
        )
        return self._details_and_store(hits)

    def run_nearby_grid(
        self,
        *,
        center_lat: float,
        center_lng: float,
        radius_m: int,
        type_: str,
        cell_radius_m: int,
        overall_max: int,
    ) -> list[Place]:
        hits = self.provider.nearby_grid_search(
            center_lat=center_lat,
            center_lng=center_lng,
            radius_m=radius_m,
            type_=type_,
            cell_radius_m=cell_radius_m,
            overall_max=overall_max,
        )
        return self._details_and_store(hits)

    def _details_and_store(self, hits: list[Place]) -> list[Place]:
        out: list[Place] = []
        for h in hits:
            if not h.place_id:
                continue
            if self.repo.get_by_id(h.place_id):
                continue  # ya existe
            d = self.provider.place_details(h.place_id)
            self.repo.upsert(d)
            out.append(d)
        return out
