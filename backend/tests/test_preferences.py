"""Tests des endpoints /v1/preferences."""

import pytest


class TestGetPreferences:
    def test_requires_auth(self, client):
        resp = client.get("/v1/preferences")
        assert resp.status_code == 403

    def test_returns_default_profile_if_none(self, client, api_headers):
        resp = client.get("/v1/preferences", headers=api_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["preferred_contract_types"] is None
        assert data["minimum_duration_months"] is None

    def test_shape(self, client, api_headers):
        resp = client.get("/v1/preferences", headers=api_headers)
        assert resp.status_code == 200
        data = resp.json()
        for field in (
            "id",
            "preferred_contract_types",
            "preferred_work_modes",
            "preferred_locations",
            "preferred_keywords",
            "preferred_domains",
            "exclude_keywords",
            "minimum_duration_months",
            "created_at",
            "updated_at",
        ):
            assert field in data


class TestUpdatePreferences:
    def test_requires_auth(self, client):
        resp = client.put("/v1/preferences", json={})
        assert resp.status_code == 403

    def test_full_update(self, client, api_headers):
        payload = {
            "preferred_contract_types": ["Stage", "Alternance"],
            "preferred_work_modes": ["REMOTE", "HYBRID"],
            "preferred_locations": ["Paris", "Lyon"],
            "preferred_keywords": ["python", "fastapi"],
            "preferred_domains": ["data", "ml"],
            "exclude_keywords": ["COBOL"],
            "minimum_duration_months": 6,
        }
        resp = client.put("/v1/preferences", json=payload, headers=api_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["preferred_contract_types"] == ["Stage", "Alternance"]
        assert data["preferred_work_modes"] == ["REMOTE", "HYBRID"]
        assert data["minimum_duration_months"] == 6

    def test_empty_lists_stored_as_none(self, client, api_headers):
        payload = {
            "preferred_contract_types": [],
            "preferred_keywords": None,
        }
        resp = client.put("/v1/preferences", json=payload, headers=api_headers)
        assert resp.status_code == 200
        data = resp.json()
        # [] → None (comportement PUT: liste vide = champ non renseigné)
        assert data["preferred_contract_types"] is None

    def test_idempotent_get_after_put(self, client, api_headers):
        payload = {"preferred_domains": ["data"], "minimum_duration_months": 3}
        client.put("/v1/preferences", json=payload, headers=api_headers)
        resp = client.get("/v1/preferences", headers=api_headers)
        assert resp.status_code == 200
        assert resp.json()["preferred_domains"] == ["data"]
        assert resp.json()["minimum_duration_months"] == 3

    def test_put_replaces_previous_values(self, client, api_headers):
        # Premier PUT
        client.put(
            "/v1/preferences",
            json={"preferred_contract_types": ["Stage"], "minimum_duration_months": 6},
            headers=api_headers,
        )
        # Deuxième PUT sans minimum_duration_months → doit remettre à None
        resp = client.put(
            "/v1/preferences",
            json={"preferred_contract_types": ["Alternance"]},
            headers=api_headers,
        )
        data = resp.json()
        assert data["preferred_contract_types"] == ["Alternance"]
        assert data["minimum_duration_months"] is None
