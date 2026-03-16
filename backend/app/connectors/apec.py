"""
Connecteur APEC.

Source type : "apec"
API REST publique : https://www.apec.fr/cms/webservices/offre/filtres/metiers
Recherche :         https://www.apec.fr/cms/webservices/offre/resultat
Détail offre :      https://www.apec.fr/cms/webservices/offre/detail/{numeroOffre}

L'API APEC est semi-publique (pas de token, mais requiert des en-têtes navigateur).
Les résultats contiennent titrePoste, nomEntreprise, lieuTravail, texteHtml.
"""

import time

import httpx

from app.connectors.base import BaseConnector
from app.domain.dto.raw_offer_payload import RawOfferPayload
from app.infrastructure.db.models.source import Source

_SEARCH_URL = "https://www.apec.fr/cms/webservices/offre/resultat"
_DETAIL_URL = "https://www.apec.fr/cms/webservices/offre/detail/{}"
_PAGE_SIZE = 20
_RATE_LIMIT_PAUSE = 1.0

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.apec.fr/candidat/recherche-emploi.html/emploi",
    "Origin": "https://www.apec.fr",
}


class ApecConnector(BaseConnector):
    """
    Connecteur APEC (Association Pour l'Emploi des Cadres).
    Configure la source avec metadata_json contenant :
      - keywords  : mots-clés (ex: "data analyst stage")
      - lieu      : code région APEC (ex: "101" pour Île-de-France)
      - typeContrat : identifiant contrat APEC (ex: "133" pour stage)
    """

    source_type = "apec"

    def is_available(self) -> bool:
        return True

    def fetch(self) -> list[RawOfferPayload]:
        meta = getattr(self.source, "metadata_json", None) or {}
        payload_base: dict = {
            "nombreOffresParPage": _PAGE_SIZE,
            "typesTri": [{"direction": "DESC", "type": "DATE"}],
        }
        if keywords := meta.get("keywords"):
            payload_base["motsCles"] = keywords
        if lieu := meta.get("lieu"):
            payload_base["lieux"] = [lieu]
        if type_contrat := meta.get("typeContrat"):
            payload_base["typesContrat"] = [type_contrat]

        results: list[RawOfferPayload] = []
        page = 0

        while True:
            request_payload = {**payload_base, "page": page}
            try:
                resp = httpx.post(
                    _SEARCH_URL,
                    json=request_payload,
                    headers=_HEADERS,
                    timeout=20,
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                self.logger.error("APEC fetch error (page %d): %s", page, exc)
                break

            offres = data.get("resultats", [])
            if not offres:
                break

            for offre in offres:
                payload = self._parse_offre(offre)
                if payload:
                    results.append(payload)

            total = data.get("nombreTotal", 0)
            fetched = (page + 1) * _PAGE_SIZE
            self.logger.info(
                "APEC page %d — %d/%d offres", page, min(fetched, total), total
            )
            if fetched >= total:
                break
            page += 1
            time.sleep(_RATE_LIMIT_PAUSE)

        self.logger.info("APEC fetch terminé — %d offres", len(results))
        return results

    def _parse_offre(self, offre: dict) -> RawOfferPayload | None:
        try:
            numero = offre.get("numeroOffre", "")
            offer_url = f"https://www.apec.fr/candidat/recherche-emploi.html/emploi/{numero}" if numero else None

            lieu = offre.get("lieuTravail", {})
            location = lieu.get("libelle") if isinstance(lieu, dict) else str(lieu or "")

            description = offre.get("texteHtml") or offre.get("accroche") or ""
            # Retire les balises HTML basiques
            import re
            description = re.sub(r"<[^>]+>", " ", description).strip()

            return RawOfferPayload(
                source_name=self.source.name,
                source_type=self.source_type,
                external_offer_id=str(numero),
                offer_url=offer_url,
                raw_title=offre.get("intitule", ""),
                raw_content=description,
                raw_location=location,
                raw_company_name=offre.get("nomEntreprise", ""),
                metadata={
                    "typeContrat": offre.get("typeContrat", {}).get("libelle"),
                    "statut": offre.get("statut"),
                    "niveauEtudes": offre.get("niveauEtudes", {}).get("libelle") if isinstance(offre.get("niveauEtudes"), dict) else None,
                },
            )
        except Exception as exc:
            self.logger.warning("APEC parse error for %s: %s", offre.get("numeroOffre"), exc)
            return None
