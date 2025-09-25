from __future__ import annotations

from src.core.entities import Place
from src.core.ports import EmailScraper, PlaceRepository


class EnrichEmailsUseCase:
    def __init__(self, repo: PlaceRepository, scraper: EmailScraper):
        self.repo = repo
        self.scraper = scraper

    def run_for_place(self, place: Place):
        if place.website and not place.email:
            email = self.scraper.get_email_from_site(place.website)
            if email and "example" not in email.lower():
                self.repo.update_email(place.place_id, email)
                return email
        return None
