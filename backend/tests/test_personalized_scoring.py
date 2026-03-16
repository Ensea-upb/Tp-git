"""Tests unitaires du service de scoring personnalisé."""

import uuid

import pytest

from app.domain.enums.work_mode import WorkMode
from app.infrastructure.db.models.offer import Offer
from app.infrastructure.db.models.user_preference import DEFAULT_PROFILE_ID, UserPreference
from app.services.personalized_offer_scoring_service import PersonalizedOfferScoringService


@pytest.fixture
def scorer() -> PersonalizedOfferScoringService:
    return PersonalizedOfferScoringService()


def _offer(**kwargs) -> Offer:
    defaults = dict(
        id=uuid.uuid4(),
        normalized_title="Stage développeur",
        normalized_description="Description générique.",
        current_state="NORMALIZED",
        is_active=True,
        global_score=50.0,
    )
    return Offer(**{**defaults, **kwargs})


def _prefs(**kwargs) -> UserPreference:
    defaults = dict(
        id=DEFAULT_PROFILE_ID,
        preferred_contract_types=["Stage"],
        preferred_work_modes=["REMOTE"],
        preferred_locations=["Paris"],
        preferred_keywords=["python"],
        preferred_domains=["data"],
        exclude_keywords=["Java EE"],
        minimum_duration_months=4,
    )
    return UserPreference(**{**defaults, **kwargs})


# ------------------------------------------------------------------ #
# Structure                                                            #
# ------------------------------------------------------------------ #

class TestOutputShape:
    def test_sets_personalized_score(self, scorer):
        offer = _offer()
        scorer.score(offer, _prefs())
        assert offer.personalized_score is not None
        assert 0 <= offer.personalized_score <= 100

    def test_sets_personalized_justification(self, scorer):
        offer = _offer()
        scorer.score(offer, _prefs())
        j = offer.personalized_justification
        assert j is not None
        assert "base_score" in j
        assert "delta" in j
        assert "score" in j
        assert "détails" in j

    def test_no_prefs_no_delta(self, scorer):
        """Sans aucune préférence renseignée, le score = global_score."""
        offer = _offer(global_score=65.0)
        prefs = UserPreference(id=DEFAULT_PROFILE_ID)
        scorer.score(offer, prefs)
        assert offer.personalized_score == 65.0


# ------------------------------------------------------------------ #
# Contract type                                                        #
# ------------------------------------------------------------------ #

class TestContractBonus:
    def test_matching_contract_bonus(self, scorer):
        offer_match = _offer(contract_type="Stage")
        offer_no_match = _offer(contract_type="CDI")
        prefs = _prefs(preferred_contract_types=["Stage"])
        scorer.score(offer_match, prefs)
        scorer.score(offer_no_match, prefs)
        assert offer_match.personalized_score > offer_no_match.personalized_score

    def test_no_contract_no_bonus(self, scorer):
        offer = _offer(contract_type=None)
        prefs = _prefs(preferred_contract_types=["Stage"])
        scorer.score(offer, prefs)
        # Aucun bonus, mais pas d'erreur
        assert offer.personalized_score is not None


# ------------------------------------------------------------------ #
# Work mode                                                            #
# ------------------------------------------------------------------ #

class TestWorkModeBonus:
    def test_matching_work_mode_bonus(self, scorer):
        offer_remote = _offer(work_mode=WorkMode.REMOTE)
        offer_onsite = _offer(work_mode=WorkMode.ONSITE)
        prefs = _prefs(preferred_work_modes=["REMOTE"])
        scorer.score(offer_remote, prefs)
        scorer.score(offer_onsite, prefs)
        assert offer_remote.personalized_score > offer_onsite.personalized_score


# ------------------------------------------------------------------ #
# Location                                                             #
# ------------------------------------------------------------------ #

class TestLocationBonus:
    def test_location_match(self, scorer):
        offer_paris = _offer(location_text="Paris 14e")
        offer_lyon = _offer(location_text="Lyon")
        prefs = _prefs(preferred_locations=["Paris"])
        scorer.score(offer_paris, prefs)
        scorer.score(offer_lyon, prefs)
        assert offer_paris.personalized_score > offer_lyon.personalized_score

    def test_case_insensitive_location(self, scorer):
        offer = _offer(location_text="PARIS")
        prefs = _prefs(preferred_locations=["paris"])
        scorer.score(offer, prefs)
        j = offer.personalized_justification
        assert any("Paris" in d or "paris" in d.lower() for d in j["détails"])


# ------------------------------------------------------------------ #
# Keywords                                                             #
# ------------------------------------------------------------------ #

class TestKeywordBonus:
    def test_keyword_found_in_title(self, scorer):
        offer = _offer(normalized_title="Stage Python Data Scientist")
        prefs = _prefs(preferred_keywords=["python"])
        scorer.score(offer, prefs)
        j = offer.personalized_justification
        assert j["delta"] >= 5

    def test_multiple_keywords_capped_at_15(self, scorer):
        offer = _offer(
            normalized_title="Stage Python Data",
            normalized_description="Machine learning, NLP, analytics",
        )
        prefs = _prefs(preferred_keywords=["python", "data", "machine", "nlp", "analytics"])
        scorer.score(offer, prefs)
        # Max +15 sur les keywords
        kw_delta = sum(
            5 for d in offer.personalized_justification["détails"] if "mots-clés" in d
        )
        assert kw_delta <= 15


# ------------------------------------------------------------------ #
# Domaine tags                                                         #
# ------------------------------------------------------------------ #

class TestDomainBonus:
    def test_matching_domain_tag(self, scorer):
        offer = _offer(tags=["data", "ml"])
        prefs = _prefs(preferred_domains=["data", "ml"])
        scorer.score(offer, prefs)
        assert offer.personalized_score >= 50.0 + 20  # +10 data, +10 ml


# ------------------------------------------------------------------ #
# Mots-clés exclus                                                     #
# ------------------------------------------------------------------ #

class TestExcludeKeywords:
    def test_excluded_keyword_penalizes(self, scorer):
        offer_clean = _offer(normalized_description="Stage Python moderne.")
        offer_excluded = _offer(normalized_description="Stage Java EE legacy.")
        prefs = _prefs(exclude_keywords=["Java EE"])
        scorer.score(offer_clean, prefs)
        scorer.score(offer_excluded, prefs)
        assert offer_excluded.personalized_score < offer_clean.personalized_score

    def test_malus_capped_at_minus_30(self, scorer):
        offer = _offer(
            normalized_description="Java EE legacy Cobol COBOL legacy2 old"
        )
        prefs = _prefs(exclude_keywords=["Java EE", "COBOL", "legacy2"])
        scorer.score(offer, prefs)
        # delta ne doit pas aller en dessous de -30 sur les exclusions
        excl_delta = 0
        for d in offer.personalized_justification["détails"]:
            if "exclus" in d:
                excl_delta = int(d.split()[0])
        assert excl_delta >= -30


# ------------------------------------------------------------------ #
# Durée minimale                                                       #
# ------------------------------------------------------------------ #

class TestDurationMalus:
    def test_short_duration_penalized(self, scorer):
        offer_ok = _offer(duration_months=6)
        offer_short = _offer(duration_months=2)
        prefs = _prefs(minimum_duration_months=4)
        scorer.score(offer_ok, prefs)
        scorer.score(offer_short, prefs)
        assert offer_short.personalized_score < offer_ok.personalized_score

    def test_exact_minimum_no_malus(self, scorer):
        offer = _offer(duration_months=4)
        prefs = _prefs(minimum_duration_months=4)
        base_offer = _offer(duration_months=4)
        scorer.score(offer, prefs)
        scorer.score(base_offer, _prefs(minimum_duration_months=None))
        # Durée exacte = pas de malus durée
        duration_details = [d for d in offer.personalized_justification["détails"] if "durée" in d]
        assert len(duration_details) == 0


# ------------------------------------------------------------------ #
# Bornes 0–100                                                         #
# ------------------------------------------------------------------ #

class TestClamp:
    def test_cannot_exceed_100(self, scorer):
        offer = _offer(
            global_score=90.0,
            contract_type="Stage",
            work_mode=WorkMode.REMOTE,
            location_text="Paris",
            tags=["data", "ml", "ai"],
            duration_months=6,
        )
        prefs = _prefs(
            preferred_contract_types=["Stage"],
            preferred_work_modes=["REMOTE"],
            preferred_locations=["Paris"],
            preferred_domains=["data", "ml", "ai"],
        )
        scorer.score(offer, prefs)
        assert offer.personalized_score <= 100

    def test_cannot_go_below_0(self, scorer):
        offer = _offer(
            global_score=5.0,
            normalized_description="Java EE legacy PHP jQuery",
        )
        prefs = _prefs(exclude_keywords=["Java EE", "legacy", "PHP"])
        scorer.score(offer, prefs)
        assert offer.personalized_score >= 0
