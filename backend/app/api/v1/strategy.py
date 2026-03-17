"""
GET /v1/strategy/recommendations — Moteur de stratégie de candidature.

Retourne en une seule réponse :
  actions            — recommandations d'action (APPLY_NOW, SEND_FOLLOWUP, …)
  prioritized_offers — offres actives triées par priority_score composite
  skill_gaps         — compétences manquantes sur les offres priorisées
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import verify_api_key
from app.api.schemas.strategy import (
    PrioritizedOfferOut,
    SkillGapOut,
    StrategyActionOut,
    StrategyRecommendationsOut,
)
from app.infrastructure.db.session import get_db
from app.services.application_strategy_service import ApplicationStrategyService
from app.services.offer_priority_service import OfferPriorityService
from app.services.skill_gap_service import SkillGapService

router = APIRouter(
    prefix="/strategy",
    tags=["strategy"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("/recommendations", response_model=StrategyRecommendationsOut)
def get_strategy_recommendations(
    limit: int = Query(default=10, ge=1, le=50, description="Nombre d'offres priorisées à retourner"),
    db: Session = Depends(get_db),
) -> StrategyRecommendationsOut:
    """
    Retourne les recommandations stratégiques du jour.

    - **actions** : liste d'actions recommandées triées par priorité décroissante
    - **prioritized_offers** : top offres actives selon priority_score composite
      (0.6 × ranking_score + 0.4 × matching_score)
    - **skill_gaps** : compétences manquantes sur les 5 premières offres priorisées
    """
    # ── Actions recommandées ──────────────────────────────────────────
    strategy_svc = ApplicationStrategyService(db)
    actions = [
        StrategyActionOut(
            action_type=a.action_type,
            reason=a.reason,
            priority=a.priority,
            application_id=a.application_id,
            offer_id=a.offer_id,
        )
        for a in strategy_svc.recommend_actions()
    ]

    # ── Offres priorisées ─────────────────────────────────────────────
    priority_svc = OfferPriorityService(db)
    top_offers = priority_svc.get_prioritized(limit=limit)
    prioritized_offers = [
        PrioritizedOfferOut(
            offer_id=item["offer"].id,
            title=item["offer"].normalized_title,
            priority_score=item["priority_score"],
            ranking_score=item["ranking_score"],
            matching_score=item["matching_score"],
            location_text=item["offer"].location_text,
            company_name=item["offer"].company.name if item["offer"].company else None,
        )
        for item in top_offers
    ]

    # ── Skill gaps (top 5 offres priorisées) ─────────────────────────
    gap_svc = SkillGapService(db)
    top_5_offers = [item["offer"] for item in top_offers[:5]]
    raw_gaps = gap_svc.analyze_for_offers(top_5_offers)
    skill_gaps = [
        SkillGapOut(
            offer_id=g["offer_id"],
            offer_title=g["offer_title"],
            missing_skills=g["missing_skills"],
        )
        for g in raw_gaps
    ]

    return StrategyRecommendationsOut(
        actions=actions,
        prioritized_offers=prioritized_offers,
        skill_gaps=skill_gaps,
    )
