"""
Tests Sprint 8 — Moteur d'offres robuste et intelligent.

Couvre :
- domain/text_normalizer : normalize_title_for_dedup, normalize_title_for_search,
                           normalize_company (France Travail safe), normalize_city
- OfferDeduplicator L4 (semantic_hash désormais persisté) et L5 fuzzy
- OfferRankingService : calcul score composite, y compris à l'ingestion
- API GET /v1/offers : filtres source, city, score_min COALESCE, sort=ranking_score
- work_mode absent → None (plus de biais ONSITE par défaut)
- BaseConnector : retry/timeout helper, IngestionReport
- IngestionReport : structure et logging
"""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.domain.text_normalizer import (
    normalize_city,
    normalize_company,
    normalize_title_for_dedup,
    normalize_title_for_search,
)
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
    ranking_score: float | None = None,
    days_old: int = 5,
    work_mode: WorkMode | None = WorkMode.HYBRID,
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
        ranking_score=ranking_score,
        primary_source_id=source.id,
        company_id=company.id,
        published_at=published_at,
        offer_url=f"https://test.example.com/{uuid.uuid4()}",
    )
    db.add(offer)
    db.flush()
    return offer


# ── PARTIE 1 : normalize_title_for_search ────────────────────────────────────


class TestNormalizeTitleForSearch:
    """Normalisation agressive pour la recherche plein texte."""

    def test_lowercase_and_remove_punctuation(self):
        assert normalize_title_for_search("Data Engineer!") == "data engineer"

    def test_removes_stage_keyword(self):
        result = normalize_title_for_search("Stage Data Engineer H/F")
        assert "stage" not in result
        assert "data" in result
        assert "engineer" in result

    def test_removes_hf_suffix(self):
        result = normalize_title_for_search("Développeur Python H/F")
        assert "h" not in result.split() and "f" not in result.split()

    def test_removes_junior_senior(self):
        result = normalize_title_for_search("Senior Data Scientist")
        assert "senior" not in result

    def test_removes_cdi_cdd(self):
        result = normalize_title_for_search("Data Analyst CDI")
        assert "cdi" not in result

    def test_removes_alternance(self):
        result = normalize_title_for_search("Data Engineer Alternance")
        assert "alternance" not in result

    def test_strips_accents(self):
        result = normalize_title_for_search("Ingénieur Données")
        assert "ingenieur" in result or "ingenieur" in result

    def test_empty_string(self):
        assert normalize_title_for_search("") == ""

    def test_only_stopwords(self):
        assert normalize_title_for_search("Stage Alternance H/F") == ""


# ── PARTIE 2 : normalize_title_for_dedup ─────────────────────────────────────


class TestNormalizeTitleForDedup:
    """Normalisation légère pour la déduplication — préserve les discriminants."""

    def test_preserves_stage(self):
        result = normalize_title_for_dedup("Stage Data Engineer H/F")
        assert "stage" in result
        assert "data" in result
        assert "engineer" in result

    def test_preserves_cdi(self):
        result = normalize_title_for_dedup("Data Analyst CDI Senior")
        assert "cdi" in result
        assert "senior" in result

    def test_preserves_alternance(self):
        result = normalize_title_for_dedup("Data Scientist Alternance")
        assert "alternance" in result

    def test_preserves_junior_senior(self):
        result = normalize_title_for_dedup("Senior Data Scientist Junior")
        assert "senior" in result
        assert "junior" in result

    def test_removes_hf(self):
        result = normalize_title_for_dedup("Data Engineer H/F")
        assert "h" not in result.split()
        assert "f" not in result.split()

    def test_stage_cdi_differ(self):
        """Un stage et un CDI pour le même poste ne doivent PAS avoir le même hash."""
        from app.services.offer_deduplicator import compute_cross_source_hash
        # normalize_title_for_dedup conserve "stage" vs "cdi" → hashes différents
        t_stage = normalize_title_for_dedup("Stage Data Analyst H/F")
        t_cdi = normalize_title_for_dedup("Data Analyst CDI Senior")
        assert t_stage != t_cdi

    def test_empty_string(self):
        assert normalize_title_for_dedup("") == ""


# ── PARTIE 3 : normalize_company ─────────────────────────────────────────────


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

    def test_france_preserved_in_brand_name(self):
        """'france' ne doit plus être supprimé des noms d'entreprise."""
        result = normalize_company("France Travail")
        assert "france" in result
        assert "travail" in result

    def test_google_france_preserved(self):
        """Google France doit conserver 'france' pour éviter les faux positifs."""
        result = normalize_company("Google France")
        assert "google" in result
        assert "france" in result

    def test_empty_string(self):
        assert normalize_company("") == ""


# ── PARTIE 4 : normalize_city ─────────────────────────────────────────────────


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


# ── PARTIE 5 : OfferRankingService ────────────────────────────────────────────


class TestOfferRankingService:
    def test_fresh_offer_scores_high_freshness(self, db):
        from app.services.offer_ranking_service import OfferRankingService
        offer = _make_offer(db, days_old=2)
        db.refresh(offer)
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


# ── PARTIE 6 : ranking_score calculé à l'ingestion ───────────────────────────


class TestRankingScoreAtIngestion:
    """Vérifie que ranking_score est peuplé directement lors de l'ingestion."""

    def test_ranking_score_set_on_new_offer(self, db):
        """Une offre créée via _process_one doit avoir un ranking_score non NULL."""
        from unittest.mock import MagicMock, patch
        from app.services.offer_ingestion_service import OfferIngestionService
        from app.domain.dto.raw_offer_payload import RawOfferPayload

        source = _make_source(db, source_type="wttj", name="WTTJ Ingestion Test")
        db.commit()

        payload = RawOfferPayload(
            source_name="WTTJ Ingestion Test",
            source_type="wttj",
            raw_title="Stage Data Engineer H/F",
            raw_content="Mission data engineering avec Python et Spark.",
            external_offer_id=f"ext-{uuid.uuid4()}",
            offer_url=f"https://wttj.co/{uuid.uuid4()}",
            raw_location="Paris",
            raw_company_name="Acme Corp",
            published_at_detected=datetime.now(timezone.utc),
        )

        service = OfferIngestionService(db)
        from app.domain.dto.ingestion_result import IngestionResult
        result = IngestionResult(source_name="WTTJ Ingestion Test")

        service._process_one(payload, source.id, result)
        db.flush()

        # Récupérer l'offre créée
        from sqlalchemy import select
        from app.infrastructure.db.models.offer import Offer as OfferModel
        offer = db.execute(
            select(OfferModel).where(OfferModel.offer_url == payload.offer_url)
        ).scalar_one_or_none()

        assert offer is not None, "L'offre doit être créée"
        assert offer.ranking_score is not None, "ranking_score doit être calculé à l'ingestion"
        assert 0.0 <= float(offer.ranking_score) <= 100.0

    def test_semantic_hash_set_on_new_offer(self, db):
        """Une offre créée via _process_one doit avoir un semantic_hash non NULL."""
        from app.services.offer_ingestion_service import OfferIngestionService
        from app.domain.dto.raw_offer_payload import RawOfferPayload
        from app.domain.dto.ingestion_result import IngestionResult

        source = _make_source(db, source_type="apec", name="APEC Ingestion Test")
        db.commit()

        payload = RawOfferPayload(
            source_name="APEC Ingestion Test",
            source_type="apec",
            raw_title="Data Scientist Alternance H/F",
            raw_content="Mission analyse de données.",
            external_offer_id=f"apec-{uuid.uuid4()}",
            offer_url=f"https://apec.fr/{uuid.uuid4()}",
            raw_location="Lyon",
            raw_company_name="TestCo SAS",
            published_at_detected=datetime.now(timezone.utc),
        )

        service = OfferIngestionService(db)
        result = IngestionResult(source_name="APEC Ingestion Test")
        service._process_one(payload, source.id, result)
        db.flush()

        from sqlalchemy import select
        from app.infrastructure.db.models.offer import Offer as OfferModel
        offer = db.execute(
            select(OfferModel).where(OfferModel.offer_url == payload.offer_url)
        ).scalar_one_or_none()

        assert offer is not None
        assert offer.semantic_hash is not None, "semantic_hash doit être persisté à l'ingestion"
        assert len(offer.semantic_hash) == 64  # SHA-256 hex


# ── PARTIE 7 : L4 réellement actif ────────────────────────────────────────────


class TestL4SemanticHash:
    """Vérifie que la déduplication L4 fonctionne quand semantic_hash est persisté."""

    def test_l4_detects_cross_source_duplicate(self, db):
        """Deux offres identiques (même titre+société+ville) de sources différentes → duplicate L4."""
        from app.services.offer_deduplicator import OfferDeduplicator, compute_cross_source_hash
        from app.domain.dto.normalized_offer_payload import NormalizedOfferPayload
        from app.domain.dto.raw_offer_payload import RawOfferPayload

        source1 = _make_source(db, source_type="wttj", name="Source WTTJ L4")
        source2 = _make_source(db, source_type="apec", name="Source APEC L4")
        company = _make_company(db, name="DeepThought SA")

        title = "Data Engineer Python"
        company_name = "DeepThought SA"
        city = "Paris"

        # Créer la première offre avec semantic_hash peuplé
        semantic_hash = compute_cross_source_hash(title, company_name, city)
        offer = Offer(
            id=uuid.uuid4(),
            normalized_title=title,
            company_id=company.id,
            primary_source_id=source1.id,
            current_state=OfferState.NORMALIZED,
            is_active=True,
            offer_url=f"https://wttj.co/l4-{uuid.uuid4()}",
            external_offer_id=f"wttj-l4-{uuid.uuid4()}",
            checksum="abc123deadbeef",
            semantic_hash=semantic_hash,
            location_text=city,
        )
        db.add(offer)
        db.flush()

        # Simuler une nouvelle offre identique venant d'APEC
        raw = RawOfferPayload(
            source_name="APEC",
            source_type="apec",
            raw_title=title,
            raw_content="Mission data engineering.",
            external_offer_id=f"apec-l4-{uuid.uuid4()}",
            offer_url=f"https://apec.fr/l4-{uuid.uuid4()}",
            raw_location=city,
            raw_company_name=company_name,
            published_at_detected=datetime.now(timezone.utc),
        )
        from app.repositories.offer_repository import OfferRepository
        from app.repositories.offer_raw_repository import OfferRawRepository
        from app.repositories.source_repository import SourceRepository

        normalized = NormalizedOfferPayload(
            normalized_title=title,
            normalized_description="Mission data engineering.",
            company_name=company_name,
            checksum="different_checksum_xyz",
            location_text=city,
        )

        dedup = OfferDeduplicator(
            offer_repo=OfferRepository(db),
            offer_raw_repo=OfferRawRepository(db),
            source_repo=SourceRepository(db),
        )
        decision = dedup.deduplicate(raw, normalized, source2.id)

        assert decision.decision == "duplicate"
        assert "L4" in decision.reason
        assert decision.matched_offer_id == offer.id

    def test_l4_no_false_positive_different_contract_type(self, db):
        """Un Stage et un CDI pour le même poste/société/ville ne sont pas des doublons L4."""
        from app.services.offer_deduplicator import OfferDeduplicator, compute_cross_source_hash
        from app.domain.dto.normalized_offer_payload import NormalizedOfferPayload
        from app.domain.dto.raw_offer_payload import RawOfferPayload
        from app.repositories.offer_repository import OfferRepository
        from app.repositories.offer_raw_repository import OfferRawRepository
        from app.repositories.source_repository import SourceRepository

        source1 = _make_source(db, source_type="wttj", name="WTTJ L4 FP")
        source2 = _make_source(db, source_type="apec", name="APEC L4 FP")
        company = _make_company(db, name="Sigma Corp")

        company_name = "Sigma Corp"
        city = "Paris"

        # Première offre : Stage Data Analyst → semantic_hash avec "stage data analyst"
        title_stage = "Stage Data Analyst H/F"
        semantic_hash_stage = compute_cross_source_hash(title_stage, company_name, city)
        offer = Offer(
            id=uuid.uuid4(),
            normalized_title=title_stage,
            company_id=company.id,
            primary_source_id=source1.id,
            current_state=OfferState.NORMALIZED,
            is_active=True,
            offer_url=f"https://wttj.co/fp-stage-{uuid.uuid4()}",
            external_offer_id=f"stage-fp-{uuid.uuid4()}",
            checksum="checksum_stage",
            semantic_hash=semantic_hash_stage,
            location_text=city,
        )
        db.add(offer)
        db.flush()

        # Nouvelle offre : Data Analyst CDI Senior — titre différent → hash différent
        title_cdi = "Data Analyst CDI Senior"
        raw = RawOfferPayload(
            source_name="APEC",
            source_type="apec",
            raw_title=title_cdi,
            raw_content="Poste CDI senior.",
            external_offer_id=f"cdi-fp-{uuid.uuid4()}",
            offer_url=f"https://apec.fr/fp-cdi-{uuid.uuid4()}",
            raw_location=city,
            raw_company_name=company_name,
            published_at_detected=datetime.now(timezone.utc),
        )
        normalized = NormalizedOfferPayload(
            normalized_title=title_cdi,
            normalized_description="Poste CDI senior.",
            company_name=company_name,
            checksum="checksum_cdi",
            location_text=city,
        )

        dedup = OfferDeduplicator(
            offer_repo=OfferRepository(db),
            offer_raw_repo=OfferRawRepository(db),
            source_repo=SourceRepository(db),
        )
        decision = dedup.deduplicate(raw, normalized, source2.id)

        # L4 ne doit PAS matcher car les titres complets sont différents
        assert "L4" not in decision.reason


# ── PARTIE 8 : work_mode None quand absent ────────────────────────────────────


class TestWorkModeDetection:
    def test_remote_detected(self):
        from app.services.offer_normalizer import _detect_work_mode
        assert _detect_work_mode("Poste en télétravail complet") == WorkMode.REMOTE

    def test_hybrid_detected(self):
        from app.services.offer_normalizer import _detect_work_mode
        assert _detect_work_mode("Mode hybride 3 jours/semaine") == WorkMode.HYBRID

    def test_no_mention_returns_none(self):
        """Sans mention de mode de travail, la valeur doit être None et non ONSITE."""
        from app.services.offer_normalizer import _detect_work_mode
        result = _detect_work_mode("Poste de Data Analyst basé à Paris")
        assert result is None, (
            f"Expected None (mode non détecté), got {result}. "
            "Ne pas biaiser vers ONSITE quand le mode n'est pas mentionné."
        )

    def test_normalizer_work_mode_none_when_absent(self):
        """Le normalizer complet renvoie work_mode=None si le contenu ne mentionne pas le mode."""
        from app.services.offer_normalizer import OfferNormalizer
        from app.domain.dto.raw_offer_payload import RawOfferPayload

        normalizer = OfferNormalizer()
        payload = RawOfferPayload(
            source_name="test",
            source_type="test",
            raw_title="Data Analyst",
            raw_content="Analyse de données financières. CDI. Paris.",
            raw_location="Paris",
            raw_company_name="Finance Corp",
            published_at_detected=None,
        )
        result = normalizer.normalize(payload)
        assert result.work_mode is None


# ── PARTIE 9 : API filtres ─────────────────────────────────────────────────────


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

    def test_filter_score_min_uses_coalesce(self, client, api_headers, db):
        """score_min filtre via COALESCE(ranking_score, global_score)."""
        # Offre avec ranking_score élevé
        _make_offer(db, score=40.0, ranking_score=90.0)
        # Offre avec ranking_score bas
        _make_offer(db, score=90.0, ranking_score=10.0)
        # Offre sans ranking_score — doit utiliser global_score comme fallback
        _make_offer(db, score=80.0, ranking_score=None)
        # Offre sous le seuil même via COALESCE
        _make_offer(db, score=20.0, ranking_score=15.0)
        db.commit()

        resp = client.get("/v1/offers?score_min=70&is_active=true", headers=api_headers)
        assert resp.status_code == 200
        data = resp.json()

        for item in data["items"]:
            rk = item.get("ranking_score")
            gl = item.get("global_score")
            effective = rk if rk is not None else gl
            assert effective is not None and effective >= 70, (
                f"Offre avec ranking={rk}, global={gl} ne doit pas passer score_min=70"
            )

    def test_no_offer_passes_score_min_without_any_score(self, client, api_headers, db):
        """Une offre sans aucun score ne doit pas passer le filtre score_min."""
        _make_offer(db, score=None, ranking_score=None)
        db.commit()

        resp = client.get("/v1/offers?score_min=50&is_active=true", headers=api_headers)
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            rk = item.get("ranking_score")
            gl = item.get("global_score")
            assert rk is not None or gl is not None

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


# ── PARTIE 10 : BaseConnector retry/timeout ───────────────────────────────────


class TestBaseConnectorRetry:
    def _make_connector(self):
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
        import httpx
        connector = self._make_connector()

        with patch("httpx.request", side_effect=httpx.ConnectError("timeout")) as mock_req:
            with pytest.raises(httpx.ConnectError):
                connector._http_get("http://example.com", retries=3)
            assert mock_req.call_count == 3

    def test_http_get_succeeds_on_second_try(self):
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


# ── PARTIE 11 : IngestionReport ───────────────────────────────────────────────


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


# ── PARTIE 12 : Déduplication fuzzy L5 ───────────────────────────────────────


class TestFuzzyDeduplication:
    def test_normalize_title_for_dedup_preserves_contract_type(self):
        """normalize_title_for_dedup conserve les indicateurs discriminants."""
        t1 = normalize_title_for_dedup("Stage Data Engineer H/F")
        t2 = normalize_title_for_dedup("Data Engineer CDI Senior")
        assert "stage" in t1
        assert "cdi" in t2
        # Les deux titres ne sont plus identiques après normalisation dedup
        assert t1 != t2

    def test_fuzzy_score_high_for_similar_titles(self):
        from rapidfuzz import fuzz
        t1 = normalize_title_for_dedup("Data Analyst Python — Paris")
        t2 = normalize_title_for_dedup("Data Analyst Python Paris")
        score = fuzz.token_sort_ratio(t1, t2)
        assert score >= 85

    def test_fuzzy_score_low_for_different_titles(self):
        from rapidfuzz import fuzz
        t1 = normalize_title_for_dedup("Data Scientist Machine Learning")
        t2 = normalize_title_for_dedup("Comptable Général Senior")
        score = fuzz.token_sort_ratio(t1, t2)
        assert score < 50

    def test_stage_vs_cdi_fuzzy_score_below_threshold(self):
        """'Stage Data Analyst' et 'Data Analyst CDI Senior' ne doivent pas dépasser 85%."""
        from rapidfuzz import fuzz
        t1 = normalize_title_for_dedup("Stage Data Analyst H/F")
        t2 = normalize_title_for_dedup("Data Analyst CDI Senior")
        score = fuzz.token_sort_ratio(t1, t2)
        # Avec les indicateurs conservés, le score sera plus bas qu'avant le fix
        # On vérifie surtout que ce n'est pas un faux positif (> 85)
        assert score < 85, (
            f"Faux positif L5 : score={score} entre Stage et CDI du même poste. "
            "normalize_title_for_dedup doit préserver les indicateurs de contrat."
        )
