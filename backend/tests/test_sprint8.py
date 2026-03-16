"""
Tests Sprint 8 — Moteur d'offres robuste et intelligent.

Couvre :
- domain/text_normalizer : normalize_title, normalize_company, normalize_city
- OfferDeduplicator L5 : similarité fuzzy
- OfferRankingService : calcul score composite
- API GET /v1/offers : filtres source, city, score_min, sort=ranking_score
- BaseConnector : retry/timeout helper, IngestionReport
- IngestionReport : structure et logging
"""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.domain.text_normalizer import normalize_city, normalize_company, normalize_title
from app.domain.dto.ingestion_report import IngestionReport
from app.infrastructure.db.models.offer import Offer
from app.infrastructure.db.models.source import Source
from app.infrastructure.db.models.company import Company
from app.domain.enums.offer_state import OfferState
from app.domain.enums.work_mode import WorkMode


# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_source(db, source_type: str = "wttj", name: str = "TestSource") -> Source:
    s = Source(
        id=uuid.uuid4(),
        name=name,
        source_type=source_type,
        is_active=True,
        check_frequency_hours=3,
    )
    db.add(s)
    db.flush()
    return s


def _make_company(db, name: str = "Acme Corp") -> Company:
    c = Company(id=uuid.uuid4(), name=name)
    db.add(c)
    db.flush()
    return c


def _make_offer(
    db,
    title: str = "Stage Data Engineer",
    source_type: str = "wttj",
    city: str = "Paris",
    score: float | None = None,
    days_old: int = 5,
    work_mode: WorkMode = WorkMode.HYBRID,
) -> Offer:
    source = _make_source(db, source_type=source_type)
    company = _make_company(db)
    published_at = datetime.now(timezone.utc) - timedelta(days=days_old)
    offer = Offer(
        id=uuid.uuid4(),
        normalized_title=title,
        contract_type="Stage",
        location_text=city,
        work_mode=work_mode,
        current_state=OfferState.NORMALIZED,
        is_active=True,
        global_score=score,
        primary_source_id=source.id,
        company_id=company.id,
        published_at=published_at,
        offer_url=f"https://test.example.com/{uuid.uuid4()}",
    )
    db.add(offer)
    db.flush()
    return offer


# ── PARTIE 1 : text_normalizer ────────────────────────────────────────────────


class TestNormalizeTitle:
    def test_lowercase_and_remove_punctuation(self):
        assert normalize_title("Data Engineer!") == "data engineer"

    def test_removes_stage_keyword(self):
        result = normalize_title("Stage Data Engineer H/F")
        assert "stage" not in result
        assert "data" in result
        assert "engineer" in result

    def test_removes_hf_suffix(self):
        result = normalize_title("Développeur Python H/F")
        assert "h" not in result.split() and "f" not in result.split()

    def test_removes_junior_senior(self):
        result = normalize_title("Senior Data Scientist")
        assert "senior" not in result

    def test_strips_accents(self):
        result = normalize_title("Ingénieur Données")
        assert "ingenieur" in result or "ingenieur" in result

    def test_empty_string(self):
        assert normalize_title("") == ""

    def test_only_stopwords(self):
        assert normalize_title("Stage Alternance H/F") == ""


class TestNormalizeCompany:
    def test_removes_sa_suffix(self):
        result = normalize_company("BNP Paribas SA")
        assert "sa" not in result.split()
        assert "bnp" in result

    def test_removes_sas_suffix(self):
        result = normalize_company("Capgemini SAS")
        assert "sas" not in result.split()

    def test_removes_ltd(self):
        result = normalize_company("Acme Ltd")
        assert "ltd" not in result

    def test_removes_group(self):
        result = normalize_company("L'Oréal Group")
        assert "group" not in result
        assert "oreal" in result

    def test_removes_france_suffix(self):
        result = normalize_company("Google France")
        assert "france" not in result

    def test_empty_string(self):
        assert normalize_company("") == ""


class TestNormalizeCity:
    def test_lowercase(self):
        assert normalize_city("Paris").lower() == normalize_city("paris")

    def test_strips_accents(self):
        result = normalize_city("Île-de-France")
        assert "ile" in result

    def test_removes_cedex(self):
        result = normalize_city("Lyon Cedex 03")
        assert "cedex" not in result
        assert "lyon" in result

    def test_empty_string(self):
        assert normalize_city("") == ""


# ── PARTIE 2 : OfferRankingService ────────────────────────────────────────────


class TestOfferRankingService:
    def test_fresh_offer_scores_high_freshness(self, db):
        from app.services.offer_ranking_service import OfferRankingService
        offer = _make_offer(db, days_old=2)
        db.refresh(offer)
        # Force load relations
        _ = offer.primary_source

        service = OfferRankingService(db)
        score = service.score_offer(offer)
        assert score > 0
        assert score <= 100.0
        assert offer.ranking_score == round(score, 2)

    def test_old_offer_scores_lower(self, db):
        from app.services.offer_ranking_service import OfferRankingService
        fresh = _make_offer(db, days_old=3, title="Data Scientist Machine Learning Python")
        old = _make_offer(db, days_old=120, title="Data Scientist Machine Learning Python")
        db.refresh(fresh)
        db.refresh(old)

        service = OfferRankingService(db)
        score_fresh = service.score_offer(fresh)
        score_old = service.score_offer(old)
        assert score_fresh > score_old

    def test_data_title_scores_higher_than_unrelated(self, db):
        from app.services.offer_ranking_service import OfferRankingService
        data_offer = _make_offer(db, title="Data Analyst Machine Learning Python", days_old=5)
        other_offer = _make_offer(db, title="Responsable Comptable", days_old=5)
        db.refresh(data_offer)
        db.refresh(other_offer)

        service = OfferRankingService(db)
        score_data = service.score_offer(data_offer)
        score_other = service.score_offer(other_offer)
        assert score_data > score_other

    def test_paris_location_scores_high(self, db):
        from app.services.offer_ranking_service import OfferRankingService
        paris = _make_offer(db, city="Paris", title="Stage", days_old=5)
        unknown = _make_offer(db, city="Inconnu-sur-Mer", title="Stage", days_old=5)
        db.refresh(paris)
        db.refresh(unknown)

        service = OfferRankingService(db)
        score_paris = service.score_offer(paris)
        score_unknown = service.score_offer(unknown)
        assert score_paris > score_unknown

    def test_remote_scores_well(self, db):
        from app.services.offer_ranking_service import OfferRankingService
        remote = _make_offer(db, work_mode=WorkMode.REMOTE, city="", days_old=5)
        db.refresh(remote)
        service = OfferRankingService(db)
        score = service.score_offer(remote)
        assert score > 15.0

    def test_score_clamped_0_100(self, db):
        from app.services.offer_ranking_service import OfferRankingService
        offer = _make_offer(db, title="Data ML AI Analytics Python Spark NLP", days_old=1)
        db.refresh(offer)
        service = OfferRankingService(db)
        score = service.score_offer(offer)
        assert 0.0 <= score <= 100.0

    def test_score_all_returns_count(self, db):
        from app.services.offer_ranking_service import OfferRankingService
        for _ in range(3):
            _make_offer(db, days_old=5)
        db.commit()
        service = OfferRankingService(db)
        count = service.score_all(active_only=True)
        assert count >= 3


# ── PARTIE 3 : API filtres ─────────────────────────────────────────────────────


class TestOfferApiFilters:
    def test_filter_by_city(self, client, api_headers, db):
        _make_offer(db, city="Paris")
        _make_offer(db, city="Lyon")
        db.commit()

        resp = client.get("/v1/offers?city=Paris&is_active=true", headers=api_headers)
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["location_text"] and "paris" in item["location_text"].lower()

    def test_filter_by_source_type(self, client, api_headers, db):
        _make_offer(db, source_type="wttj")
        _make_offer(db, source_type="apec")
        db.commit()

        resp = client.get("/v1/offers?source=wttj&is_active=true", headers=api_headers)
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            if item["primary_source"]:
                assert item["primary_source"]["source_type"] == "wttj"

    def test_filter_by_score_min(self, client, api_headers, db):
        _make_offer(db, score=90.0)
        _make_offer(db, score=10.0)
        db.commit()

        resp = client.get("/v1/offers?score_min=50&is_active=true", headers=api_headers)
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            score = item.get("ranking_score") or item.get("global_score") or 0
            assert score >= 50 or item.get("ranking_score") is None

    def test_sort_by_ranking_score(self, client, api_headers, db):
        db.commit()
        resp = client.get("/v1/offers?sort_by=ranking_score&is_active=true", headers=api_headers)
        assert resp.status_code == 200

    def test_ranking_score_in_response(self, client, api_headers, db):
        _make_offer(db)
        db.commit()
        resp = client.get("/v1/offers?is_active=true", headers=api_headers)
        assert resp.status_code == 200
        data = resp.json()
        if data["items"]:
            assert "ranking_score" in data["items"][0]


# ── PARTIE 4 : BaseConnector retry/timeout ────────────────────────────────────


class TestBaseConnectorRetry:
    def _make_connector(self):
        """Crée un connecteur minimal pour tester les méthodes de BaseConnector."""
        from app.connectors.base import BaseConnector
        from app.domain.dto.raw_offer_payload import RawOfferPayload

        class _DummyConnector(BaseConnector):
            source_type = "test"

            def _do_fetch(self) -> list[RawOfferPayload]:
                return []

        source = MagicMock()
        source.name = "TestSource"
        return _DummyConnector(source)

    def test_fetch_returns_ingestion_report(self):
        connector = self._make_connector()
        result = connector.fetch()
        assert isinstance(result, list)
        assert connector.last_report is not None
        assert isinstance(connector.last_report, IngestionReport)

    def test_ingestion_report_has_duration(self):
        connector = self._make_connector()
        connector.fetch()
        assert connector.last_report.duration_seconds >= 0.0

    def test_ingestion_report_source_name(self):
        connector = self._make_connector()
        connector.fetch()
        assert connector.last_report.source == "TestSource"

    def test_fetch_wraps_exception_in_report(self):
        from app.connectors.base import BaseConnector
        from app.domain.dto.raw_offer_payload import RawOfferPayload

        class _CrashingConnector(BaseConnector):
            source_type = "test"

            def _do_fetch(self) -> list[RawOfferPayload]:
                raise RuntimeError("Connexion refusée")

        source = MagicMock()
        source.name = "CrashSource"
        connector = _CrashingConnector(source)

        result = connector.fetch()
        assert result == []
        assert connector.last_report.errors == 1
        assert "Connexion refusée" in connector.last_report.error_details[0]

    def test_http_get_retries_on_failure(self):
        """_http_get doit lever une exception après 3 tentatives échouées."""
        import httpx
        connector = self._make_connector()

        with patch("httpx.request", side_effect=httpx.ConnectError("timeout")) as mock_req:
            with pytest.raises(httpx.ConnectError):
                connector._http_get("http://example.com", retries=3)
            assert mock_req.call_count == 3

    def test_http_get_succeeds_on_second_try(self):
        """_http_get retourne la réponse dès qu'une tentative réussit."""
        import httpx
        connector = self._make_connector()

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch(
            "httpx.request",
            side_effect=[httpx.ConnectError("err"), mock_response],
        ) as mock_req:
            resp = connector._http_get("http://example.com", retries=3)
            assert resp == mock_response
            assert mock_req.call_count == 2


# ── PARTIE 5 : IngestionReport ───────────────────────────────────────────────


class TestIngestionReport:
    def test_str_representation(self):
        report = IngestionReport(
            source="APEC",
            fetched=42,
            inserted=10,
            duplicates=30,
            errors=2,
            duration_seconds=1.23,
        )
        s = str(report)
        assert "APEC" in s
        assert "42" in s
        assert "1.23" in s

    def test_default_values(self):
        report = IngestionReport(source="Test")
        assert report.fetched == 0
        assert report.inserted == 0
        assert report.duplicates == 0
        assert report.errors == 0
        assert report.error_details == []


# ── PARTIE 6 : Déduplication fuzzy (L5) ──────────────────────────────────────


class TestFuzzyDeduplication:
    def test_normalize_title_used_in_dedup(self):
        """Vérifie que normalize_title traite bien les variantes pour la comparaison."""
        t1 = normalize_title("Stage Data Engineer H/F")
        t2 = normalize_title("Data Engineer Stage — Junior")
        # Les deux pointent vers "data engineer" après normalisation
        assert "data" in t1 and "engineer" in t1
        assert "data" in t2 and "engineer" in t2

    def test_fuzzy_score_high_for_similar_titles(self):
        from rapidfuzz import fuzz
        t1 = normalize_title("Data Analyst Python — Paris")
        t2 = normalize_title("Data Analyst Python Paris")
        score = fuzz.token_sort_ratio(t1, t2)
        assert score >= 85

    def test_fuzzy_score_low_for_different_titles(self):
        from rapidfuzz import fuzz
        t1 = normalize_title("Data Scientist Machine Learning")
        t2 = normalize_title("Comptable Général Senior")
        score = fuzz.token_sort_ratio(t1, t2)
        assert score < 50
