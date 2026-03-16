"""
Connecteur Welcome to the Jungle (WTTJ).

Source type : "wttj"
API publique : https://api.welcometothejungle.com/api/v1/jobs
Aucune authentification requise pour les recherches basiques.
Pagination via paramètres page / per_page.
"""

import time

import httpx

from app.connectors.base import BaseConnector
from app.domain.dto.raw_offer_payload import RawOfferPayload
from app.infrastructure.db.models.source import Source

_SEARCH_URL = "https://api.welcometothejungle.com/api/v1/jobs"
_PAGE_SIZE = 30
_RATE_LIMIT_PAUSE = 0.5


class WelcomeToTheJungleConnector(BaseConnector):
    """
    Connecteur Welcome to the Jungle.
    Configure la source avec metadata_json contenant :
      - query   : mots-clés (ex: "data stage")
      - country : code pays (ex: "FR")
      - contract_type : "internship" | "full_time" | …
    """

    source_type = "wttj"

    def is_available(self) -> bool:
        return True  # API publique, aucun credential requis

    def fetch(self) -> list[RawOfferPayload]:
        meta = getattr(self.source, "metadata_json", None) or {}
        params_base: dict = {
            "per_page": _PAGE_SIZE,
            "locale": "fr",
        }
        if query := meta.get("query"):
            params_base["query"] = query
        if country := meta.get("country", "FR"):
            params_base["country_code"] = country
        if contract := meta.get("contract_type"):
            params_base["contract_type[]"] = contract

        results: list[RawOfferPayload] = []
        page = 1

        while True:
            try:
                resp = httpx.get(
                    _SEARCH_URL,
                    params={**params_base, "page": page},
                    headers={"Accept": "application/json"},
                    timeout=20,
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                self.logger.error("WTTJ fetch error (page %d): %s", page, exc)
                break

            jobs = data.get("jobs", [])
            if not jobs:
                break

            for job in jobs:
                payload = self._parse_job(job)
                if payload:
                    results.append(payload)

            # Pagination : arrêt si dernière page
            pagination = data.get("meta", {}).get("pagination", {})
            total_pages = pagination.get("total_pages", 1)
            self.logger.info(
                "WTTJ page %d/%d — %d offres cumulées", page, total_pages, len(results)
            )
            if page >= total_pages:
                break
            page += 1
            time.sleep(_RATE_LIMIT_PAUSE)

        self.logger.info("WTTJ fetch terminé — %d offres", len(results))
        return results

    def _parse_job(self, job: dict) -> RawOfferPayload | None:
        try:
            org = job.get("organization", {})
            company_name = org.get("name", "")

            office = job.get("office", {})
            location = office.get("city") or office.get("country_code") or ""

            contract_raw = job.get("contract_type", "")
            slug = job.get("slug", "")
            offer_url = (
                f"https://www.welcometothejungle.com/fr/companies/"
                f"{org.get('slug', '')}/jobs/{slug}"
                if slug
                else None
            )

            description_parts = []
            if intro := job.get("description"):
                description_parts.append(intro)
            if profile := job.get("profile"):
                description_parts.append(profile)
            description = "\n\n".join(description_parts)

            return RawOfferPayload(
                source_name=self.source.name,
                source_type=self.source_type,
                external_offer_id=str(job.get("id", "")),
                offer_url=offer_url,
                raw_title=job.get("name", ""),
                raw_content=description,
                raw_location=location,
                raw_company_name=company_name,
                metadata={
                    "contract_type": contract_raw,
                    "remote": job.get("remote", ""),
                    "experience_years_min": job.get("experience_years_min"),
                },
            )
        except Exception as exc:
            self.logger.warning("WTTJ parse error for job %s: %s", job.get("id"), exc)
            return None
