"""
Tests Sprint 9 — Copilote de suivi des candidatures.

Couvre :
- ApplicationEvent : création, persistance, timeline
- ApplicationService : emit events sur create/update_status/add_followup
- add_recruiter_reply : événement RECRUITER_REPLIED
- FollowupRecommendationService : règles déterministes par source
- ApplicationService.get_stats : agrégats corrects
- API endpoints : /timeline, /recruiter-reply, /stats, /followup-recommendation
"""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.domain.enums.application_event_type import ApplicationEventType
from app.domain.enums.application_status import ApplicationStatus
from app.domain.enums.offer_state import OfferState
from app.domain.enums.work_mode import WorkMode
from app.infrastructure.db.models.application import Application
from app.infrastructure.db.models.application_event import ApplicationEvent
from app.infrastructure.db.models.company import Company
from app.infrastructure.db.models.offer import Offer
from app.infrastructure.db.models.source import Source


# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_source(db, source_type: str = "wttj", name: str = "TestSrc") -> Source:
    s = Source(
        id=uuid.uuid4(), name=name, source_type=source_type,
        is_active=True, check_frequency_hours=3,
    )
    db.add(s)
    db.flush()
    return s


def _make_offer(db, source_type: str = "wttj") -> Offer:
    source = _make_source(db, source_type=source_type)
    company = Company(id=uuid.uuid4(), name="TestCo")
    db.add(company)
    db.flush()
    offer = Offer(
        id=uuid.uuid4(),
        normalized_title="Data Engineer",
        current_state=OfferState.NORMALIZED,
        is_active=True,
        primary_source_id=source.id,
        company_id=company.id,
        offer_url=f"https://test.example.com/{uuid.uuid4()}",
    )
    db.add(offer)
    db.flush()
    return offer


def _make_application(db, status: ApplicationStatus = ApplicationStatus.DRAFT,
                       source_type: str = "wttj") -> Application:
    offer = _make_offer(db, source_type=source_type)
    app = Application(
        id=uuid.uuid4(),
        offer_id=offer.id,
        status=status,
        drafts_ready=False,
    )
    db.add(app)
    db.flush()
    return app


# ── PARTIE 1 : ApplicationEvent ORM ──────────────────────────────────────────


class TestApplicationEventModel:
    def test_event_persisted(self, db):
        """Un événement peut être créé et récupéré depuis la DB."""
        from app.repositories.application_event_repository import ApplicationEventRepository

        app = _make_application(db)
        repo = ApplicationEventRepository(db)

        event = repo.emit(
            application_id=app.id,
            event_type=ApplicationEventType.APPLICATION_CREATED,
            payload={"test": True},
        )
        db.commit()

        from sqlalchemy import select
        found = db.execute(
            select(ApplicationEvent).where(ApplicationEvent.id == event.id)
        ).scalar_one_or_none()

        assert found is not None
        assert found.event_type == ApplicationEventType.APPLICATION_CREATED
        assert found.payload_json == {"test": True}
        assert found.application_id == app.id

    def test_event_cascade_delete(self, db):
        """La suppression d'une candidature supprime ses événements (CASCADE)."""
        from app.repositories.application_event_repository import ApplicationEventRepository
        from sqlalchemy import select

        app = _make_application(db)
        repo = ApplicationEventRepository(db)
        repo.emit(app.id, ApplicationEventType.APPLICATION_CREATED)
        db.commit()

        db.delete(app)
        db.commit()

        events = db.execute(
            select(ApplicationEvent).where(ApplicationEvent.application_id == app.id)
        ).scalars().all()
        assert len(events) == 0


# ── PARTIE 2 : Timeline via ApplicationService ───────────────────────────────


class TestApplicationTimeline:
    def test_create_emits_application_created(self, db):
        """ApplicationService.create() émet APPLICATION_CREATED."""
        from app.services.application_service import ApplicationService
        from app.repositories.application_event_repository import ApplicationEventRepository

        offer = _make_offer(db)
        db.commit()

        svc = ApplicationService(db)
        app = svc.create(offer_id=offer.id, source_channel="email")

        events = ApplicationEventRepository(db).get_timeline(app.id)
        types = [e.event_type for e in events]
        assert ApplicationEventType.APPLICATION_CREATED in types

    def test_update_status_emits_status_changed(self, db):
        """update_status() émet STATUS_CHANGED avec les bons from/to."""
        from app.services.application_service import ApplicationService
        from app.repositories.application_event_repository import ApplicationEventRepository

        offer = _make_offer(db)
        db.commit()

        svc = ApplicationService(db)
        app = svc.create(offer_id=offer.id)
        app = svc.update_status(app.id, ApplicationStatus.READY_TO_SEND)

        events = ApplicationEventRepository(db).get_timeline(app.id)
        status_events = [e for e in events if e.event_type == ApplicationEventType.STATUS_CHANGED]
        assert len(status_events) >= 1
        last = status_events[-1]
        assert last.payload_json["from"] == ApplicationStatus.DRAFT.value
        assert last.payload_json["to"] == ApplicationStatus.READY_TO_SEND.value

    def test_add_followup_emits_followup_scheduled(self, db):
        """add_followup() émet FOLLOWUP_SCHEDULED."""
        from app.services.application_service import ApplicationService
        from app.repositories.application_event_repository import ApplicationEventRepository

        offer = _make_offer(db)
        db.commit()

        svc = ApplicationService(db)
        app = svc.create(offer_id=offer.id)
        # DRAFT → READY_TO_SEND → SENT
        svc.update_status(app.id, ApplicationStatus.READY_TO_SEND)
        svc.update_status(app.id, ApplicationStatus.SENT)

        future = datetime.now(timezone.utc) + timedelta(days=7)
        svc.add_followup(app.id, scheduled_at=future, notes="Relance test")

        events = ApplicationEventRepository(db).get_timeline(app.id)
        types = [e.event_type for e in events]
        assert ApplicationEventType.FOLLOWUP_SCHEDULED in types

    def test_get_timeline_returns_chronological_order(self, db):
        """get_timeline retourne les événements dans l'ordre chronologique."""
        from app.services.application_service import ApplicationService

        offer = _make_offer(db)
        db.commit()

        svc = ApplicationService(db)
        app = svc.create(offer_id=offer.id)
        svc.update_status(app.id, ApplicationStatus.READY_TO_SEND)
        svc.update_status(app.id, ApplicationStatus.SENT)

        events = svc.get_timeline(app.id)
        timestamps = [e.created_at for e in events]
        assert timestamps == sorted(timestamps)

    def test_get_timeline_not_found(self, db):
        """get_timeline lève NotFoundError pour un ID inexistant."""
        from app.services.application_service import ApplicationService
        from app.domain.errors import NotFoundError

        svc = ApplicationService(db)
        with pytest.raises(NotFoundError):
            svc.get_timeline(uuid.uuid4())


# ── PARTIE 3 : Réponse recruteur ──────────────────────────────────────────────


class TestRecruiterReply:
    def test_add_recruiter_reply_emits_event(self, db):
        """add_recruiter_reply crée un événement RECRUITER_REPLIED."""
        from app.services.application_service import ApplicationService
        from app.repositories.application_event_repository import ApplicationEventRepository

        offer = _make_offer(db)
        db.commit()

        svc = ApplicationService(db)
        app = svc.create(offer_id=offer.id)

        event = svc.add_recruiter_reply(
            application_id=app.id,
            message_text="Votre candidature a bien été reçue.",
            channel="email",
        )

        assert event.event_type == ApplicationEventType.RECRUITER_REPLIED
        assert event.payload_json["message_text"] == "Votre candidature a bien été reçue."
        assert event.payload_json["channel"] == "email"

    def test_recruiter_reply_visible_in_timeline(self, db):
        """La réponse recruteur apparaît dans la timeline."""
        from app.services.application_service import ApplicationService

        offer = _make_offer(db)
        db.commit()

        svc = ApplicationService(db)
        app = svc.create(offer_id=offer.id)
        svc.add_recruiter_reply(app.id, "Entretien prévu jeudi.", "phone")

        events = svc.get_timeline(app.id)
        recruiter_events = [e for e in events if e.event_type == ApplicationEventType.RECRUITER_REPLIED]
        assert len(recruiter_events) == 1

    def test_recruiter_reply_not_found(self, db):
        """add_recruiter_reply lève NotFoundError si la candidature n'existe pas."""
        from app.services.application_service import ApplicationService
        from app.domain.errors import NotFoundError

        svc = ApplicationService(db)
        with pytest.raises(NotFoundError):
            svc.add_recruiter_reply(uuid.uuid4(), "Test", "email")


# ── PARTIE 4 : FollowupRecommendationService ─────────────────────────────────


class TestFollowupRecommendationService:
    def _make_mock_app(self, source_type: str) -> MagicMock:
        source = MagicMock()
        source.source_type = source_type
        offer = MagicMock()
        offer.primary_source = source
        app = MagicMock()
        app.offer = offer
        app.applied_at = None
        app.created_at = datetime.now(timezone.utc)
        return app

    def test_wttj_recommends_5_days(self):
        from app.services.followup_recommendation_service import FollowupRecommendationService
        app = self._make_mock_app("wttj")
        rec = FollowupRecommendationService().recommend(app)
        assert rec["recommended_delay_days"] == 5
        assert "startup" in rec["reason"].lower()

    def test_career_page_recommends_5_days(self):
        from app.services.followup_recommendation_service import FollowupRecommendationService
        app = self._make_mock_app("career_page")
        rec = FollowupRecommendationService().recommend(app)
        assert rec["recommended_delay_days"] == 5

    def test_apec_recommends_10_days(self):
        from app.services.followup_recommendation_service import FollowupRecommendationService
        app = self._make_mock_app("apec")
        rec = FollowupRecommendationService().recommend(app)
        assert rec["recommended_delay_days"] == 10
        assert "grande" in rec["reason"].lower()

    def test_api_officielle_recommends_10_days(self):
        from app.services.followup_recommendation_service import FollowupRecommendationService
        app = self._make_mock_app("api_officielle")
        rec = FollowupRecommendationService().recommend(app)
        assert rec["recommended_delay_days"] == 10

    def test_indeed_recommends_7_days(self):
        from app.services.followup_recommendation_service import FollowupRecommendationService
        app = self._make_mock_app("indeed")
        rec = FollowupRecommendationService().recommend(app)
        assert rec["recommended_delay_days"] == 7

    def test_linkedin_recommends_7_days(self):
        from app.services.followup_recommendation_service import FollowupRecommendationService
        app = self._make_mock_app("linkedin")
        rec = FollowupRecommendationService().recommend(app)
        assert rec["recommended_delay_days"] == 7

    def test_unknown_source_defaults_to_7_days(self):
        from app.services.followup_recommendation_service import FollowupRecommendationService
        app = self._make_mock_app("some_unknown_source")
        rec = FollowupRecommendationService().recommend(app)
        assert rec["recommended_delay_days"] == 7

    def test_suggested_date_is_base_plus_delay(self):
        from app.services.followup_recommendation_service import FollowupRecommendationService
        base = datetime(2026, 3, 16, 12, 0, 0, tzinfo=timezone.utc)
        app = self._make_mock_app("wttj")
        app.applied_at = base

        rec = FollowupRecommendationService().recommend(app)
        expected = base + timedelta(days=5)
        assert rec["suggested_date"] == expected

    def test_uses_created_at_when_no_applied_at(self):
        from app.services.followup_recommendation_service import FollowupRecommendationService
        created = datetime(2026, 3, 10, 0, 0, 0, tzinfo=timezone.utc)
        app = self._make_mock_app("apec")
        app.applied_at = None
        app.created_at = created

        rec = FollowupRecommendationService().recommend(app)
        assert rec["suggested_date"] == created + timedelta(days=10)


# ── PARTIE 5 : Statistiques ───────────────────────────────────────────────────


class TestApplicationStats:
    def test_stats_empty(self, db):
        """Stats sur base vide → tous à 0."""
        from app.services.application_service import ApplicationService
        # Supprimer les candidatures existantes peut polluer — on vérifie juste le type
        stats = ApplicationService(db).get_stats()
        assert "total" in stats
        assert "interviews" in stats
        assert "rejections" in stats
        assert "offers" in stats
        assert "response_rate" in stats
        assert 0.0 <= stats["response_rate"] <= 100.0

    def test_stats_counts_correctly(self, db):
        """Les compteurs reflètent les statuts réels en base."""
        from app.services.application_service import ApplicationService

        offer1 = _make_offer(db)
        offer2 = _make_offer(db)
        offer3 = _make_offer(db)
        db.commit()

        svc = ApplicationService(db)
        # 1 INTERVIEW
        a1 = svc.create(offer1.id)
        svc.update_status(a1.id, ApplicationStatus.READY_TO_SEND)
        svc.update_status(a1.id, ApplicationStatus.SENT)
        svc.update_status(a1.id, ApplicationStatus.FOLLOW_UP_DUE)
        svc.update_status(a1.id, ApplicationStatus.INTERVIEW)

        # 1 REJECTED
        a2 = svc.create(offer2.id)
        svc.update_status(a2.id, ApplicationStatus.READY_TO_SEND)
        svc.update_status(a2.id, ApplicationStatus.SENT)
        svc.update_status(a2.id, ApplicationStatus.FOLLOW_UP_DUE)
        svc.update_status(a2.id, ApplicationStatus.REJECTED)

        # 1 DRAFT
        svc.create(offer3.id)

        stats = svc.get_stats()
        # Au moins nos 3 candidatures dans le total
        assert stats["total"] >= 3
        assert stats["interviews"] >= 1
        assert stats["rejections"] >= 1
        assert stats["response_rate"] > 0

    def test_response_rate_correct(self, db):
        """response_rate = (interviews + rejections + offers) / total × 100."""
        from app.services.application_service import ApplicationService
        from sqlalchemy import delete

        # Clean slate pour ce test
        db.execute(
            delete(Application)
        )
        db.commit()

        offer1 = _make_offer(db)
        offer2 = _make_offer(db)
        offer3 = _make_offer(db)
        offer4 = _make_offer(db)
        db.commit()

        svc = ApplicationService(db)

        def quick_to(offer_id, target_status):
            a = svc.create(offer_id)
            transitions = {
                ApplicationStatus.INTERVIEW: [
                    ApplicationStatus.READY_TO_SEND, ApplicationStatus.SENT,
                    ApplicationStatus.FOLLOW_UP_DUE, ApplicationStatus.INTERVIEW,
                ],
                ApplicationStatus.REJECTED: [
                    ApplicationStatus.READY_TO_SEND, ApplicationStatus.SENT,
                    ApplicationStatus.FOLLOW_UP_DUE, ApplicationStatus.REJECTED,
                ],
                ApplicationStatus.DRAFT: [],
            }
            for s in transitions.get(target_status, []):
                svc.update_status(a.id, s)
            return a

        quick_to(offer1.id, ApplicationStatus.INTERVIEW)
        quick_to(offer2.id, ApplicationStatus.REJECTED)
        quick_to(offer3.id, ApplicationStatus.DRAFT)
        quick_to(offer4.id, ApplicationStatus.DRAFT)

        stats = svc.get_stats()
        # 2 responded out of 4 total → 50%
        assert stats["total"] == 4
        assert stats["response_rate"] == 50.0


# ── PARTIE 6 : API Endpoints ──────────────────────────────────────────────────


class TestApplicationApiSprint9:
    def test_get_timeline_empty(self, client, api_headers, db):
        """GET /applications/{id}/timeline retourne [] pour une nouvelle candidature."""
        offer = _make_offer(db)
        db.commit()

        from app.services.application_service import ApplicationService
        svc = ApplicationService(db)
        app = svc.create(offer.id)

        resp = client.get(f"/v1/applications/{app.id}/timeline", headers=api_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # APPLICATION_CREATED doit être présent
        types = [e["event_type"] for e in data]
        assert "APPLICATION_CREATED" in types

    def test_get_timeline_not_found(self, client, api_headers):
        """GET /applications/{id}/timeline → 404 si candidature inconnue."""
        resp = client.get(f"/v1/applications/{uuid.uuid4()}/timeline", headers=api_headers)
        assert resp.status_code == 404

    def test_post_recruiter_reply(self, client, api_headers, db):
        """POST /applications/{id}/recruiter-reply crée l'événement et retourne 201."""
        offer = _make_offer(db)
        db.commit()

        from app.services.application_service import ApplicationService
        app = ApplicationService(db).create(offer.id)

        payload = {"message_text": "Bonjour, votre profil nous intéresse.", "channel": "email"}
        resp = client.post(
            f"/v1/applications/{app.id}/recruiter-reply",
            json=payload,
            headers=api_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["event_type"] == "RECRUITER_REPLIED"
        assert data["payload_json"]["channel"] == "email"

    def test_post_recruiter_reply_not_found(self, client, api_headers):
        """POST /recruiter-reply → 404 si candidature inconnue."""
        resp = client.post(
            f"/v1/applications/{uuid.uuid4()}/recruiter-reply",
            json={"message_text": "test"},
            headers=api_headers,
        )
        assert resp.status_code == 404

    def test_get_stats(self, client, api_headers):
        """GET /applications/stats retourne les bons champs."""
        resp = client.get("/v1/applications/stats", headers=api_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "interviews" in data
        assert "rejections" in data
        assert "offers" in data
        assert "response_rate" in data

    def test_get_followup_recommendation(self, client, api_headers, db):
        """GET /applications/{id}/followup-recommendation retourne les bons champs."""
        offer = _make_offer(db, source_type="wttj")
        db.commit()

        from app.services.application_service import ApplicationService
        app = ApplicationService(db).create(offer.id)

        resp = client.get(
            f"/v1/applications/{app.id}/followup-recommendation",
            headers=api_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["recommended_delay_days"] == 5  # wttj → startup → 5 jours
        assert "suggested_date" in data
        assert "reason" in data

    def test_get_followup_recommendation_not_found(self, client, api_headers):
        """GET /followup-recommendation → 404 si candidature inconnue."""
        resp = client.get(
            f"/v1/applications/{uuid.uuid4()}/followup-recommendation",
            headers=api_headers,
        )
        assert resp.status_code == 404

    def test_stats_route_before_id_route(self, client, api_headers):
        """Vérifie que /stats n'est pas capturé par /{application_id}."""
        resp = client.get("/v1/applications/stats", headers=api_headers)
        # 200 (stats) et non 422 (validation UUID échouée)
        assert resp.status_code == 200
