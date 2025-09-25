from dataclasses import dataclass


@dataclass(frozen=True)
class Place:
    place_id: str
    name: str
    address: str | None = None
    website: str | None = None
    phone: str | None = None
    lat: float | None = None
    lng: float | None = None
    email: str | None = None
