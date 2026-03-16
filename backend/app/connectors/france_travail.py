"""
Connecteur France Travail (ex-Pôle Emploi) — API Offres d'emploi v2.

Documentation : https://francetravail.io/data/api/offres-emploi
Auth           : OAuth2 client_credentials
Scope          : api_offresdemploiv2 o2dsoffre
"""

import time
from datetime import datetime, timezone

import httpx

from app.connectors.base import BaseConnector
from app.domain.dto.raw_offer_payload import RawOfferPayload
from app.infrastructure.db.models.source import Source

_TOKEN_URL = (
    "https://entreprise.francetravail.fr/connexion/oauth2/access_token"
    "?realm=%2Fpartenaire"
)
_SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
_SCOPE = "api_offresdemploiv2 o2dsoffre"
_PAGE_SIZE = 150  # max autorisé par l'API
_RATE_LIMIT_PAUSE = 1.0  # secondes entre les pages


class FranceTravailConnector(BaseConnector):
    source_type = "api_officielle"

    def __init__(self, source: Source, client_id: str, client_secret: str) -> None:
        super().__init__(source)
        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token: str | None = None

    # ------------------------------------------------------------------ #
    # Auth                                                                 #
    # ------------------------------------------------------------------ #

    def _authenticate(self) -> bool:
        """Récupère un access token OAuth2. Retourne False si échec."""
        try:
            resp = httpx.post(
                _TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "scope": _SCOPE,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=15,
            )
            resp.raise_for_status()
            self._access_token = resp.json()["access_token"]
            return True
        except Exception as exc:
            self.logger.error("FT auth failed: %s", exc)
            return False

    # ------------------------------------------------------------------ #
    # is_available                                                         #
    # ------------------------------------------------------------------ #

    def is_available(self) -> bool:
        return bool(self._client_id and self._client_secret)

    # ------------------------------------------------------------------ #
    # fetch                                                                #
    # ------------------------------------------------------------------ #

    def fetch(self) -> list[RawOfferPayload]:
        if not self.is_available():
            self.logger.warning("FT credentials absents — connecteur désactivé")
            return []

        if not self._authenticate():
            return []

        params = self._build_params()
        results: list[RawOfferPayload] = []
        start = 0

        while True:
            page_params = {**params, "range": f"{start}-{start + _PAGE_SIZE - 1}"}
            try:
                data = self._get_page(page_params)
            except Exception as exc:
                self.logger.error("FT fetch error (range %d): %s", start, exc)
                break

            offers = data.get("resultats", [])
            if not offers:
                break

            for item in offers:
                payload = self._parse_item(item)
                if payload:
                    results.append(payload)

            content_range = data.get("Content-Range", "")
            total = self._parse_total(content_range, data)
            fetched_so_far = start + len(offers)

            self.logger.info(
                "FT page %d–%d / ~%s — %d offres récupérées",
                start,
                start + len(offers) - 1,
                total or "?",
                len(results),
            )

            if total and fetched_so_far >= total:
                break
            if len(offers) < _PAGE_SIZE:
                break

            start += _PAGE_SIZE
            time.sleep(_RATE_LIMIT_PAUSE)

        self.logger.info("FT fetch terminé — %d offres", len(results))
        return results

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _build_params(self) -> dict:
        """Paramètres de recherche à partir des métadonnées de la source."""
        meta = getattr(self.source, "metadata_json", None) or {}
        params: dict = {}
        if "typeContrat" in meta:
            params["typeContrat"] = meta["typeContrat"]
        if "commune" in meta:
            params["commune"] = meta["commune"]
        if "motsCles" in meta:
            params["motsCles"] = meta["motsCles"]
        if "distance" in meta:
            params["distance"] = meta["distance"]
        return params

    def _get_page(self, params: dict) -> dict:
        headers = {"Authorization": f"Bearer {self._access_token}"}
        resp = httpx.get(_SEARCH_URL, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _parse_total(content_range: str, data: dict) -> int | None:
        """Extrait le total depuis l'en-tête Content-Range ou la réponse."""
        # Format: "offres 0-149/3456"
        if content_range and "/" in content_range:
            try:
                return int(content_range.split("/")[-1])
            except ValueError:
                pass
        return data.get("nbResultats")

    def _parse_item(self, item: dict) -> RawOfferPayload | None:
        try:
            published_at: datetime | None = None
            if raw_date := item.get("dateCreation"):
                try:
                    published_at = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                except ValueError:
                    pass

            lieu = item.get("lieuTravail", {})
            location = lieu.get("libelle") or lieu.get("commune")

            entreprise = item.get("entreprise", {})
            company_name = entreprise.get("nom") or entreprise.get("entreprise")

            description = item.get("description", "")
            qualite_pro = item.get("qualitesProfessionnelles", [])
            if qualite_pro:
                extras = " ".join(q.get("libelle", "") for q in qualite_pro)
                description = f"{description} {extras}".strip()

            offer_id = item.get("id", "")
            offer_url = (
                f"https://www.francetravail.fr/offres/recherche/detail/{offer_id}"
                if offer_id
                else None
            )

            return RawOfferPayload(
                source_name=self.source.name,
                source_type=self.source_type,
                external_offer_id=offer_id or None,
                offer_url=offer_url,
                raw_title=item.get("intitule", ""),
                raw_content=description,
                raw_location=location,
                raw_company_name=company_name,
                published_at_detected=published_at,
                metadata={
                    "typeContrat": item.get("typeContrat"),
                    "secteurActiviteLibelle": item.get("secteurActiviteLibelle"),
                    "experienceLibelle": item.get("experienceLibelle"),
                    "niveauFormation": (
                        item.get("formations", [{}])[0].get("niveauLibelle")
                        if item.get("formations")
                        else None
                    ),
                },
            )
        except Exception as exc:
            self.logger.warning("Impossible de parser l'offre FT %s: %s", item.get("id"), exc)
            return None
