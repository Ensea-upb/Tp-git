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


# ── Tests : états terminaux protégés (fix 2) ──────────────────────────


@pytest.mark.parametrize("terminal_status", ["REJECTED", "ACCEPTED", "ARCHIVED"])
def test_cannot_transition_from_terminal_status(client, api_headers, db, terminal_status):
    offer = _make_offer(db)
    create_resp = client.post(
        "/v1/applications",
        json={"offer_id": str(offer.id)},
        headers=api_headers,
    )
    app_id = create_resp.json()["id"]

    # Aller directement en statut terminal
    client.patch(
        f"/v1/applications/{app_id}/status",
        json={"status": terminal_status},
        headers=api_headers,
    )

    # Toute transition depuis un état terminal doit être bloquée
    resp = client.patch(
        f"/v1/applications/{app_id}/status",
        json={"status": "DRAFT"},
        headers=api_headers,
    )
    assert resp.status_code == 400


# ── Tests : follow-up atomique (fix 1) ────────────────────────────────


def test_followup_and_status_update_are_atomic(client, api_headers, db):
    """Vérifie que le follow-up et la mise à jour de statut sont persistés ensemble."""
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

    scheduled = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    client.post(
        f"/v1/applications/{app_id}/followup",
        json={"scheduled_at": scheduled},
        headers=api_headers,
    )

    # Les deux effets doivent être visibles en un seul GET
    resp = client.get(f"/v1/applications/{app_id}", headers=api_headers)
    data = resp.json()
    assert data["status"] == "FOLLOW_UP_DUE"
    assert len(data["followups"]) == 1


# ── Tests : restriction aux statuts autorisés (fix 5) ─────────────────


@pytest.mark.parametrize("forbidden_status", ["DRAFT", "READY_TO_SEND", "REJECTED", "ACCEPTED", "ARCHIVED"])
def test_followup_forbidden_on_inactive_statuses(client, api_headers, db, forbidden_status):
    offer = _make_offer(db)
    create_resp = client.post(
        "/v1/applications",
        json={"offer_id": str(offer.id)},
        headers=api_headers,
    )
    app_id = create_resp.json()["id"]

    # Forcer le statut (ne pas passer par transition gardée pour les terminaux)
    # On set direct via patch (DRAFT → forbidden_status est autorisé sauf si terminal)
    client.patch(
        f"/v1/applications/{app_id}/status",
        json={"status": forbidden_status},
        headers=api_headers,
    )

    scheduled = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    resp = client.post(
        f"/v1/applications/{app_id}/followup",
        json={"scheduled_at": scheduled},
        headers=api_headers,
    )
    assert resp.status_code == 400


# ── Tests : scheduled_at dans le futur (fix 4) ────────────────────────


def test_followup_past_date_rejected(client, api_headers, db):
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

    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    resp = client.post(
        f"/v1/applications/{app_id}/followup",
        json={"scheduled_at": past},
        headers=api_headers,
    )
    assert resp.status_code == 422  # validation Pydantic


def test_followup_now_rejected(client, api_headers, db):
    """Une date = maintenant doit aussi être refusée (strictement futur)."""
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

    # Utilise une date légèrement dans le passé pour simuler "maintenant ou avant"
    now_minus = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    resp = client.post(
        f"/v1/applications/{app_id}/followup",
        json={"scheduled_at": now_minus},
        headers=api_headers,
    )
    assert resp.status_code == 422


# ── Tests : drafts_ready (fix 3) ──────────────────────────────────────


def test_new_application_has_drafts_ready_false(client, api_headers, db):
    offer = _make_offer(db)
    resp = client.post(
        "/v1/applications",
        json={"offer_id": str(offer.id)},
        headers=api_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["drafts_ready"] is False


def test_drafts_ready_exposed_in_get(client, api_headers, db):
    offer = _make_offer(db)
    create_resp = client.post(
        "/v1/applications",
        json={"offer_id": str(offer.id)},
        headers=api_headers,
    )
    app_id = create_resp.json()["id"]

    resp = client.get(f"/v1/applications/{app_id}", headers=api_headers)
    assert "drafts_ready" in resp.json()
    assert resp.json()["drafts_ready"] is False
