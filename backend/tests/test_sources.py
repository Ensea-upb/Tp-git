"""Tests des endpoints admin /v1/sources."""

import uuid

import pytest

from app.infrastructure.db.models.source import Source


@pytest.fixture
def existing_source(db) -> Source:
    s = Source(
        id=uuid.uuid4(),
        name="Source Admin Test",
        source_type="api_officielle",
        base_url="https://api.example.com",
        is_active=True,
        check_frequency_hours=6,
    )
    db.add(s)
    db.flush()
    return s


class TestListSources:
    def test_requires_auth(self, client):
        resp = client.get("/v1/sources")
        assert resp.status_code == 403

    def test_returns_empty_list(self, client, api_headers):
        resp = client.get("/v1/sources", headers=api_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_existing_sources(self, client, api_headers, existing_source):
        resp = client.get("/v1/sources", headers=api_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        names = [s["name"] for s in data]
        assert "Source Admin Test" in names

    def test_source_shape(self, client, api_headers, existing_source):
        resp = client.get("/v1/sources", headers=api_headers)
        source = resp.json()[0]
        for field in ("id", "name", "source_type", "is_active", "check_frequency_hours", "created_at"):
            assert field in source


class TestCreateSource:
    def test_requires_auth(self, client):
        resp = client.post("/v1/sources", json={"name": "X", "source_type": "test"})
        assert resp.status_code == 403

    def test_creates_source(self, client, api_headers):
        payload = {
            "name": "Nouvelle Source",
            "source_type": "career_page",
            "base_url": "https://careers.example.com",
            "is_active": True,
            "check_frequency_hours": 12,
        }
        resp = client.post("/v1/sources", json=payload, headers=api_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Nouvelle Source"
        assert data["source_type"] == "career_page"
        assert "id" in data

    def test_conflict_on_duplicate_name(self, client, api_headers, existing_source):
        payload = {"name": "Source Admin Test", "source_type": "career_page"}
        resp = client.post("/v1/sources", json=payload, headers=api_headers)
        assert resp.status_code == 409


class TestUpdateSource:
    def test_requires_auth(self, client, existing_source):
        resp = client.patch(f"/v1/sources/{existing_source.id}", json={"is_active": False})
        assert resp.status_code == 403

    def test_deactivates_source(self, client, api_headers, existing_source):
        resp = client.patch(
            f"/v1/sources/{existing_source.id}",
            json={"is_active": False},
            headers=api_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_updates_frequency(self, client, api_headers, existing_source):
        resp = client.patch(
            f"/v1/sources/{existing_source.id}",
            json={"check_frequency_hours": 24},
            headers=api_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["check_frequency_hours"] == 24

    def test_404_on_unknown_source(self, client, api_headers):
        resp = client.patch(
            f"/v1/sources/{uuid.uuid4()}",
            json={"is_active": False},
            headers=api_headers,
        )
        assert resp.status_code == 404

    def test_partial_update_preserves_other_fields(self, client, api_headers, existing_source):
        resp = client.patch(
            f"/v1/sources/{existing_source.id}",
            json={"is_active": False},
            headers=api_headers,
        )
        data = resp.json()
        assert data["name"] == "Source Admin Test"
        assert data["source_type"] == "api_officielle"
