"""Tests unitaires du service de scoring déterministe."""

import uuid

import pytest

from app.domain.dto.normalized_offer_payload import NormalizedOfferPayload
from app.domain.enums.work_mode import WorkMode
from app.infrastructure.db.models.offer import Offer
from app.services.offer_scoring_service import OfferScoringService


@pytest.fixture
def scorer() -> OfferScoringService:
    return OfferScoringService()


def _offer() -> Offer:
    return Offer(
        id=uuid.uuid4(),
        normalized_title="Stage développeur",
        current_state="NORMALIZED",
        is_active=True,
    )


def _normalized(**kwargs) -> NormalizedOfferPayload:
    defaults = dict(
        normalized_title="Stage développeur",
        normalized_description="Description générique.",
        company_name="Corp",
        checksum="x" * 64,
    )
    return NormalizedOfferPayload(**{**defaults, **kwargs})


# ------------------------------------------------------------------ #
# Structure des sorties                                                #
# ------------------------------------------------------------------ #

class TestOutputShape:
    def test_sets_global_score(self, scorer):
        offer = _offer()
        scorer.score(offer, _normalized())
        assert offer.global_score is not None
        assert 0 <= offer.global_score <= 100

    def test_sets_score_justification(self, scorer):
        offer = _offer()
        scorer.score(offer, _normalized())
        assert offer.score_justification is not None
        assert "score" in offer.score_justification
        assert "détails" in offer.score_justification

    def test_score_is_float(self, scorer):
        offer = _offer()
        scorer.score(offer, _normalized())
        assert isinstance(offer.global_score, float)


# ------------------------------------------------------------------ #
# Contrat — bonus stage                                                #
# ------------------------------------------------------------------ #

class TestContractBonus:
    def test_stage_gives_25_points(self, scorer):
        offer = _offer()
        n = _normalized(contract_type="Stage")
        scorer.score(offer, n)
        assert offer.global_score >= 25

    def test_alternance_gives_20_points(self, scorer):
        offer = _offer()
        n = _normalized(contract_type="Alternance")
        scorer.score(offer, n)
        assert offer.global_score >= 20

    def test_cdi_penalizes(self, scorer):
        offer_cdi = _offer()
        offer_stage = _offer()
        n_cdi = _normalized(contract_type="CDI")
        n_stage = _normalized(contract_type="Stage")
        scorer.score(offer_cdi, n_cdi)
        scorer.score(offer_stage, n_stage)
        assert offer_cdi.global_score < offer_stage.global_score

    def test_cdi_senior_penalizes_more(self, scorer):
        offer_cdi = _offer()
        offer_cdi_senior = _offer()
        n_cdi = _normalized(
            contract_type="CDI",
            normalized_description="Poste CDI pour profil confirmé.",
        )
        n_cdi_senior = _normalized(
            contract_type="CDI",
            normalized_description="Poste CDI senior lead expérimenté.",
        )
        scorer.score(offer_cdi, n_cdi)
        scorer.score(offer_cdi_senior, n_cdi_senior)
        assert offer_cdi_senior.global_score < offer_cdi.global_score


# ------------------------------------------------------------------ #
# Domaines — tags                                                      #
# ------------------------------------------------------------------ #

class TestDomainTags:
    @pytest.mark.parametrize("text,expected_tag,min_bonus", [
        ("Poste de data scientist confirmé", "data", 20),
        ("Développement machine learning", "ml", 15),
        ("Projet AI NLP en entreprise", "ai", 10),
        ("Analyse data viz power bi", "analytics", 10),
        ("Modèles économétriques avancés", "econometrics", 10),
    ])
    def test_tag_detected_and_score_increased(self, scorer, text, expected_tag, min_bonus):
        offer_with = _offer()
        offer_without = _offer()
        n_with = _normalized(normalized_description=text)
        n_without = _normalized(normalized_description="Description sans mots-clés.")
        scorer.score(offer_with, n_with)
        scorer.score(offer_without, n_without)
        assert expected_tag in (offer_with.tags or [])
        assert offer_with.global_score >= offer_without.global_score + min_bonus

    def test_no_tags_when_no_keywords(self, scorer):
        offer = _offer()
        scorer.score(offer, _normalized(normalized_description="Développement web classique."))
        assert not offer.tags

    def test_multiple_tags_accumulated(self, scorer):
        offer = _offer()
        n = _normalized(
            normalized_description="data scientist machine learning NLP"
        )
        scorer.score(offer, n)
        assert "data" in (offer.tags or [])
        assert "ml" in (offer.tags or [])
        assert "ai" in (offer.tags or [])


# ------------------------------------------------------------------ #
# Mode de travail                                                      #
# ------------------------------------------------------------------ #

class TestWorkModeBonus:
    def test_remote_bonus(self, scorer):
        offer_remote = _offer()
        offer_onsite = _offer()
        scorer.score(offer_remote, _normalized(work_mode=WorkMode.REMOTE))
        scorer.score(offer_onsite, _normalized(work_mode=WorkMode.ONSITE))
        assert offer_remote.global_score > offer_onsite.global_score

    def test_hybrid_bonus_less_than_remote(self, scorer):
        offer_hybrid = _offer()
        offer_remote = _offer()
        scorer.score(offer_hybrid, _normalized(work_mode=WorkMode.HYBRID))
        scorer.score(offer_remote, _normalized(work_mode=WorkMode.REMOTE))
        assert offer_hybrid.global_score < offer_remote.global_score


# ------------------------------------------------------------------ #
# Localisation                                                         #
# ------------------------------------------------------------------ #

class TestLocationBonus:
    @pytest.mark.parametrize("location", ["Paris", "Île-de-France", "92 Hauts-de-Seine", "75013"])
    def test_idf_bonus(self, scorer, location):
        offer_idf = _offer()
        offer_other = _offer()
        scorer.score(offer_idf, _normalized(location_text=location))
        scorer.score(offer_other, _normalized(location_text="Lyon"))
        assert offer_idf.global_score > offer_other.global_score


# ------------------------------------------------------------------ #
# Durée                                                                #
# ------------------------------------------------------------------ #

class TestDurationBonus:
    def test_6_month_bonus(self, scorer):
        offer_long = _offer()
        offer_short = _offer()
        scorer.score(offer_long, _normalized(duration_months=6))
        scorer.score(offer_short, _normalized(duration_months=3))
        assert offer_long.global_score > offer_short.global_score

    def test_5_months_no_bonus(self, scorer):
        offer_5m = _offer()
        offer_none = _offer()
        scorer.score(offer_5m, _normalized(duration_months=5))
        scorer.score(offer_none, _normalized(duration_months=None))
        assert offer_5m.global_score == offer_none.global_score


# ------------------------------------------------------------------ #
# Bornes 0–100                                                         #
# ------------------------------------------------------------------ #

class TestScoreClamp:
    def test_score_not_above_100(self, scorer):
        offer = _offer()
        n = _normalized(
            normalized_title="Data Scientist Machine Learning AI Stage",
            normalized_description=(
                "Stage 6 mois data scientist machine learning deep learning AI NLP "
                "analytics econometrics Paris IDF télétravail"
            ),
            contract_type="Stage",
            work_mode=WorkMode.REMOTE,
            location_text="Paris",
            duration_months=6,
        )
        scorer.score(offer, n)
        assert offer.global_score <= 100

    def test_score_not_below_0(self, scorer):
        offer = _offer()
        n = _normalized(
            contract_type="CDI",
            normalized_description="Directeur senior confirmé expérimenté lead manager.",
        )
        scorer.score(offer, n)
        assert offer.global_score >= 0
