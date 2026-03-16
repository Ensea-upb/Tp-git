"""
Connecteur HTTP Career Page.

Stratégie :
  1. GET de l'URL configurée dans Source.base_url
  2. Respecte robots.txt
  3. Parse les blocs JSON-LD <script type="application/ld+json"> avec @type JobPosting
  4. Fallback : extraction heuristique de liens /jobs/, /careers/, /emploi/
     puis parsing JSON-LD sur chaque page détail
"""

import json
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from app.connectors.base import BaseConnector
from app.domain.dto.raw_offer_payload import RawOfferPayload
from app.infrastructure.db.models.source import Source

_JOB_PATH_RE = re.compile(
    r"/(jobs?|careers?|emplois?|offres?|postes?|recrutement)/",
    re.I,
)
_USER_AGENT = "Mozilla/5.0 (compatible; InternshipAgent/1.0)"
_TIMEOUT = 20
_MAX_FALLBACK_LINKS = 30


class HttpCareerPageConnector(BaseConnector):
    source_type = "career_page"

    def __init__(self, source: Source) -> None:
        super().__init__(source)
        self._robots: RobotFileParser | None = None

    # ------------------------------------------------------------------ #
    # is_available                                                         #
    # ------------------------------------------------------------------ #

    def is_available(self) -> bool:
        return bool(self.source.base_url)

    # ------------------------------------------------------------------ #
    # fetch                                                                #
    # ------------------------------------------------------------------ #

    def fetch(self) -> list[RawOfferPayload]:
        base_url = self.source.base_url
        if not base_url:
            self.logger.warning("HttpCareerPage : base_url absent pour %s", self.source.name)
            return []

        self._load_robots(base_url)

        if not self._can_fetch(base_url):
            self.logger.info("robots.txt interdit : %s", base_url)
            return []

        html = self._get_html(base_url)
        if not html:
            return []

        # Tentative 1 : JSON-LD directement dans la page
        payloads = self._extract_jsonld_offers(html, base_url)
        if payloads:
            self.logger.info(
                "HttpCareerPage %s — %d offres JSON-LD directes", self.source.name, len(payloads)
            )
            return payloads

        # Tentative 2 : liens de détail heuristiques
        links = self._extract_job_links(html, base_url)
        if not links:
            self.logger.info("HttpCareerPage %s — aucun lien job trouvé", self.source.name)
            return []

        self.logger.info(
            "HttpCareerPage %s — %d liens détail à scraper", self.source.name, len(links)
        )
        for link in links[:_MAX_FALLBACK_LINKS]:
            if not self._can_fetch(link):
                continue
            detail_html = self._get_html(link)
            if detail_html:
                found = self._extract_jsonld_offers(detail_html, link)
                payloads.extend(found)

        self.logger.info(
            "HttpCareerPage %s — %d offres récupérées", self.source.name, len(payloads)
        )
        return payloads

    # ------------------------------------------------------------------ #
    # robots.txt                                                           #
    # ------------------------------------------------------------------ #

    def _load_robots(self, base_url: str) -> None:
        parsed = urlparse(base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)
        try:
            rp.read()
        except Exception:
            pass  # Pas de robots.txt = tout autorisé
        self._robots = rp

    def _can_fetch(self, url: str) -> bool:
        if self._robots is None:
            return True
        return self._robots.can_fetch(_USER_AGENT, url)

    # ------------------------------------------------------------------ #
    # HTTP                                                                 #
    # ------------------------------------------------------------------ #

    def _get_html(self, url: str) -> str | None:
        try:
            resp = httpx.get(
                url,
                headers={"User-Agent": _USER_AGENT},
                follow_redirects=True,
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.text
        except Exception as exc:
            self.logger.warning("GET %s : %s", url, exc)
            return None

    # ------------------------------------------------------------------ #
    # JSON-LD parsing                                                      #
    # ------------------------------------------------------------------ #

    def _extract_jsonld_offers(self, html: str, page_url: str) -> list[RawOfferPayload]:
        soup = BeautifulSoup(html, "lxml")
        payloads: list[RawOfferPayload] = []

        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
            except (json.JSONDecodeError, TypeError):
                continue

            # Peut être un objet unique ou une liste
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict) and item.get("@type") == "JobPosting":
                    payload = self._parse_jsonld_item(item, page_url)
                    if payload:
                        payloads.append(payload)

        return payloads

    def _parse_jsonld_item(self, item: dict, page_url: str) -> RawOfferPayload | None:
        try:
            title = item.get("title") or item.get("name") or ""
            description = item.get("description") or ""

            # Localisation
            job_location = item.get("jobLocation", {})
            if isinstance(job_location, list):
                job_location = job_location[0] if job_location else {}
            address = job_location.get("address", {})
            if isinstance(address, str):
                location = address
            else:
                parts = [
                    address.get("streetAddress", ""),
                    address.get("addressLocality", ""),
                    address.get("addressRegion", ""),
                    address.get("addressCountry", ""),
                ]
                location = ", ".join(p for p in parts if p) or None

            # Entreprise
            hiring_org = item.get("hiringOrganization", {})
            company_name = (
                hiring_org.get("name") if isinstance(hiring_org, dict) else None
            )

            # URL de l'offre
            offer_url = item.get("url") or item.get("sameAs") or page_url

            # Date de publication
            published_at: datetime | None = None
            if raw_date := item.get("datePosted"):
                try:
                    published_at = datetime.fromisoformat(raw_date)
                except ValueError:
                    pass

            return RawOfferPayload(
                source_name=self.source.name,
                source_type=self.source_type,
                external_offer_id=item.get("identifier") or None,
                offer_url=offer_url,
                raw_title=title,
                raw_content=description,
                raw_location=location,
                raw_company_name=company_name or self.source.name,
                published_at_detected=published_at,
                metadata={
                    "employmentType": item.get("employmentType"),
                    "validThrough": item.get("validThrough"),
                    "baseSalary": item.get("baseSalary"),
                },
            )
        except Exception as exc:
            self.logger.warning("Erreur parsing JSON-LD item : %s", exc)
            return None

    # ------------------------------------------------------------------ #
    # Fallback heuristique                                                 #
    # ------------------------------------------------------------------ #

    def _extract_job_links(self, html: str, base_url: str) -> list[str]:
        soup = BeautifulSoup(html, "lxml")
        seen: set[str] = set()
        links: list[str] = []

        for a in soup.find_all("a", href=True):
            href: str = a["href"]
            absolute = urljoin(base_url, href)
            # Même domaine uniquement
            if urlparse(absolute).netloc != urlparse(base_url).netloc:
                continue
            if _JOB_PATH_RE.search(absolute) and absolute not in seen:
                seen.add(absolute)
                links.append(absolute)

        return links
