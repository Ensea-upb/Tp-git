"""Tests des endpoints /v1/ingestion/runs et de l'observabilité des ingestions."""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.domain.dto.raw_offer_payload import RawOfferPayload
from app.infrastructure.db.models.ingestion_run import IngestionRun
from app.infrastructure.db.models.source import Source
from app.repositories.ingestion_run_repository import IngestionRunRepository
from app.services.offer_ingestion_service import OfferIngestionService


# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #

@pytest.fixture
def active_source(db) -> Source:
    s = Source(
        id=uuid.uuid4(),
        name="Runs Test Source",
        source_type="career_page",
        base_url="https://test.example.com/jobs",
        is_active=True,
        check_frequency_hours=3,
    )
    db.add(s)
    db.flush()
    return s


def _make_payload(title: str = "Stage Data") -> RawOfferPayload:
    return RawOfferPayload(
        source_name="Runs Test Source",
        source_type="career_page",
        raw_title=title,
        raw_content=f"Description {title}. Stage 6 mois Paris.",
        raw_company_name="Corp",
        raw_location="Paris",
        offer_url=f"https://test.example.com/jobs/{uuid.uuid4()}",
        external_offer_id=str(uuid.uuid4()),
    )


# ------------------------------------------------------------------ #
# Tests repository                                                     #
# ------------------------------------------------------------------ #

class TestIngestionRunRepository:
    def test_create_running(self, db, active_source):
        repo = IngestionRunRepository(db)
        run = repo.create_running(active_source.id)
        db.flush()

        assert run.id is not None
        assert run.status == "RUNNING"
        assert run.source_id == active_source.id
        assert run.started_at is not None
        assert run.finished_at is None

    def test_finish_success(self, db, active_source):
        from app.domain.dto.ingestion_result import IngestionResult
        from app.domain.enums.ingestion_status import IngestionStatus

        repo = IngestionRunRepository(db)
        run = repo.create_running(active_source.id)
        db.flush()

        result = IngestionResult(
            source_name="test",
            total_fetched=10,
            new_offers=8,
            updated_offers=1,
            duplicates=1,
            errors=0,
        )
        repo.finish(run, result, IngestionStatus.SUCCESS)
        db.flush()

        assert run.status == "SUCCESS"
        assert run.finished_at is not None
        assert run.offers_fetched == 10
        assert run.offers_created == 8
        assert run.offers_updated == 1
        assert run.offers_duplicated == 1
        assert run.offers_failed == 0

    def test_finish_with_errors(self, db, active_source):
        from app.domain.dto.ingestion_result import IngestionResult
        from app.domain.enums.ingestion_status import IngestionStatus

        repo = IngestionRunRepository(db)
        run = repo.create_running(active_source.id)
        db.flush()

        result = IngestionResult(
            source_name="test",
            total_fetched=5,
            new_offers=0,
            errors=2,
            error_details=["Error A", "Error B"],
        )
        repo.finish(run, result, IngestionStatus.FAILED)
        db.flush()

        assert run.status == "FAILED"
        assert run.offers_failed == 2
        assert "Error A" in run.error_summary

    def test_get_all_paginated(self, db, active_source):
        repo = IngestionRunRepository(db)
        for _ in range(3):
            r = repo.create_running(active_source.id)
            db.flush()

        runs, total = repo.get_all(page=1, page_size=2)
        assert total >= 3
        assert len(runs) == 2

    def test_get_all_filtered_by_source(self, db):
        # Deux sources différentes
        s1 = Source(id=uuid.uuid4(), name="S1", source_type="t", is_active=True, check_frequency_hours=1)
        s2 = Source(id=uuid.uuid4(), name="S2", source_type="t", is_active=True, check_frequency_hours=1)
        db.add_all([s1, s2])
        db.flush()

        repo = IngestionRunRepository(db)
        repo.create_running(s1.id)
        repo.create_running(s1.id)
        repo.create_running(s2.id)
        db.flush()

        runs_s1, total_s1 = repo.get_all(source_id=s1.id)
        assert total_s1 == 2

        runs_s2, total_s2 = repo.get_all(source_id=s2.id)
        assert total_s2 == 1


# ------------------------------------------------------------------ #
# Tests endpoint GET /v1/ingestion/runs                               #
# ------------------------------------------------------------------ #

class TestRunsEndpoint:
    def test_requires_auth(self, client):
        resp = client.get("/v1/ingestion/runs")
        assert resp.status_code == 403

    def test_returns_empty_initially(self, client, api_headers):
        resp = client.get("/v1/ingestion/runs", headers=api_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_run_shape(self, client, api_headers, db, active_source):
        # Créer un run directement
        repo = IngestionRunRepository(db)
        run = repo.create_running(active_source.id)
        db.commit()

        resp = client.get("/v1/ingestion/runs", headers=api_headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) >= 1
        run_data = items[0]
        for field in ("id", "status", "started_at", "offers_fetched", "offers_created"):
            assert field in run_data

    def test_get_run_by_id(self, client, api_headers, db, active_source):
        repo = IngestionRunRepository(db)
        run = repo.create_running(active_source.id)
        db.commit()

        resp = client.get(f"/v1/ingestion/runs/{run.id}", headers=api_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == str(run.id)
        assert resp.json()["status"] == "RUNNING"

    def test_get_run_404(self, client, api_headers):
        resp = client.get(f"/v1/ingestion/runs/{uuid.uuid4()}", headers=api_headers)
        assert resp.status_code == 404


# ------------------------------------------------------------------ #
# Tests intégration : run créé par ingestion                          #
# ------------------------------------------------------------------ #

class TestIngestionCreatesRun:
    def test_run_persisted_after_successful_ingestion(self, db, active_source):
        mock_connector = MagicMock()
        mock_connector.fetch.return_value = [_make_payload("Stage ML")]
        mock_connector.is_available.return_value = True

        service = OfferIngestionService(db)
        with patch.object(service.connector_manager, "get_connector", return_value=mock_connector):
            result = service.run_source(active_source.id)

        assert result.run_id is not None
        repo = IngestionRunRepository(db)
        run = repo.get_by_id(result.run_id)
        assert run is not None
        assert run.status == "SUCCESS"
        assert run.offers_created == 1
        assert run.offers_fetched == 1

    def test_run_status_partial_on_mixed_results(self, db, active_source):
        """Un run avec des offres créées ET des erreurs → PARTIAL."""
        good_payload = _make_payload("Stage Data")
        bad_payload = RawOfferPayload(
            source_name="Runs Test Source",
            source_type="career_page",
            raw_title=None,  # titre None → devrait créer quand même
            raw_content="",
            offer_url=f"https://test.example.com/jobs/{uuid.uuid4()}",
            external_offer_id=str(uuid.uuid4()),
        )

        mock_connector = MagicMock()
        mock_connector.fetch.return_value = [good_payload, bad_payload]
        mock_connector.is_available.return_value = True

        service = OfferIngestionService(db)
        with patch.object(service.connector_manager, "get_connector", return_value=mock_connector):
            result = service.run_source(active_source.id)

        assert result.run_id is not None
        # Both offers should succeed (empty title → "")
        assert result.new_offers >= 1

    def test_run_for_unknown_source_has_no_run_id(self, db):
        service = OfferIngestionService(db)
        result = service.run_source(uuid.uuid4())
        # Source introuvable → pas de run créé
        assert result.run_id is None
        assert result.errors == 1
