"""
OfferRankingService — Score de pertinence composite pour les offres.

Score final 0-100, composé de 4 dimensions équipondérées (25 pts chacune) :
  - freshness          : fraîcheur de publication
  - title_relevance    : correspondance avec mots-clés cibles (data, ml, …)
  - location_relevance : proximité géographique / mode de travail
  - source_reliability : fiabilité historique de la source

Usage :
  service = OfferRankingService(db)
  service.score_offer(offer)    → float (0-100), persiste en base
  service.score_all()           → int (nombre d'offres traitées)
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.db.models.offer import Offer

logger = logging.getLogger(__name__)

# ── Mots-clés cibles pour la pertinence du titre ─────────────────────────────
_TITLE_KEYWORDS: list[str] = [
    "data", "ml", "machine learning", "deep learning",
    "ai", "artificial intelligence",
    "analytics", "analyse", "analyst",
    "engineer", "ingenieur", "ingénieur",
    "scientist", "science",
    "python", "spark", "sql",
    "econometr", "statistique", "statistician",
    "nlp", "llm", "computer vision",
]

# ── Villes / régions bien notées ──────────────────────────────────────────────
_TOP_CITIES: frozenset[str] = frozenset(
    {"paris", "ile-de-france", "ile de france", "idf", "remote", "teletravail", "télétravail"}
)
_GOOD_CITIES: frozenset[str] = frozenset(
    {"lyon", "bordeaux", "toulouse", "nantes", "lille", "marseille", "grenoble", "sophia"}
)

# ── Fiabilité des sources ─────────────────────────────────────────────────────
_SOURCE_SCORES: dict[str, float] = {
    "wttj": 25.0,
    "welcome_to_the_jungle": 25.0,
    "apec": 22.0,
    "indeed": 18.0,
    "linkedin": 25.0,
}
_SOURCE_SCORE_DEFAULT = 12.0


class OfferRankingService:
    """
    Calcule et persiste ranking_score sur les offres.

    Chaque composante est normalisée sur 25 points.
    Le score final est la somme, écrêtée entre 0 et 100.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Interface publique ─────────────────────────────────────────────

    def score_offer(self, offer: Offer) -> float:
        """Calcule ranking_score, le persiste et retourne la valeur."""
        score = self._compute(offer)
        offer.ranking_score = round(score, 2)
        self.db.flush()
        return score

    def score_all(self, active_only: bool = True) -> int:
        """Re-score toutes les offres. Retourne le nombre d'offres traitées."""
        query = select(Offer)
        if active_only:
            query = query.where(Offer.is_active == True)  # noqa: E712
        offers = list(self.db.execute(query).scalars().all())
        for offer in offers:
            score = self._compute(offer)
            offer.ranking_score = round(score, 2)
        self.db.commit()
        logger.info("OfferRankingService: %d offres re-scorées", len(offers))
        return len(offers)

    # ── Calcul du score ────────────────────────────────────────────────

    def _compute(self, offer: Offer) -> float:
        freshness = self._freshness_score(offer)
        title_rel = self._title_relevance_score(offer)
        location_rel = self._location_score(offer)
        source_rel = self._source_score(offer)
        total = freshness + title_rel + location_rel + source_rel
        return max(0.0, min(100.0, total))

    def _freshness_score(self, offer: Offer) -> float:
        """
        25 pts si publiée < 7 jours, dégression linéaire jusqu'à 0 à 90 jours.
        Offres sans date de publication : 10 pts (pénalité légère).
        """
        if offer.published_at is None:
            return 10.0
        now = datetime.now(timezone.utc)
        published = offer.published_at
        # Normaliser en UTC si naïve
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        age_days = (now - published).days
        if age_days < 0:
            return 25.0
        if age_days <= 7:
            return 25.0
        if age_days <= 30:
            # 25 → 15 linéairement sur 7..30 jours
            return 25.0 - (age_days - 7) * (10.0 / 23.0)
        if age_days <= 90:
            # 15 → 0 linéairement sur 30..90 jours
            return 15.0 - (age_days - 30) * (15.0 / 60.0)
        return 0.0

    def _title_relevance_score(self, offer: Offer) -> float:
        """
        25 pts si le titre contient ≥ 3 mots-clés cibles,
        proportionnel au nombre de mots-clés détectés (min 0).
        """
        if not offer.normalized_title:
            return 0.0
        title_lower = offer.normalized_title.lower()
        matches = sum(1 for kw in _TITLE_KEYWORDS if kw in title_lower)
        # 25 pts pour 3+ mots-clés, prorata sinon
        return min(25.0, matches * (25.0 / 3.0))

    def _location_score(self, offer: Offer) -> float:
        """
        25 pts pour les villes/modes top, 15 pts pour les villes secondaires,
        5 pts par défaut, 20 pts si remote.
        """
        if offer.work_mode and str(offer.work_mode).upper() == "REMOTE":
            return 20.0

        location = (offer.location_text or "").lower()
        for city in _TOP_CITIES:
            if city in location:
                return 25.0
        for city in _GOOD_CITIES:
            if city in location:
                return 15.0

        if offer.work_mode and str(offer.work_mode).upper() == "HYBRID":
            return 12.0

        return 5.0

    def _source_score(self, offer: Offer) -> float:
        """
        Score de fiabilité selon la source. Voir _SOURCE_SCORES.
        Défaut : 12 pts pour les sources inconnues.
        """
        if offer.primary_source is None:
            return _SOURCE_SCORE_DEFAULT
        source_type = (offer.primary_source.source_type or "").lower()
        return _SOURCE_SCORES.get(source_type, _SOURCE_SCORE_DEFAULT)
