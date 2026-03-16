"""
Tests Sprint 7 — Machine de transitions + pagination + filtre.

La machine de transitions est testée en deux dimensions :
  - transitions valides : vérification que le chemin nominal passe
  - transitions invalides : vérification que BusinessRuleError (400) est levée

NOTE : les tests Sprint 6 existants sont mis à jour séparément pour respecter
       le nouveau graphe de transitions (DRAFT ne peut plus aller directement à SENT).
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.domain.enums.application_status import ApplicationStatus
from app.domain.errors import BusinessRuleError
from app.domain.state_machine import ALLOWED_TRANSITIONS, validate_transition
from app.infrastructure.db.models.offer import Offer


# ── Helpers ───────────────────────────────────────────────────────────


def _make_offer(db) -> Offer:
    offer = Offer(normalized_title="Stage ML Engineer", current_state="DETECTED")
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


def _create_app(client, api_headers, offer_id: str) -> dict:
    resp = client.post(
        "/v1/applications",
        json={"offer_id": offer_id},
        headers=api_headers,
    )
    assert resp.status_code == 201
    return resp.json()


def _patch_status(client, api_headers, app_id: str, new_status: str) -> int:
    return client.patch(
        f"/v1/applications/{app_id}/status",
        json={"status": new_status},
        headers=api_headers,
    ).status_code


# ── Tests : validate_transition (unit, sans DB) ───────────────────────


def test_state_machine_allowed_transitions_coverage():
    """Vérifie que tous les statuts ont une entrée dans le graphe."""
    for s in ApplicationStatus:
        assert s in ALLOWED_TRANSITIONS, f"Statut {s} absent du graphe"


def test_validate_transition_valid():
    validate_transition(ApplicationStatus.DRAFT, ApplicationStatus.READY_TO_SEND)
    validate_transition(ApplicationStatus.READY_TO_SEND, ApplicationStatus.SENT)
    validate_transition(ApplicationStatus.SENT, ApplicationStatus.FOLLOW_UP_DUE)
    validate_transition(ApplicationStatus.FOLLOW_UP_DUE, ApplicationStatus.INTERVIEW)
    validate_transition(ApplicationStatus.FOLLOW_UP_DUE, ApplicationStatus.REJECTED)
    validate_transition(ApplicationStatus.INTERVIEW, ApplicationStatus.ACCEPTED)
    validate_transition(ApplicationStatus.INTERVIEW, ApplicationStatus.REJECTED)
    # ANY → ARCHIVED
    for s in ApplicationStatus:
        if s != ApplicationStatus.ARCHIVED:
            validate_transition(s, ApplicationStatus.ARCHIVED)


def test_validate_transition_invalid_raises():
    with pytest.raises(BusinessRuleError):
        validate_transition(ApplicationStatus.DRAFT, ApplicationStatus.SENT)
    with pytest.raises(BusinessRuleError):
        validate_transition(ApplicationStatus.DRAFT, ApplicationStatus.INTERVIEW)
    with pytest.raises(BusinessRuleError):
        validate_transition(ApplicationStatus.SENT, ApplicationStatus.INTERVIEW)
    with pytest.raises(BusinessRuleError):
        validate_transition(ApplicationStatus.ARCHIVED, ApplicationStatus.DRAFT)
    with pytest.raises(BusinessRuleError):
        validate_transition(ApplicationStatus.ACCEPTED, ApplicationStatus.DRAFT)
    with pytest.raises(BusinessRuleError):
        validate_transition(ApplicationStatus.REJECTED, ApplicationStatus.SENT)


# ── Tests : transitions via API ───────────────────────────────────────


def test_full_happy_path_to_accepted(client, api_headers, db):
    """DRAFT → READY_TO_SEND → SENT → FOLLOW_UP_DUE → INTERVIEW → ACCEPTED."""
    offer = _make_offer(db)
    app = _create_app(client, api_headers, str(offer.id))
    app_id = app["id"]

    assert _patch_status(client, api_headers, app_id, "READY_TO_SEND") == 200
    assert _patch_status(client, api_headers, app_id, "SENT") == 200
    assert _patch_status(client, api_headers, app_id, "FOLLOW_UP_DUE") == 200
    assert _patch_status(client, api_headers, app_id, "INTERVIEW") == 200
    assert _patch_status(client, api_headers, app_id, "ACCEPTED") == 200

    resp = client.get(f"/v1/applications/{app_id}", headers=api_headers)
    assert resp.json()["status"] == "ACCEPTED"


def test_full_happy_path_to_rejected_via_followup(client, api_headers, db):
    """DRAFT → READY_TO_SEND → SENT → FOLLOW_UP_DUE → REJECTED."""
    offer = _make_offer(db)
    app = _create_app(client, api_headers, str(offer.id))
    app_id = app["id"]

    _patch_status(client, api_headers, app_id, "READY_TO_SEND")
    _patch_status(client, api_headers, app_id, "SENT")
    _patch_status(client, api_headers, app_id, "FOLLOW_UP_DUE")
    assert _patch_status(client, api_headers, app_id, "REJECTED") == 200


def test_archive_from_any_state(client, api_headers, db):
    """ANY → ARCHIVED doit fonctionner depuis chaque statut atteignable."""
    for initial_path in [
        [],
        ["READY_TO_SEND"],
        ["READY_TO_SEND", "SENT"],
        ["READY_TO_SEND", "SENT", "FOLLOW_UP_DUE"],
    ]:
        offer = _make_offer(db)
        app = _create_app(client, api_headers, str(offer.id))
        app_id = app["id"]
        for step in initial_path:
            _patch_status(client, api_headers, app_id, step)
        assert _patch_status(client, api_headers, app_id, "ARCHIVED") == 200, (
            f"ARCHIVED failed from path {initial_path}"
        )


@pytest.mark.parametrize(
    "from_status, to_status",
    [
        ("DRAFT", "SENT"),            # saute READY_TO_SEND
        ("DRAFT", "INTERVIEW"),       # saute plusieurs étapes
        ("DRAFT", "ACCEPTED"),        # état final sans chemin
        ("READY_TO_SEND", "FOLLOW_UP_DUE"),  # saute SENT
        ("SENT", "INTERVIEW"),        # doit passer par FOLLOW_UP_DUE
        ("SENT", "REJECTED"),         # doit passer par FOLLOW_UP_DUE
    ],
)
def test_invalid_transitions_return_400(client, api_headers, db, from_status, to_status):
    """Toute transition hors graphe doit retourner 400."""
    offer = _make_offer(db)
    app = _create_app(client, api_headers, str(offer.id))
    app_id = app["id"]

    # Atteindre from_status par transitions valides
    _valid_path_to(client, api_headers, app_id, from_status)

    resp = client.patch(
        f"/v1/applications/{app_id}/status",
        json={"status": to_status},
        headers=api_headers,
    )
    assert resp.status_code == 400, (
        f"Expected 400 for {from_status} → {to_status}, got {resp.status_code}"
    )


def test_archived_is_terminal(client, api_headers, db):
    """ARCHIVED ne peut aller nulle part."""
    offer = _make_offer(db)
    app = _create_app(client, api_headers, str(offer.id))
    app_id = app["id"]

    _patch_status(client, api_headers, app_id, "ARCHIVED")

    for target in ["DRAFT", "READY_TO_SEND", "SENT", "INTERVIEW", "ACCEPTED", "REJECTED"]:
        assert _patch_status(client, api_headers, app_id, target) == 400


# ── Tests : pagination + filtre ───────────────────────────────────────


def test_list_returns_paginated_response(client, api_headers, db):
    offer = _make_offer(db)
    for _ in range(3):
        _create_app(client, api_headers, str(offer.id))

    resp = client.get("/v1/applications", headers=api_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "limit" in data
    assert "has_next" in data
    assert isinstance(data["items"], list)


def test_list_filter_by_status(client, api_headers, db):
    offer = _make_offer(db)
    app = _create_app(client, api_headers, str(offer.id))
    app_id = app["id"]
    _patch_status(client, api_headers, app_id, "READY_TO_SEND")

    # Filtre READY_TO_SEND doit inclure notre application
    resp = client.get("/v1/applications?status=READY_TO_SEND", headers=api_headers)
    assert resp.status_code == 200
    ids = [a["id"] for a in resp.json()["items"]]
    assert app_id in ids

    # Filtre DRAFT ne doit pas l'inclure
    resp2 = client.get("/v1/applications?status=DRAFT", headers=api_headers)
    ids2 = [a["id"] for a in resp2.json()["items"]]
    assert app_id not in ids2


def test_list_pagination_limit(client, api_headers, db):
    offer = _make_offer(db)
    for _ in range(5):
        _create_app(client, api_headers, str(offer.id))

    resp = client.get("/v1/applications?limit=2&page=1", headers=api_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) <= 2
    assert data["limit"] == 2
    assert data["page"] == 1


def test_list_has_next_flag(client, api_headers, db):
    offer = _make_offer(db)
    for _ in range(3):
        _create_app(client, api_headers, str(offer.id))

    resp = client.get("/v1/applications?limit=2&page=1", headers=api_headers)
    data = resp.json()
    if data["total"] > 2:
        assert data["has_next"] is True

    # Dernière page : pas de suivant
    last_page = (data["total"] + 1) // 2
    resp2 = client.get(f"/v1/applications?limit=2&page={last_page}", headers=api_headers)
    assert resp2.json()["has_next"] is False


# ── Tests : offer_title + offer_source_name enrichis ──────────────────


def test_application_exposes_offer_title(client, api_headers, db):
    offer = _make_offer(db)
    app = _create_app(client, api_headers, str(offer.id))

    resp = client.get(f"/v1/applications/{app['id']}", headers=api_headers)
    assert resp.status_code == 200
    assert resp.json()["offer_title"] == "Stage ML Engineer"


# ── Helper : chemin de transitions valides vers un statut cible ───────


def _valid_path_to(client, api_headers, app_id: str, target: str) -> None:
    """Effectue les transitions valides minimales pour atteindre `target`."""
    _PATHS: dict[str, list[str]] = {
        "DRAFT": [],
        "READY_TO_SEND": ["READY_TO_SEND"],
        "SENT": ["READY_TO_SEND", "SENT"],
        "FOLLOW_UP_DUE": ["READY_TO_SEND", "SENT", "FOLLOW_UP_DUE"],
        "INTERVIEW": ["READY_TO_SEND", "SENT", "FOLLOW_UP_DUE", "INTERVIEW"],
        "ACCEPTED": ["READY_TO_SEND", "SENT", "FOLLOW_UP_DUE", "INTERVIEW", "ACCEPTED"],
        "REJECTED": ["READY_TO_SEND", "SENT", "FOLLOW_UP_DUE", "REJECTED"],
        "ARCHIVED": ["ARCHIVED"],
    }
    for step in _PATHS.get(target, []):
        client.patch(
            f"/v1/applications/{app_id}/status",
            json={"status": step},
            headers=api_headers,
        )
