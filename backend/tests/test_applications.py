"""
Tests Sprint 6 — Pipeline de candidatures.
Couvre :
- création d'une application
- changement de statut
- création de follow-up
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.domain.enums.application_status import ApplicationStatus
from app.infrastructure.db.models.application import Application
from app.infrastructure.db.models.application_followup import ApplicationFollowup
from app.infrastructure.db.models.offer import Offer
from app.repositories.application_repository import ApplicationRepository


# ── Helpers ───────────────────────────────────────────────────────────


def _make_offer(db) -> Offer:
    offer = Offer(normalized_title="Stage Data Engineer", current_state="DETECTED")
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


# ── Tests : création d'application ────────────────────────────────────


def test_create_application_default_status(db):
    offer = _make_offer(db)
    repo = ApplicationRepository(db)

    app = Application(offer_id=offer.id)
    repo.create(app)
    db.commit()
    db.refresh(app)

    assert app.id is not None
    assert app.status == ApplicationStatus.DRAFT
    assert app.draft_cover_letter is None
    assert app.draft_email is None


def test_create_application_with_channel(db):
    offer = _make_offer(db)
    repo = ApplicationRepository(db)

    app = Application(offer_id=offer.id, source_channel="LinkedIn", notes="Priorité haute")
    repo.create(app)
    db.commit()
    db.refresh(app)

    assert app.source_channel == "LinkedIn"
    assert app.notes == "Priorité haute"


def test_create_application_via_api(client, api_headers, db):
    offer = _make_offer(db)

    resp = client.post(
        "/v1/applications",
        json={"offer_id": str(offer.id), "source_channel": "Email"},
        headers=api_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "DRAFT"
    assert data["offer_id"] == str(offer.id)
    assert data["source_channel"] == "Email"


def test_list_applications_via_api(client, api_headers, db):
    offer = _make_offer(db)
    client.post(
        "/v1/applications",
        json={"offer_id": str(offer.id)},
        headers=api_headers,
    )

    resp = client.get("/v1/applications", headers=api_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1


# ── Tests : changement de statut ──────────────────────────────────────


def test_update_status_to_sent(client, api_headers, db):
    offer = _make_offer(db)
    create_resp = client.post(
        "/v1/applications",
        json={"offer_id": str(offer.id)},
        headers=api_headers,
    )
    app_id = create_resp.json()["id"]

    resp = client.patch(
        f"/v1/applications/{app_id}/status",
        json={"status": "SENT"},
        headers=api_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SENT"
    assert data["applied_at"] is not None


def test_update_status_to_interview(client, api_headers, db):
    offer = _make_offer(db)
    create_resp = client.post(
        "/v1/applications",
        json={"offer_id": str(offer.id)},
        headers=api_headers,
    )
    app_id = create_resp.json()["id"]

    # DRAFT → SENT → INTERVIEW
    client.patch(
        f"/v1/applications/{app_id}/status",
        json={"status": "SENT"},
        headers=api_headers,
    )
    resp = client.patch(
        f"/v1/applications/{app_id}/status",
        json={"status": "INTERVIEW"},
        headers=api_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "INTERVIEW"


def test_update_status_unknown_application(client, api_headers):
    resp = client.patch(
        f"/v1/applications/{uuid.uuid4()}/status",
        json={"status": "SENT"},
        headers=api_headers,
    )
    assert resp.status_code == 404


# ── Tests : follow-up ─────────────────────────────────────────────────


def test_add_followup(client, api_headers, db):
    offer = _make_offer(db)
    create_resp = client.post(
        "/v1/applications",
        json={"offer_id": str(offer.id)},
        headers=api_headers,
    )
    app_id = create_resp.json()["id"]

    # Passer en SENT d'abord
    client.patch(
        f"/v1/applications/{app_id}/status",
        json={"status": "SENT"},
        headers=api_headers,
    )

    scheduled = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    resp = client.post(
        f"/v1/applications/{app_id}/followup",
        json={"scheduled_at": scheduled, "notes": "Relance J+7"},
        headers=api_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "PENDING"
    assert data["notes"] == "Relance J+7"


def test_followup_changes_status_to_follow_up_due(client, api_headers, db):
    offer = _make_offer(db)
    create_resp = client.post(
        "/v1/applications",
        json={"offer_id": str(offer.id)},
        headers=api_headers,
    )
    app_id = create_resp.json()["id"]

    client.patch(
        f"/v1/applications/{app_id}/status",
        json={"status": "SENT"},
        headers=api_headers,
    )

    scheduled = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    client.post(
        f"/v1/applications/{app_id}/followup",
        json={"scheduled_at": scheduled},
        headers=api_headers,
    )

    resp = client.get(f"/v1/applications/{app_id}", headers=api_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "FOLLOW_UP_DUE"
    assert len(resp.json()["followups"]) == 1


def test_followup_requires_existing_application(client, api_headers):
    scheduled = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    resp = client.post(
        f"/v1/applications/{uuid.uuid4()}/followup",
        json={"scheduled_at": scheduled},
        headers=api_headers,
    )
    assert resp.status_code == 404


# ── Test : auth ───────────────────────────────────────────────────────


def test_applications_require_auth(client, db):
    offer = _make_offer(db)
    resp = client.post("/v1/applications", json={"offer_id": str(offer.id)})
    assert resp.status_code == 401
