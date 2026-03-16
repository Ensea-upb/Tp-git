"""Tests for offer LLM analysis and profile matching services."""
import json
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.infrastructure.db.models.offer import Offer
from app.infrastructure.db.models.offer_llm_analysis import OfferLLMAnalysis
from app.infrastructure.db.models.profile_match_llm import ProfileMatchLLM
from app.infrastructure.db.models.candidate_profile import CandidateProfile, DEFAULT_CANDIDATE_ID
from app.services.offer_llm_analysis_service import OfferLLMAnalysisService
from app.services.profile_matching_service import ProfileMatchingService


def _make_offer(title="Data Science Intern"):
    offer = MagicMock(spec=Offer)
    offer.id = uuid.uuid4()
    offer.normalized_title = title
    offer.normalized_description = "A great internship opportunity in data science."
    offer.contract_type = "Stage"
    offer.duration_months = 6
    offer.location_text = "Paris"
    offer.company = MagicMock()
    offer.company.name = "Acme Corp"
    offer.work_mode = "HYBRID"
    return offer


def _make_profile():
    profile = MagicMock(spec=CandidateProfile)
    profile.id = DEFAULT_CANDIDATE_ID
    profile.full_name = "Jane Doe"
    profile.current_level = "Master 2 Data Science"
    profile.school = "Paris Dauphine"
    profile.summary = "Passionate data scientist"
    profile.skills = ["Python", "Machine Learning", "SQL"]
    profile.tech_stack = ["Python", "Pandas", "scikit-learn"]
    profile.target_domains = ["data", "ml"]
    profile.availability = "March 2026"
    profile.languages = ["French", "English"]
    return profile


# ---- OfferLLMAnalysisService -----------------------------------------------

@pytest.mark.asyncio
async def test_analyze_offer_success():
    offer = _make_offer()
    db = MagicMock()

    mock_analysis_repo = MagicMock()
    captured = {}

    def fake_upsert(analysis):
        captured["analysis"] = analysis
        analysis.analysis_status = "DONE"
        return analysis

    mock_analysis_repo.upsert = fake_upsert

    llm_json_response = {
        "summary": "Data internship at Acme",
        "missions": ["Analyze data", "Build models"],
        "skills_required": ["Python", "SQL"],
        "tech_stack": ["Python", "Spark"],
        "seniority_level": "junior",
    }

    with patch("app.services.offer_llm_analysis_service.OfferRepository") as MockOfferRepo, \
         patch("app.services.offer_llm_analysis_service.OfferLLMAnalysisRepository") as MockAnalysisRepo, \
         patch("app.services.offer_llm_analysis_service.call_llm_json", AsyncMock(return_value=llm_json_response)):

        MockOfferRepo.return_value.get_by_id.return_value = offer
        MockAnalysisRepo.return_value = mock_analysis_repo

        service = OfferLLMAnalysisService(db)
        result = await service.analyze_offer(offer.id)

    assert captured["analysis"].summary == "Data internship at Acme"
    assert captured["analysis"].missions == ["Analyze data", "Build models"]
    assert captured["analysis"].analysis_status == "DONE"


@pytest.mark.asyncio
async def test_analyze_offer_llm_failure_stores_failed_status():
    offer = _make_offer()
    db = MagicMock()

    mock_analysis_repo = MagicMock()
    captured = {}

    def fake_upsert(analysis):
        captured["analysis"] = analysis
        return analysis

    mock_analysis_repo.upsert = fake_upsert

    with patch("app.services.offer_llm_analysis_service.OfferRepository") as MockOfferRepo, \
         patch("app.services.offer_llm_analysis_service.OfferLLMAnalysisRepository") as MockAnalysisRepo, \
         patch("app.services.offer_llm_analysis_service.call_llm_json", AsyncMock(side_effect=Exception("Ollama down"))):

        MockOfferRepo.return_value.get_by_id.return_value = offer
        MockAnalysisRepo.return_value = mock_analysis_repo

        service = OfferLLMAnalysisService(db)
        result = await service.analyze_offer(offer.id)

    assert captured["analysis"].analysis_status == "FAILED"
    assert "Ollama down" in captured["analysis"].raw_response


@pytest.mark.asyncio
async def test_analyze_offer_not_found_raises():
    db = MagicMock()
    with patch("app.services.offer_llm_analysis_service.OfferRepository") as MockOfferRepo:
        MockOfferRepo.return_value.get_by_id.return_value = None
        service = OfferLLMAnalysisService(db)
        with pytest.raises(ValueError, match="not found"):
            await service.analyze_offer(uuid.uuid4())


# ---- ProfileMatchingService ------------------------------------------------

@pytest.mark.asyncio
async def test_match_offer_success():
    offer = _make_offer()
    profile = _make_profile()
    db = MagicMock()

    mock_match_repo = MagicMock()
    captured = {}

    def fake_upsert(match):
        captured["match"] = match
        match.match_status = "DONE"
        return match

    mock_match_repo.upsert = fake_upsert

    llm_response = {
        "match_score": 82,
        "strengths": ["Python expertise", "ML background"],
        "gaps": ["No Spark experience"],
        "recommendation": "Strong candidate, apply confidently.",
    }

    with patch("app.services.profile_matching_service.OfferRepository") as MockOffer, \
         patch("app.services.profile_matching_service.CandidateProfileRepository") as MockProfile, \
         patch("app.services.profile_matching_service.ProfileMatchLLMRepository") as MockMatch, \
         patch("app.services.profile_matching_service.call_llm_json", AsyncMock(return_value=llm_response)):

        MockOffer.return_value.get_by_id.return_value = offer
        MockProfile.return_value.get_default.return_value = profile
        MockMatch.return_value = mock_match_repo

        service = ProfileMatchingService(db)
        result = await service.match_offer(offer.id)

    assert captured["match"].match_score == 82.0
    assert captured["match"].strengths == ["Python expertise", "ML background"]
    assert captured["match"].match_status == "DONE"


@pytest.mark.asyncio
async def test_match_offer_no_profile_raises():
    offer = _make_offer()
    db = MagicMock()
    with patch("app.services.profile_matching_service.OfferRepository") as MockOffer, \
         patch("app.services.profile_matching_service.CandidateProfileRepository") as MockProfile:
        MockOffer.return_value.get_by_id.return_value = offer
        MockProfile.return_value.get_default.return_value = None

        service = ProfileMatchingService(db)
        with pytest.raises(ValueError, match="No candidate profile"):
            await service.match_offer(offer.id)


@pytest.mark.asyncio
async def test_match_offer_clamps_score():
    offer = _make_offer()
    profile = _make_profile()
    db = MagicMock()

    mock_match_repo = MagicMock()
    captured = {}

    def fake_upsert(match):
        captured["match"] = match
        return match

    mock_match_repo.upsert = fake_upsert

    llm_response = {"match_score": 150, "strengths": [], "gaps": [], "recommendation": ""}

    with patch("app.services.profile_matching_service.OfferRepository") as MockOffer, \
         patch("app.services.profile_matching_service.CandidateProfileRepository") as MockProfile, \
         patch("app.services.profile_matching_service.ProfileMatchLLMRepository") as MockMatch, \
         patch("app.services.profile_matching_service.call_llm_json", AsyncMock(return_value=llm_response)):

        MockOffer.return_value.get_by_id.return_value = offer
        MockProfile.return_value.get_default.return_value = profile
        MockMatch.return_value = mock_match_repo

        service = ProfileMatchingService(db)
        await service.match_offer(offer.id)

    # Score should be clamped to 100
    assert captured["match"].match_score == 100.0
