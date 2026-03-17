"""
Tests unitaires de base — sans base de données.

Ces tests vérifient la logique pure (domaine, scoring, normalisation, validation)
et peuvent être lancés sans PostgreSQL : pytest tests/test_basic.py
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError


# ── Domaine : machine d'états ────────────────────────────────────────────────


class TestStateMachine:
    """Tests de la machine de transitions ApplicationStatus."""

    def test_valid_transition_draft_to_ready(self):
        from app.domain.state_machine import validate_transition
        from app.domain.enums.application_status import ApplicationStatus as S
        # Ne doit pas lever d'exception
        validate_transition(S.DRAFT, S.READY_TO_SEND)

    def test_invalid_transition_draft_to_sent(self):
        from app.domain.state_machine import validate_transition
        from app.domain.enums.application_status import ApplicationStatus as S
        from app.domain.errors import BusinessRuleError
        with pytest.raises(BusinessRuleError):
            validate_transition(S.DRAFT, S.SENT)

    def test_archived_is_terminal(self):
        from app.domain.state_machine import validate_transition, ALLOWED_TRANSITIONS
        from app.domain.enums.application_status import ApplicationStatus as S
        from app.domain.errors import BusinessRuleError
        # ARCHIVED n'a aucune sortie
        assert ALLOWED_TRANSITIONS[S.ARCHIVED] == frozenset()
        with pytest.raises(BusinessRuleError):
            validate_transition(S.ARCHIVED, S.DRAFT)

    def test_interview_to_accepted(self):
        from app.domain.state_machine import validate_transition
        from app.domain.enums.application_status import ApplicationStatus as S
        validate_transition(S.INTERVIEW, S.ACCEPTED)

    def test_rejected_to_archived(self):
        from app.domain.state_machine import validate_transition
        from app.domain.enums.application_status import ApplicationStatus as S
        validate_transition(S.REJECTED, S.ARCHIVED)

    def test_all_statuses_have_transitions_defined(self):
        from app.domain.state_machine import ALLOWED_TRANSITIONS
        from app.domain.enums.application_status import ApplicationStatus
        for status in ApplicationStatus:
            assert status in ALLOWED_TRANSITIONS, f"{status} manquant dans ALLOWED_TRANSITIONS"


# ── Domaine : normalisation de texte ─────────────────────────────────────────


class TestTextNormalizer:
    """Tests des fonctions de normalisation de texte."""

    def test_dedup_removes_gender_markers(self):
        from app.domain.text_normalizer import normalize_title_for_dedup
        assert "stage data engineer" == normalize_title_for_dedup("Stage Data Engineer H/F")

    def test_dedup_keeps_contract_type(self):
        from app.domain.text_normalizer import normalize_title_for_dedup
        result = normalize_title_for_dedup("Data Engineer CDI Senior")
        assert "cdi" in result
        assert "senior" in result

    def test_search_removes_contract_type(self):
        from app.domain.text_normalizer import normalize_title_for_search
        result = normalize_title_for_search("Stage Data Engineer Junior")
        assert "stage" not in result
        assert "junior" not in result
        assert "data" in result

    def test_same_title_different_case_dedup_equal(self):
        from app.domain.text_normalizer import normalize_title_for_dedup
        a = normalize_title_for_dedup("STAGE Data Engineer H/F")
        b = normalize_title_for_dedup("stage data engineer h/f")
        assert a == b

    def test_normalize_company_removes_suffixes(self):
        from app.domain.text_normalizer import normalize_company
        assert normalize_company("BNP Paribas SA") == "bnp paribas"
        assert normalize_company("Google France") == "google france"

    def test_normalize_city_basic(self):
        from app.domain.text_normalizer import normalize_city
        result = normalize_city("Paris")
        assert result == "paris"

    def test_normalize_city_empty(self):
        from app.domain.text_normalizer import normalize_city
        assert normalize_city("") == ""

    def test_dedup_hash_deterministic(self):
        from app.services.offer_deduplicator import compute_cross_source_hash
        h1 = compute_cross_source_hash("Data Engineer", "Google", "Paris")
        h2 = compute_cross_source_hash("Data Engineer", "Google", "Paris")
        assert h1 == h2

    def test_dedup_hash_differs_on_company(self):
        from app.services.offer_deduplicator import compute_cross_source_hash
        h1 = compute_cross_source_hash("Data Engineer", "Google", "Paris")
        h2 = compute_cross_source_hash("Data Engineer", "Meta", "Paris")
        assert h1 != h2


# ── Scoring : service déterministe ───────────────────────────────────────────


class TestOfferScoringService:
    """Tests du scoring déterministe sans DB."""

    def _make_offer_and_payload(self, title, description, contract_type, work_mode=None, location=None, duration_months=None):
        """Crée un Offer et NormalizedOfferPayload minimaux pour le test."""
        from app.infrastructure.db.models.company import Company
        from app.infrastructure.db.models.source import Source
        from app.infrastructure.db.models.offer import Offer
        from app.infrastructure.db.models.application_followup import ApplicationFollowup  # noqa: F401 — registration
        from app.infrastructure.db.models.application import Application  # noqa: F401 — registration
        from app.domain.dto.normalized_offer_payload import NormalizedOfferPayload
        from app.domain.enums.work_mode import WorkMode

        offer = Offer(
            id=uuid.uuid4(),
            normalized_title=title,
            is_active=True,
        )
        payload = NormalizedOfferPayload(
            normalized_title=title,
            normalized_description=description,
            contract_type=contract_type,
            company_name="TestCo",
            location_text=location or "",
            work_mode=work_mode,
            duration_months=duration_months,
            checksum="test",
        )
        return offer, payload

    def test_stage_gets_25_points(self):
        from app.services.offer_scoring_service import OfferScoringService
        svc = OfferScoringService()
        offer, payload = self._make_offer_and_payload(
            "Stage développeur", "description", "Stage"
        )
        svc.score(offer, payload)
        assert offer.global_score >= 25

    def test_cdi_senior_penalized(self):
        from app.services.offer_scoring_service import OfferScoringService
        svc = OfferScoringService()
        offer, payload = self._make_offer_and_payload(
            "Développeur senior confirmé lead", "lead team", "CDI"
        )
        svc.score(offer, payload)
        # CDI -15, senior -10 → score négatif clampé à 0
        assert offer.global_score == 0.0

    def test_data_tag_detected(self):
        from app.services.offer_scoring_service import OfferScoringService
        svc = OfferScoringService()
        offer, payload = self._make_offer_and_payload(
            "Data Analyst", "data analyst SQL python", "Stage"
        )
        svc.score(offer, payload)
        assert offer.tags is not None
        assert "data" in offer.tags

    def test_score_clamped_0_100(self):
        from app.services.offer_scoring_service import OfferScoringService
        from app.domain.enums.work_mode import WorkMode
        svc = OfferScoringService()
        offer, payload = self._make_offer_and_payload(
            "Stage Data Scientist ML AI Python",
            "machine learning deep learning NLP LLM analytics data viz power bi econometr",
            "Stage",
            work_mode=WorkMode.REMOTE,
            location="Paris",
            duration_months=6,
        )
        svc.score(offer, payload)
        assert 0 <= offer.global_score <= 100

    def test_score_justification_keys(self):
        from app.services.offer_scoring_service import OfferScoringService
        svc = OfferScoringService()
        offer, payload = self._make_offer_and_payload("Stage Python", "python dev", "Stage")
        svc.score(offer, payload)
        assert "score" in offer.score_justification
        assert "détails" in offer.score_justification


# ── Schémas Pydantic ─────────────────────────────────────────────────────────


class TestPydanticSchemas:
    """Tests des validations Pydantic."""

    def test_recruiter_reply_rejects_empty_message(self):
        from app.api.schemas.application import RecruiterReplyCreate
        with pytest.raises(ValidationError):
            RecruiterReplyCreate(message_text="", channel="email")

    def test_recruiter_reply_rejects_invalid_channel(self):
        from app.api.schemas.application import RecruiterReplyCreate
        with pytest.raises(ValidationError):
            RecruiterReplyCreate(message_text="Bonjour", channel="fax")

    def test_recruiter_reply_valid_all_channels(self):
        from app.api.schemas.application import RecruiterReplyCreate
        for ch in ("email", "phone", "linkedin", "other"):
            r = RecruiterReplyCreate(message_text="Réponse recruteur", channel=ch)
            assert r.channel == ch

    def test_recruiter_reply_channel_none_allowed(self):
        from app.api.schemas.application import RecruiterReplyCreate
        r = RecruiterReplyCreate(message_text="Réponse sans canal")
        assert r.channel is None

    def test_recruiter_reply_max_length(self):
        from app.api.schemas.application import RecruiterReplyCreate
        # 5001 chars doit échouer
        with pytest.raises(ValidationError):
            RecruiterReplyCreate(message_text="a" * 5001)

    def test_followup_create_rejects_past_date(self):
        from app.api.schemas.application import FollowupCreate
        past = datetime.now(timezone.utc) - timedelta(days=1)
        with pytest.raises(ValidationError):
            FollowupCreate(scheduled_at=past)

    def test_followup_create_accepts_future_date(self):
        from app.api.schemas.application import FollowupCreate
        future = datetime.now(timezone.utc) + timedelta(days=7)
        f = FollowupCreate(scheduled_at=future)
        assert f.scheduled_at == future


# ── LLM Service : normalize_list ─────────────────────────────────────────────


class TestNormalizeList:
    """Tests de normalize_list() — coercion des sorties LLM."""

    def test_none_returns_none(self):
        from app.services.llm.llm_service import normalize_list
        assert normalize_list(None) is None

    def test_empty_list_returns_none(self):
        from app.services.llm.llm_service import normalize_list
        assert normalize_list([]) is None

    def test_list_of_strings(self):
        from app.services.llm.llm_service import normalize_list
        assert normalize_list(["python", "sql"]) == ["python", "sql"]

    def test_csv_string(self):
        from app.services.llm.llm_service import normalize_list
        assert normalize_list("python, sql, pandas") == ["python", "sql", "pandas"]

    def test_single_string(self):
        from app.services.llm.llm_service import normalize_list
        assert normalize_list("python") == ["python"]

    def test_dict_returns_none(self):
        from app.services.llm.llm_service import normalize_list
        assert normalize_list({"key": "value"}) is None

    def test_list_with_empty_elements_filtered(self):
        from app.services.llm.llm_service import normalize_list
        result = normalize_list(["python", "", "  ", "sql"])
        assert result == ["python", "sql"]


# ── LLM Cache : borne de taille ──────────────────────────────────────────────


class TestLLMCache:
    """Tests du cache LLM borné."""

    def test_cache_bounded(self):
        from app.services.llm.llm_service import _IN_MEMORY_CACHE, _MAX_CACHE_SIZE, _cache_put
        # Vider le cache
        _IN_MEMORY_CACHE.clear()
        # Remplir au-delà de la limite
        for i in range(_MAX_CACHE_SIZE + 10):
            _cache_put(f"key_{i}", f"value_{i}")
        assert len(_IN_MEMORY_CACHE) == _MAX_CACHE_SIZE

    def test_cache_evicts_oldest(self):
        from app.services.llm.llm_service import _IN_MEMORY_CACHE, _MAX_CACHE_SIZE, _cache_put
        _IN_MEMORY_CACHE.clear()
        # Remplir exactement à la limite
        for i in range(_MAX_CACHE_SIZE):
            _cache_put(f"key_{i}", f"value_{i}")
        # Ajouter une entrée de plus → key_0 doit être évincée
        _cache_put("new_key", "new_value")
        assert "key_0" not in _IN_MEMORY_CACHE
        assert "new_key" in _IN_MEMORY_CACHE


# ── SkillGapService : logique pure ───────────────────────────────────────────


class TestSkillGapHelpers:
    """Tests des fonctions pures de SkillGapService."""

    def test_extract_candidate_skills_none_profile(self):
        from app.services.skill_gap_service import _extract_candidate_skills
        assert _extract_candidate_skills(None) == set()

    def test_extract_candidate_skills_normalizes_case(self):
        from app.services.skill_gap_service import _extract_candidate_skills
        # Simuler un profil minimal
        class FakeProfile:
            skills = ["Python", "SQL"]
            tech_stack = ["DOCKER"]
        skills = _extract_candidate_skills(FakeProfile())
        assert "python" in skills
        assert "sql" in skills
        assert "docker" in skills

    def test_extract_candidate_skills_empty_lists(self):
        from app.services.skill_gap_service import _extract_candidate_skills
        class FakeProfile:
            skills = []
            tech_stack = []
        assert _extract_candidate_skills(FakeProfile()) == set()


# ── StrategyActionType : enum ─────────────────────────────────────────────────


class TestStrategyActionType:
    def test_all_values_present(self):
        from app.domain.enums.strategy_action_type import StrategyActionType
        values = {a.value for a in StrategyActionType}
        assert "APPLY_NOW" in values
        assert "SEND_FOLLOWUP" in values
        assert "PREPARE_INTERVIEW" in values
        assert "ARCHIVE_STALE" in values

    def test_is_str_enum(self):
        from app.domain.enums.strategy_action_type import StrategyActionType
        # StrEnum → les membres sont des str
        assert str(StrategyActionType.APPLY_NOW) == "APPLY_NOW"
