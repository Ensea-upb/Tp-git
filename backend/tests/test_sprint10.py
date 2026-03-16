"""
Tests Sprint 10 — Moteur de stratégie de candidature.

Couvre :
- ApplicationStrategyService : PREPARE_INTERVIEW, SEND_FOLLOWUP, ARCHIVE_STALE, APPLY_NOW
- Détection stale (dernier événement > 21 jours)
- OfferPriorityService : calcul et tri du priority_score
- SkillGapService : extraction des compétences manquantes
- GET /v1/strategy/recommendations : structure de la réponse
- GET /v1/offers/prioritized : structure de la réponse
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.domain.enums.application_status import ApplicationStatus
from app.domain.enums.offer_state import OfferState
from app.domain.enums.strategy_action_type import StrategyActionType
from app.infrastructure.db.models.application import Application
from app.infrastructure.db.models.application_event import ApplicationEvent
from app.infrastructure.db.models.company import Company
from app.infrastructure.db.models.offer import Offer
from app.infrastructure.db.models.source import Source


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_source(db, source_type: str = "wttj") -> Source:
    s = Source(
        id=uuid.uuid4(), name=f"Src-{uuid.uuid4().hex[:6]}",
        source_type=source_type, is_active=True, check_frequency_hours=3,
    )
    db.add(s)
    db.flush()
    return s


def _make_offer(db, ranking_score: float | None = None, is_active: bool = True) -> Offer:
    source = _make_source(db)
    company = Company(id=uuid.uuid4(), name=f"Co-{uuid.uuid4().hex[:6]}")
    db.add(company)
    db.flush()
    offer = Offer(
        id=uuid.uuid4(),
        normalized_title="Data Engineer",
        current_state=OfferState.NORMALIZED,
        is_active=is_active,
        primary_source_id=source.id,
        company_id=company.id,
        offer_url=f"https://test.example.com/{uuid.uuid4()}",
        ranking_score=ranking_score,
        tags=["python", "sql"],
    )
    db.add(offer)
    db.flush()
    return offer


def _make_application(
    db,
    status: ApplicationStatus = ApplicationStatus.DRAFT,
    offer: Offer | None = None,
) -> Application:
    if offer is None:
        offer = _make_offer(db)
    app = Application(
        id=uuid.uuid4(), offer_id=offer.id, status=status, drafts_ready=False,
    )
    db.add(app)
    db.flush()
    return app


def _emit_event(db, application_id: uuid.UUID, days_ago: int = 0) -> ApplicationEvent:
    """Crée un événement avec un created_at artificiellement vieux."""
    event = ApplicationEvent(
        application_id=application_id,
        event_type="STATUS_CHANGED",
        payload_json={},
        created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
    )
    db.add(event)
    db.flush()
    return event


# ── PARTIE 1 : ApplicationStrategyService ────────────────────────────────────


class TestApplicationStrategyService:
    def test_no_actions_when_empty(self, db):
        """Aucune action si base vide."""
        from sqlalchemy import delete
        db.execute(delete(Application))
        db.flush()

        from app.services.application_strategy_service import ApplicationStrategyService
        svc = ApplicationStrategyService(db)
        actions = svc.recommend_actions()
        # Peut contenir des APPLY_NOW si des offres existent — on filtre
        stale = [a for a in actions if a.action_type == StrategyActionType.ARCHIVE_STALE]
        interview = [a for a in actions if a.action_type == StrategyActionType.PREPARE_INTERVIEW]
        followup = [a for a in actions if a.action_type == StrategyActionType.SEND_FOLLOWUP]
        assert stale == []
        assert interview == []
        assert followup == []

    def test_prepare_interview_action(self, db):
        """Une candidature en INTERVIEW génère PREPARE_INTERVIEW (priorité 3)."""
        from app.services.application_strategy_service import ApplicationStrategyService

        app = _make_application(db, status=ApplicationStatus.INTERVIEW)
        db.commit()

        svc = ApplicationStrategyService(db)
        actions = svc.recommend_actions()

        interview_actions = [a for a in actions if a.action_type == StrategyActionType.PREPARE_INTERVIEW]
        assert len(interview_actions) >= 1
        target = next(a for a in interview_actions if a.application_id == app.id)
        assert target.priority == 3

    def test_send_followup_action(self, db):
        """Une candidature en FOLLOW_UP_DUE génère SEND_FOLLOWUP (priorité 2)."""
        from app.services.application_strategy_service import ApplicationStrategyService

        app = _make_application(db, status=ApplicationStatus.FOLLOW_UP_DUE)
        db.commit()

        svc = ApplicationStrategyService(db)
        actions = svc.recommend_actions()

        followup_actions = [a for a in actions if a.action_type == StrategyActionType.SEND_FOLLOWUP]
        assert any(a.application_id == app.id for a in followup_actions)
        target = next(a for a in followup_actions if a.application_id == app.id)
        assert target.priority == 2

    def test_apply_now_action(self, db):
        """Une offre haute priorité sans candidature génère APPLY_NOW (priorité 3)."""
        from app.services.application_strategy_service import ApplicationStrategyService
        from sqlalchemy import delete

        db.execute(delete(Application))
        db.flush()

        offer = _make_offer(db, ranking_score=85.0)
        db.commit()

        svc = ApplicationStrategyService(db)
        actions = svc.recommend_actions()

        apply_now = [a for a in actions if a.action_type == StrategyActionType.APPLY_NOW]
        assert any(a.offer_id == offer.id for a in apply_now)
        target = next(a for a in apply_now if a.offer_id == offer.id)
        assert target.priority == 3

    def test_apply_now_not_generated_if_active_application_exists(self, db):
        """APPLY_NOW n'est pas généré si une candidature active (SENT) existe pour l'offre."""
        from app.services.application_strategy_service import ApplicationStrategyService

        offer = _make_offer(db, ranking_score=90.0)
        _make_application(db, status=ApplicationStatus.SENT, offer=offer)
        db.commit()

        svc = ApplicationStrategyService(db)
        actions = svc.recommend_actions()

        apply_now = [a for a in actions if a.action_type == StrategyActionType.APPLY_NOW]
        assert not any(a.offer_id == offer.id for a in apply_now)

    def test_apply_now_generated_after_rejection(self, db):
        """
        APPLY_NOW est généré pour une offre dont la seule candidature est REJECTED.
        Une candidature rejetée est un statut terminal — l'offre peut être repostée
        et mérite d'être re-signalée comme opportunité.
        """
        from app.services.application_strategy_service import ApplicationStrategyService

        offer = _make_offer(db, ranking_score=80.0)
        _make_application(db, status=ApplicationStatus.REJECTED, offer=offer)
        db.commit()

        svc = ApplicationStrategyService(db)
        actions = svc.recommend_actions()

        apply_now = [a for a in actions if a.action_type == StrategyActionType.APPLY_NOW]
        assert any(a.offer_id == offer.id for a in apply_now)

    def test_apply_now_generated_after_archived(self, db):
        """APPLY_NOW est généré si la seule candidature est ARCHIVED (statut terminal)."""
        from app.services.application_strategy_service import ApplicationStrategyService

        offer = _make_offer(db, ranking_score=80.0)
        _make_application(db, status=ApplicationStatus.ARCHIVED, offer=offer)
        db.commit()

        svc = ApplicationStrategyService(db)
        actions = svc.recommend_actions()

        apply_now = [a for a in actions if a.action_type == StrategyActionType.APPLY_NOW]
        assert any(a.offer_id == offer.id for a in apply_now)

    def test_apply_now_not_generated_for_low_score(self, db):
        """APPLY_NOW requiert ranking_score ≥ 70."""
        from app.services.application_strategy_service import ApplicationStrategyService
        from sqlalchemy import delete

        db.execute(delete(Application))
        db.flush()

        offer = _make_offer(db, ranking_score=50.0)
        db.commit()

        svc = ApplicationStrategyService(db)
        actions = svc.recommend_actions()

        apply_now = [a for a in actions if a.action_type == StrategyActionType.APPLY_NOW]
        assert not any(a.offer_id == offer.id for a in apply_now)

    def test_actions_sorted_by_priority_desc(self, db):
        """Les actions sont triées par priorité décroissante."""
        from app.services.application_strategy_service import ApplicationStrategyService

        _make_application(db, status=ApplicationStatus.INTERVIEW)
        _make_application(db, status=ApplicationStatus.FOLLOW_UP_DUE)
        db.commit()

        svc = ApplicationStrategyService(db)
        actions = svc.recommend_actions()

        priorities = [a.priority for a in actions]
        assert priorities == sorted(priorities, reverse=True)


# ── PARTIE 2 : Détection STALE ────────────────────────────────────────────────


class TestStaleDetection:
    def test_stale_application_detected(self, db):
        """Application SENT avec dernier événement > 21 jours → ARCHIVE_STALE."""
        from app.services.application_strategy_service import ApplicationStrategyService

        app = _make_application(db, status=ApplicationStatus.SENT)
        _emit_event(db, app.id, days_ago=25)
        db.commit()

        svc = ApplicationStrategyService(db)
        actions = svc.recommend_actions()

        stale = [a for a in actions if a.action_type == StrategyActionType.ARCHIVE_STALE]
        assert any(a.application_id == app.id for a in stale)
        target = next(a for a in stale if a.application_id == app.id)
        assert target.priority == 1

    def test_recent_application_not_stale(self, db):
        """Application SENT avec événement récent (5 jours) → pas ARCHIVE_STALE."""
        from app.services.application_strategy_service import ApplicationStrategyService

        app = _make_application(db, status=ApplicationStatus.SENT)
        _emit_event(db, app.id, days_ago=5)
        db.commit()

        svc = ApplicationStrategyService(db)
        actions = svc.recommend_actions()

        stale = [a for a in actions if a.action_type == StrategyActionType.ARCHIVE_STALE]
        assert not any(a.application_id == app.id for a in stale)

    def test_sent_application_no_events_is_stale(self, db):
        """Application SENT sans aucun événement → ARCHIVE_STALE."""
        from app.services.application_strategy_service import ApplicationStrategyService

        app = _make_application(db, status=ApplicationStatus.SENT)
        # Pas d'événement créé
        db.commit()

        svc = ApplicationStrategyService(db)
        actions = svc.recommend_actions()

        stale = [a for a in actions if a.action_type == StrategyActionType.ARCHIVE_STALE]
        assert any(a.application_id == app.id for a in stale)


# ── PARTIE 3 : OfferPriorityService ──────────────────────────────────────────


class TestOfferPriorityService:
    def test_returns_list(self, db):
        """get_prioritized retourne une liste."""
        from app.services.offer_priority_service import OfferPriorityService

        result = OfferPriorityService(db).get_prioritized(limit=5)
        assert isinstance(result, list)

    def test_priority_score_formula(self, db):
        """
        priority_score = 0.6 × ranking_score + 0.4 × matching_score
        Vérifié pour une offre avec ranking_score=80, personalized_score=60.
        Résultat attendu : 0.6 × 80 + 0.4 × 60 = 72.0
        """
        from app.services.offer_priority_service import OfferPriorityService

        offer = _make_offer(db, ranking_score=80.0)
        offer.personalized_score = 60.0
        db.flush()
        db.commit()

        result = OfferPriorityService(db).get_prioritized(limit=50)
        entry = next((r for r in result if r["offer"].id == offer.id), None)
        assert entry is not None

        expected_score = round(0.6 * 80 + 0.4 * 60, 2)  # 72.0
        assert abs(entry["priority_score"] - expected_score) < 0.01

    def test_sorted_by_priority_desc(self, db):
        """Les résultats sont triés par priority_score décroissant."""
        from app.services.offer_priority_service import OfferPriorityService

        _make_offer(db, ranking_score=30.0)
        _make_offer(db, ranking_score=90.0)
        _make_offer(db, ranking_score=60.0)
        db.commit()

        result = OfferPriorityService(db).get_prioritized(limit=50)
        scores = [r["priority_score"] for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_inactive_offers_excluded(self, db):
        """Les offres inactives (is_active=False) ne sont pas incluses."""
        from app.services.offer_priority_service import OfferPriorityService

        inactive = _make_offer(db, ranking_score=95.0, is_active=False)
        db.commit()

        result = OfferPriorityService(db).get_prioritized(limit=50)
        ids = [r["offer"].id for r in result]
        assert inactive.id not in ids

    def test_limit_respected(self, db):
        """Le paramètre limit est respecté."""
        from app.services.offer_priority_service import OfferPriorityService

        for _ in range(5):
            _make_offer(db, ranking_score=75.0)
        db.commit()

        result = OfferPriorityService(db).get_prioritized(limit=3)
        assert len(result) <= 3


# ── PARTIE 4 : SkillGapService ───────────────────────────────────────────────


class TestSkillGapService:
    def test_no_gap_when_no_profile(self, db):
        """Sans profil candidat, aucune compétence manquante."""
        from app.services.skill_gap_service import SkillGapService

        offer = _make_offer(db)
        offer.tags = ["python", "spark"]
        db.flush()

        svc = SkillGapService(db)
        missing = svc.analyze_for_offer(offer)
        assert missing == []

    def test_missing_skills_detected(self, db):
        """Les compétences requises absentes du profil sont détectées."""
        from app.services.skill_gap_service import SkillGapService
        from app.infrastructure.db.models.candidate_profile import CandidateProfile, DEFAULT_CANDIDATE_ID

        profile = CandidateProfile(
            id=DEFAULT_CANDIDATE_ID,
            skills=["python", "git"],
            tech_stack=["fastapi"],
        )
        db.add(profile)
        db.flush()

        offer = _make_offer(db)
        offer.tags = ["python", "spark", "sql"]
        db.flush()

        svc = SkillGapService(db)
        missing = svc.analyze_for_offer(offer)
        assert "spark" in missing
        assert "sql" in missing
        assert "python" not in missing

    def test_no_gap_when_all_skills_covered(self, db):
        """Pas de gap si le profil couvre toutes les compétences requises."""
        from app.services.skill_gap_service import SkillGapService
        from app.infrastructure.db.models.candidate_profile import CandidateProfile, DEFAULT_CANDIDATE_ID

        profile = CandidateProfile(
            id=DEFAULT_CANDIDATE_ID,
            skills=["python", "sql"],
            tech_stack=["spark"],
        )
        db.add(profile)
        db.flush()

        offer = _make_offer(db)
        offer.tags = ["Python", "SQL", "Spark"]  # casse différente
        db.flush()

        svc = SkillGapService(db)
        missing = svc.analyze_for_offer(offer)
        assert missing == []

    def test_analyze_for_offers_filters_empty_gaps(self, db):
        """analyze_for_offers n'inclut que les offres avec des compétences manquantes."""
        from app.services.skill_gap_service import SkillGapService
        from app.infrastructure.db.models.candidate_profile import CandidateProfile, DEFAULT_CANDIDATE_ID

        profile = CandidateProfile(
            id=DEFAULT_CANDIDATE_ID,
            skills=["python"],
            tech_stack=[],
        )
        db.add(profile)
        db.flush()

        offer_no_gap = _make_offer(db)
        offer_no_gap.tags = ["python"]
        offer_with_gap = _make_offer(db)
        offer_with_gap.tags = ["python", "kafka"]
        db.flush()

        svc = SkillGapService(db)
        results = svc.analyze_for_offers([offer_no_gap, offer_with_gap])
        assert len(results) == 1
        assert results[0]["offer_id"] == offer_with_gap.id
        assert "kafka" in results[0]["missing_skills"]

    def test_missing_skills_sorted(self, db):
        """Les compétences manquantes sont retournées triées alphabétiquement."""
        from app.services.skill_gap_service import SkillGapService
        from app.infrastructure.db.models.candidate_profile import CandidateProfile, DEFAULT_CANDIDATE_ID

        # Profil avec au moins une compétence pour que la garde ne bloque pas
        profile = CandidateProfile(id=DEFAULT_CANDIDATE_ID, skills=["git"], tech_stack=[])
        db.add(profile)
        db.flush()

        offer = _make_offer(db)
        offer.tags = ["spark", "airflow", "python", "kafka"]
        db.flush()

        svc = SkillGapService(db)
        missing = svc.analyze_for_offer(offer)
        assert len(missing) > 0
        assert missing == sorted(missing)

    def test_no_gaps_when_profile_empty(self, db):
        """
        Garde profil vide : si le profil ne déclare aucune compétence,
        analyze_for_offer et analyze_for_offers retournent [] sans bruit.

        Sans cette garde, toutes les compétences requises apparaîtraient comme
        manquantes, produisant un signal inexploitable.
        """
        from app.services.skill_gap_service import SkillGapService
        from app.infrastructure.db.models.candidate_profile import CandidateProfile, DEFAULT_CANDIDATE_ID

        # Profil existant mais sans compétences déclarées
        profile = CandidateProfile(id=DEFAULT_CANDIDATE_ID, skills=None, tech_stack=None)
        db.add(profile)
        db.flush()

        offer = _make_offer(db)
        offer.tags = ["python", "spark", "kafka"]
        db.flush()

        svc = SkillGapService(db)
        assert svc.analyze_for_offer(offer) == []

    def test_no_gaps_when_profile_has_empty_lists(self, db):
        """
        Garde profil vide : skills=[] et tech_stack=[] → même comportement que None.
        """
        from app.services.skill_gap_service import SkillGapService
        from app.infrastructure.db.models.candidate_profile import CandidateProfile, DEFAULT_CANDIDATE_ID

        profile = CandidateProfile(id=DEFAULT_CANDIDATE_ID, skills=[], tech_stack=[])
        db.add(profile)
        db.flush()

        offer = _make_offer(db)
        offer.tags = ["python", "spark"]
        db.flush()

        svc = SkillGapService(db)
        assert svc.analyze_for_offer(offer) == []
        assert svc.analyze_for_offers([offer]) == []


# ── PARTIE 5 : API Strategy ───────────────────────────────────────────────────


class TestStrategyApi:
    def test_get_recommendations_structure(self, client, api_headers):
        """GET /strategy/recommendations retourne la structure attendue."""
        resp = client.get("/v1/strategy/recommendations", headers=api_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "actions" in data
        assert "prioritized_offers" in data
        assert "skill_gaps" in data
        assert isinstance(data["actions"], list)
        assert isinstance(data["prioritized_offers"], list)
        assert isinstance(data["skill_gaps"], list)

    def test_get_recommendations_action_fields(self, client, api_headers, db):
        """Chaque action a les champs requis."""
        _make_application(db, status=ApplicationStatus.INTERVIEW)
        db.commit()

        resp = client.get("/v1/strategy/recommendations", headers=api_headers)
        assert resp.status_code == 200
        data = resp.json()

        interview_actions = [
            a for a in data["actions"] if a["action_type"] == "PREPARE_INTERVIEW"
        ]
        assert len(interview_actions) >= 1
        action = interview_actions[0]
        assert "action_type" in action
        assert "reason" in action
        assert "priority" in action

    def test_get_recommendations_prioritized_offer_fields(self, client, api_headers, db):
        """Chaque offre priorisée a les champs requis."""
        _make_offer(db, ranking_score=75.0)
        db.commit()

        resp = client.get("/v1/strategy/recommendations", headers=api_headers)
        assert resp.status_code == 200
        data = resp.json()

        if data["prioritized_offers"]:
            offer = data["prioritized_offers"][0]
            assert "offer_id" in offer
            assert "title" in offer
            assert "priority_score" in offer
            assert "ranking_score" in offer
            assert "matching_score" in offer

    def test_get_recommendations_limit_param(self, client, api_headers):
        """Le paramètre limit est respecté (≤ limit offres retournées)."""
        resp = client.get("/v1/strategy/recommendations?limit=3", headers=api_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["prioritized_offers"]) <= 3

    def test_get_recommendations_invalid_limit(self, client, api_headers):
        """limit=0 → 422 (validation FastAPI)."""
        resp = client.get("/v1/strategy/recommendations?limit=0", headers=api_headers)
        assert resp.status_code == 422

    def test_get_prioritized_offers(self, client, api_headers, db):
        """GET /offers/prioritized retourne une liste avec les bons champs."""
        _make_offer(db, ranking_score=80.0)
        db.commit()

        resp = client.get("/v1/offers/prioritized?limit=5", headers=api_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            offer = data[0]
            assert "offer_id" in offer
            assert "title" in offer
            assert "priority_score" in offer

    def test_strategy_stale_appears_in_recommendations(self, client, api_headers, db):
        """Une application stale apparaît dans les actions de stratégie."""
        app = _make_application(db, status=ApplicationStatus.SENT)
        _emit_event(db, app.id, days_ago=30)
        db.commit()

        resp = client.get("/v1/strategy/recommendations", headers=api_headers)
        assert resp.status_code == 200
        data = resp.json()

        stale_actions = [a for a in data["actions"] if a["action_type"] == "ARCHIVE_STALE"]
        assert any(a.get("application_id") == str(app.id) for a in stale_actions)
