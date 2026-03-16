"""Tests des endpoints d'action utilisateur sur les offres."""

import uuid

import pytest

from app.domain.enums.user_status import UserStatus
from app.repositories.offer_user_status_repository import OfferUserStatusRepository


# ------------------------------------------------------------------ #
# Repository tests                                                     #
# ------------------------------------------------------------------ #

class TestOfferUserStatusRepository:
    def test_set_and_get(self, db, sample_offer):
        repo = OfferUserStatusRepository(db)
        repo.set_status(sample_offer.id, UserStatus.FAVORITE)
        db.flush()

        row = repo.get(sample_offer.id)
        assert row is not None
        assert row.status == UserStatus.FAVORITE

    def test_update_replaces_status(self, db, sample_offer):
        repo = OfferUserStatusRepository(db)
        repo.set_status(sample_offer.id, UserStatus.FAVORITE)
        repo.set_status(sample_offer.id, UserStatus.SHORTLISTED)
        db.flush()

        row = repo.get(sample_offer.id)
        assert row.status == UserStatus.SHORTLISTED

    def test_remove(self, db, sample_offer):
        repo = OfferUserStatusRepository(db)
        repo.set_status(sample_offer.id, UserStatus.REJECTED)
        db.flush()

        removed = repo.remove(sample_offer.id)
        assert removed is True

        row = repo.get(sample_offer.id)
        assert row is None

    def test_remove_nonexistent_returns_false(self, db, sample_offer):
        repo = OfferUserStatusRepository(db)
        result = repo.remove(sample_offer.id)
        assert result is False


# ------------------------------------------------------------------ #
# Endpoints — Favorite                                                 #
# ------------------------------------------------------------------ #

class TestFavoriteEndpoint:
    def test_requires_auth(self, client, sample_offer):
        resp = client.post(f"/v1/offers/{sample_offer.id}/favorite")
        assert resp.status_code == 403

    def test_add_favorite(self, client, api_headers, sample_offer):
        resp = client.post(
            f"/v1/offers/{sample_offer.id}/favorite",
            headers=api_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "FAVORITE"
        assert data["offer_id"] == str(sample_offer.id)

    def test_remove_favorite(self, client, api_headers, sample_offer):
        client.post(f"/v1/offers/{sample_offer.id}/favorite", headers=api_headers)
        resp = client.delete(f"/v1/offers/{sample_offer.id}/favorite", headers=api_headers)
        assert resp.status_code == 204

    def test_404_on_unknown_offer(self, client, api_headers):
        resp = client.post(f"/v1/offers/{uuid.uuid4()}/favorite", headers=api_headers)
        assert resp.status_code == 404


# ------------------------------------------------------------------ #
# Endpoints — Shortlist                                                #
# ------------------------------------------------------------------ #

class TestShortlistEndpoint:
    def test_add_shortlist(self, client, api_headers, sample_offer):
        resp = client.post(
            f"/v1/offers/{sample_offer.id}/shortlist",
            headers=api_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "SHORTLISTED"

    def test_remove_shortlist(self, client, api_headers, sample_offer):
        client.post(f"/v1/offers/{sample_offer.id}/shortlist", headers=api_headers)
        resp = client.delete(f"/v1/offers/{sample_offer.id}/shortlist", headers=api_headers)
        assert resp.status_code == 204


# ------------------------------------------------------------------ #
# Endpoints — Reject                                                   #
# ------------------------------------------------------------------ #

class TestRejectEndpoint:
    def test_add_reject(self, client, api_headers, sample_offer):
        resp = client.post(
            f"/v1/offers/{sample_offer.id}/reject",
            headers=api_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "REJECTED"

    def test_remove_reject(self, client, api_headers, sample_offer):
        client.post(f"/v1/offers/{sample_offer.id}/reject", headers=api_headers)
        resp = client.delete(f"/v1/offers/{sample_offer.id}/reject", headers=api_headers)
        assert resp.status_code == 204


# ------------------------------------------------------------------ #
# Statuts exclusifs                                                    #
# ------------------------------------------------------------------ #

class TestStatusExclusivity:
    def test_shortlist_replaces_favorite(self, client, api_headers, sample_offer):
        client.post(f"/v1/offers/{sample_offer.id}/favorite", headers=api_headers)
        client.post(f"/v1/offers/{sample_offer.id}/shortlist", headers=api_headers)

        # Le statut courant doit être SHORTLISTED
        resp = client.get(f"/v1/offers/{sample_offer.id}", headers=api_headers)
        assert resp.status_code == 200
        us = resp.json().get("user_status")
        assert us is not None
        assert us["status"] == "SHORTLISTED"

    def test_reject_replaces_shortlist(self, client, api_headers, sample_offer):
        client.post(f"/v1/offers/{sample_offer.id}/shortlist", headers=api_headers)
        client.post(f"/v1/offers/{sample_offer.id}/reject", headers=api_headers)
        resp = client.get(f"/v1/offers/{sample_offer.id}", headers=api_headers)
        us = resp.json().get("user_status")
        assert us["status"] == "REJECTED"


# ------------------------------------------------------------------ #
# Filtre par user_status dans GET /offers                             #
# ------------------------------------------------------------------ #

class TestOfferListFilterByStatus:
    def test_filter_favorites(self, client, api_headers, sample_offer):
        # Marquer l'offre comme favorite
        client.post(f"/v1/offers/{sample_offer.id}/favorite", headers=api_headers)

        # Filtrer les favorites
        resp = client.get(
            "/v1/offers?user_status=FAVORITE&is_active=",
            headers=api_headers,
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert any(i["id"] == str(sample_offer.id) for i in items)

    def test_filter_rejected_excludes_favorites(self, client, api_headers, sample_offer):
        client.post(f"/v1/offers/{sample_offer.id}/favorite", headers=api_headers)

        resp = client.get("/v1/offers?user_status=REJECTED", headers=api_headers)
        items = resp.json()["items"]
        assert not any(i["id"] == str(sample_offer.id) for i in items)
