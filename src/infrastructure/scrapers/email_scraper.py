from __future__ import annotations

from typing import Iterable, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


class MailtoScraper:
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari"
    }

    def _fetch(self, url: str, timeout: int = 15) -> Optional[str]:
        try:
            r = requests.get(
                url, headers=self.DEFAULT_HEADERS, timeout=timeout, allow_redirects=True
            )
            if r.status_code >= 400:
                return None
            return r.text
        except requests.RequestException:
            return None

    def _extract_mailtos(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        emails: list[str] = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.lower().startswith("mailto:"):
                addr = href.split(":", 1)[1].split("?", 1)[0].strip()
                if addr and "example" not in addr.lower() and addr not in emails:
                    emails.append(addr)
        return emails

    def _candidate_contact_paths(self, links: Iterable[str]) -> list[str]:
        keys = ("contact", "contacto", "contato", "kontakt")
        cands = []
        for h in links:
            l = h.lower()
            if any(k in l for k in keys):
                cands.append(h)
        return cands[:3]

    def get_email_from_site(self, website_url: str) -> Optional[str]:
        if not website_url:
            return None
        parsed = urlparse(website_url)
        if not parsed.scheme:
            website_url = "https://" + website_url

        html = self._fetch(website_url)
        if html:
            emails = self._extract_mailtos(html)
            if emails:
                return emails[0]
            soup = BeautifulSoup(html, "html.parser")
            links = [a["href"] for a in soup.find_all("a", href=True)]
            for href in self._candidate_contact_paths(links):
                target = urljoin(website_url, href)
                html2 = self._fetch(target)
                if not html2:
                    continue
                emails2 = self._extract_mailtos(html2)
                if emails2:
                    return emails2[0]
        return None
