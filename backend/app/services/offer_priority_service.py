"""
OfferPriorityService — Sprint 10 (corrigé).

Calcule le priority_score composite pour chaque offre active.

  priority_score = 0.6 × ranking_score
                 + 0.4 × matching_score

Justification de la formule :
  - ranking_score (0-100) est déjà un score composite qui intègre la fraîcheur
    (25 pts), la pertinence du titre (25 pts), la localisation (25 pts) et la
    fiabilité de la source (25 pts). Ajouter un terme freshness séparé revenait
    à double-compter la fraîcheur (~30 % de poids effectif au lieu de 20 %).
  - matching_score (0-100) est personalized_score si disponible, sinon
    global_score. Il capture la correspondance avec le profil du candidat.
  - Le ratio 60/40 donne légèrement plus de poids à la qualité intrinsèque de
    l'offre (ranking) tout en garantissant que la pertinence personnelle compte.

Résultat : liste triée par priority_score décroissant, limitée à `limit` éléments.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.infrastructure.db.models.offer import Offer
from app.infrastructure.db.models.offer_llm_analysis import OfferLLMAnalysis  # noqa: F401 – eager-load


class OfferPriorityService:
    """
    Classe de calcul et de tri des offres par priority_score.

    priority_score = 0.6 × ranking_score + 0.4 × matching_score
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_prioritized(self, limit: int = 10) -> list[dict]:
        """
        Retourne les `limit` offres actives triées par priority_score décroissant.

        Chaque élément est un dict avec les clés :
          offer          — objet Offer (company, primary_source et llm_analysis chargés)
          priority_score — score composite (float, 0-100)
          ranking_score  — composante ranking (float)
          matching_score — composante matching (float)
        """
        offers = self.db.execute(
            select(Offer)
            .where(Offer.is_active == True)  # noqa: E712
            .options(
                joinedload(Offer.company),
                joinedload(Offer.primary_source),
                joinedload(Offer.llm_analysis),  # évite le N+1 dans SkillGapService
            )
        ).scalars().all()

        scored: list[dict] = []
        for offer in offers:
            ranking = float(offer.ranking_score or 0.0)
            matching = float(
                offer.personalized_score
                if offer.personalized_score is not None
                else (offer.global_score or 0.0)
            )
            p_score = round(0.6 * ranking + 0.4 * matching, 2)
            scored.append({
                "offer": offer,
                "priority_score": p_score,
                "ranking_score": ranking,
                "matching_score": matching,
            })

        scored.sort(key=lambda x: x["priority_score"], reverse=True)
        return scored[:limit]
