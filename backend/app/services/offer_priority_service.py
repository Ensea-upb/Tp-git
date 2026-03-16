"""
OfferPriorityService — Sprint 10.

Calcule le priority_score composite pour chaque offre active :

  priority_score = 0.4 × ranking_score
                 + 0.4 × matching_score   (personalized_score, ou global_score si absent)
                 + 0.2 × freshness_score  (fraîcheur normalisée 0-100)

Retourne les offres triées par priority_score décroissant.
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.infrastructure.db.models.offer import Offer


def _freshness_score_100(offer: Offer) -> float:
    """
    Fraîcheur de l'offre normalisée sur 100 points.
    Même logique que OfferRankingService._freshness_score (0-25) multipliée par 4.
    """
    if offer.published_at is None:
        return 40.0  # pénalité légère : 10 pts × 4
    now = datetime.now(timezone.utc)
    published = offer.published_at
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    age_days = (now - published).days
    if age_days < 0:
        return 100.0
    if age_days <= 7:
        return 100.0
    if age_days <= 30:
        return (25.0 - (age_days - 7) * (10.0 / 23.0)) * 4.0
    if age_days <= 90:
        return (15.0 - (age_days - 30) * (15.0 / 60.0)) * 4.0
    return 0.0


class OfferPriorityService:
    """
    Classe de calcul et de tri des offres par priority_score.

    priority_score = 0.4 × ranking_score
                   + 0.4 × matching_score
                   + 0.2 × freshness_score
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_prioritized(self, limit: int = 10) -> list[dict]:
        """
        Retourne les `limit` offres actives triées par priority_score décroissant.

        Chaque élément du résultat est un dict avec les clés :
          offer          — objet Offer
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
            freshness = _freshness_score_100(offer)
            p_score = round(0.4 * ranking + 0.4 * matching + 0.2 * freshness, 2)
            scored.append({
                "offer": offer,
                "priority_score": p_score,
                "ranking_score": ranking,
                "matching_score": matching,
            })

        scored.sort(key=lambda x: x["priority_score"], reverse=True)
        return scored[:limit]
