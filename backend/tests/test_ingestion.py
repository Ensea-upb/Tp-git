"""Tests d'intégration du pipeline d'ingestion."""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.domain.dto.raw_offer_payload import RawOfferPayload
from app.domain.enums.offer_state import OfferState
from app.infrastructure.db.models.source import Source
from app.repositories.offer_repository import OfferRepository
from app.services.offer_ingestion_service import OfferIngestionService


# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #

@pytest.fixture
def active_source(db) -> Source:
    s = Source(
        id=uuid.uuid4(),
        name="Integration Test Source",
        source_type="career_page",
        base_url="https://test.example.com/jobs",
        is_active=True,
        check_frequency_hours=3,
    )
    db.add(s)
    db.flush()
    return s


def _make_raw_payload(
    title: str = "Stage Python",
    company: str = "Test Corp",
    url: str | None = None,
    ext_id: str | None = None,
) -> RawOfferPayload:
    return RawOfferPayload(
        source_name="Integration Test Source",
        source_type="career_page",
        raw_title=title,
        raw_content=f"Description de {title}. Stage de 6 mois à Paris.",
        raw_company_name=company,
        raw_location="Paris",
        offer_url=url or f"https://test.example.com/jobs/{uuid.uuid4()}",
        external_offer_id=ext_id or str(uuid.uuid4()),
    )


# ------------------------------------------------------------------ #
# Tests                                                                #
# ------------------------------------------------------------------ #

class TestRunSource:
    def test_creates_new_offers(self, db, active_source):
        payloads = [
            _make_raw_payload("Stage Python Senior"),
            _make_raw_payload("Stage DevOps"),
        ]

        service = OfferIngestionService(db)
        mock_connector = MagicMock()
        mock_connector.fetch.return_value = payloads
        mock_connector.is_available.return_value = True

        with patch.object(
            service.connector_manager, "get_connector", return_value=mock_connector
        ):
            result = service.run_source(active_source.id)

        assert result.total_fetched == 2
        assert result.new_offers == 2
        assert result.duplicates == 0
        assert result.errors == 0

        # Vérifier les offres en base
        offer_repo = OfferRepository(db)
        offers, total = offer_repo.get_all(page=1, page_size=50)
        assert total >= 2
        titles = {o.normalized_title for o in offers}
        assert "Stage Python Senior" in titles
        assert "Stage Devops" in titles or "Stage DevOps" in titles

    def test_deduplicates_duplicate_offers(self, db, active_source):
        url = f"https://test.example.com/jobs/{uuid.uuid4()}"
        payload = _make_raw_payload(url=url)

        mock_connector = MagicMock()
        mock_connector.fetch.return_value = [payload]
        mock_connector.is_available.return_value = True

        service = OfferIngestionService(db)

        with patch.object(service.connector_manager, "get_connector", return_value=mock_connector):
            result1 = service.run_source(active_source.id)

        assert result1.new_offers == 1
        assert result1.duplicates == 0

        # Rejouer avec le même payload
        with patch.object(service.connector_manager, "get_connector", return_value=mock_connector):
            result2 = service.run_source(active_source.id)

        assert result2.new_offers == 0
        assert result2.duplicates == 1

    def test_unknown_source_returns_error(self, db):
        service = OfferIngestionService(db)
        result = service.run_source(uuid.uuid4())  # UUID inexistant

        assert result.errors == 1

    def test_no_connector_returns_empty_result(self, db, active_source):
        service = OfferIngestionService(db)

        with patch.object(service.connector_manager, "get_connector", return_value=None):
            result = service.run_source(active_source.id)

        assert result.total_fetched == 0
        assert result.new_offers == 0
        assert result.errors == 0

    def test_fetch_exception_is_caught(self, db, active_source):
        mock_connector = MagicMock()
        mock_connector.fetch.side_effect = RuntimeError("Network error")
        mock_connector.is_available.return_value = True

        service = OfferIngestionService(db)

        with patch.object(service.connector_manager, "get_connector", return_value=mock_connector):
            result = service.run_source(active_source.id)

        assert result.errors == 1
        assert "fetch error" in result.error_details[0]


class TestRunAll:
    def test_run_all_returns_one_result_per_source(self, db, active_source):
        mock_connector = MagicMock()
        mock_connector.fetch.return_value = []
        mock_connector.is_available.return_value = True

        service = OfferIngestionService(db)

        with patch.object(service.connector_manager, "get_connector", return_value=mock_connector):
            results = service.run_all()

        # Au moins notre source de test
        assert len(results) >= 1
        source_names = [r.source_name for r in results]
        assert "Integration Test Source" in source_names

    def test_run_all_no_active_sources(self, db):
        # Aucune source active dans DB vide (transaction isolée)
        service = OfferIngestionService(db)
        results = service.run_all()
        assert results == []


class TestOfferState:
    def test_new_offer_state_is_normalized(self, db, active_source):
        url = f"https://test.example.com/jobs/{uuid.uuid4()}"
        payload = _make_raw_payload(url=url, title="Stage Backend Ingénieur")

        mock_connector = MagicMock()
        mock_connector.fetch.return_value = [payload]
        mock_connector.is_available.return_value = True

        service = OfferIngestionService(db)

        with patch.object(service.connector_manager, "get_connector", return_value=mock_connector):
            service.run_source(active_source.id)

        offer_repo = OfferRepository(db)
        offers, _ = offer_repo.get_all(page=1, page_size=50, state=OfferState.NORMALIZED)
        normalized_titles = {o.normalized_title for o in offers}
        assert any("Backend" in t or "Ingénieur" in t or "Ingenieur" in t for t in normalized_titles)
