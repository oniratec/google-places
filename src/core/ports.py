from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from .entities import Place


class PlaceRepository(ABC):
    @abstractmethod
    def upsert(self, place: Place) -> None: ...
    @abstractmethod
    def get_by_id(self, place_id: str) -> Place | None: ...
    @abstractmethod
    def update_email(self, place_id: str, email: str) -> None: ...


class PlacesProvider(Protocol):
    def text_search(
        self,
        *,
        query: str,
        location: str | None,
        radius_m: int | None,
        type_: str | None,
        max_results: int,
    ) -> list[Place]: ...

    def nearby_grid_search(
        self,
        *,
        center_lat: float,
        center_lng: float,
        radius_m: int,
        type_: str,
        cell_radius_m: int,
        overall_max: int,
    ) -> list[Place]: ...

    def place_details(self, place_id: str) -> Place: ...


class EmailScraper(Protocol):
    def get_email_from_site(self, website_url: str) -> str | None: ...
