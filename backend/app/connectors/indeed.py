"""
Connecteur Indeed (RSS).

Source type : "indeed"
Flux RSS : https://fr.indeed.com/rss?q=<query>&l=<location>&sort=date

Indeed ne propose plus d'API publique officielle depuis 2023.
Ce connecteur utilise le flux RSS public (non authentifié) qui reste accessible.
Chaque item RSS contient : title, link, description (HTML), pubDate.
L'entreprise est extraite du titre (format "Poste — Entreprise") ou du contenu.

Limitation : ~25 résultats par requête RSS.
Pour LinkedIn, utiliser un futur connecteur dédié (cf. connectors/linkedin.py).
"""

import re
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

from app.connectors.base import BaseConnector
from app.domain.dto.raw_offer_payload import RawOfferPayload
from app.infrastructure.db.models.source import Source

_RSS_URL = "https://fr.indeed.com/rss"
_INDEED_NS = {"content": "http://purl.org/rss/1.0/modules/content/"}


class IndeedConnector(BaseConnector):
    """
    Connecteur Indeed via flux RSS.
    Configure la source avec metadata_json contenant :
      - query    : mots-clés (ex: "stage data engineer")
      - location : ville / pays (ex: "France")
      - sort     : "date" | "relevance" (défaut: "date")
    """

    source_type = "indeed"

    def is_available(self) -> bool:
        return True

    def _do_fetch(self) -> list[RawOfferPayload]:
        meta = getattr(self.source, "metadata_json", None) or {}
        params: dict = {"sort": meta.get("sort", "date")}
        if query := meta.get("query"):
            params["q"] = query
        if location := meta.get("location", "France"):
            params["l"] = location

        try:
            resp = self._http_get(
                _RSS_URL,
                params=params,
                headers={"User-Agent": "Mozilla/5.0 (compatible; InternshipAgent/1.0)"},
                follow_redirects=True,
            )
            xml_content = resp.text
        except Exception as exc:
            self.logger.error("Indeed RSS fetch error: %s", exc)
            return []

        results = self._parse_rss(xml_content)
        self.logger.info("Indeed fetch terminé — %d offres", len(results))
        return results

    def _parse_rss(self, xml_content: str) -> list[RawOfferPayload]:
        results: list[RawOfferPayload] = []
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as exc:
            self.logger.error("Indeed RSS XML parse error: %s", exc)
            return []

        channel = root.find("channel")
        if channel is None:
            return []

        for item in channel.findall("item"):
            payload = self._parse_item(item)
            if payload:
                results.append(payload)

        return results

    def _parse_item(self, item: ET.Element) -> RawOfferPayload | None:
        try:
            title_raw = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            description_html = (item.findtext("description") or "").strip()
            pub_date_str = item.findtext("pubDate") or ""

            # Nettoyage HTML basique
            description = re.sub(r"<[^>]+>", " ", description_html)
            description = re.sub(r"\s+", " ", description).strip()

            # Indeed encode le titre "Poste - Entreprise - Ville"
            company_name, location = self._extract_company_location(title_raw)
            # Le titre propre est la première partie
            job_title = title_raw.split(" - ")[0].strip() if " - " in title_raw else title_raw

            # guid comme ID externe
            guid = item.findtext("guid") or link

            published_at: datetime | None = None
            if pub_date_str:
                try:
                    from email.utils import parsedate_to_datetime
                    published_at = parsedate_to_datetime(pub_date_str).astimezone(timezone.utc)
                except Exception:
                    pass

            return RawOfferPayload(
                source_name=self.source.name,
                source_type=self.source_type,
                external_offer_id=guid or None,
                offer_url=link or None,
                raw_title=job_title,
                raw_content=description,
                raw_location=location,
                raw_company_name=company_name,
                published_at_detected=published_at,
                metadata={},
            )
        except Exception as exc:
            self.logger.warning("Indeed item parse error: %s", exc)
            return None

    @staticmethod
    def _extract_company_location(title: str) -> tuple[str, str]:
        """
        Indeed titre format: "Job Title - Company Name - City, Country"
        Retourne (company, location).
        """
        parts = [p.strip() for p in title.split(" - ")]
        if len(parts) >= 3:
            return parts[1], parts[2]
        if len(parts) == 2:
            return parts[1], ""
        return "", ""
