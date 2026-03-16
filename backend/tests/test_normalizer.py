"""Tests du service de normalisation déterministe."""

import pytest

from app.domain.dto.raw_offer_payload import RawOfferPayload
from app.domain.enums.work_mode import WorkMode
from app.services.offer_normalizer import OfferNormalizer


@pytest.fixture
def normalizer() -> OfferNormalizer:
    return OfferNormalizer()


def _make_payload(**kwargs) -> RawOfferPayload:
    defaults = dict(
        source_name="test",
        source_type="test",
        raw_title="Stage développeur Python",
        raw_content="Poste en CDI à Paris.",
        raw_company_name="Acme Corp",
        raw_location="Paris",
    )
    return RawOfferPayload(**{**defaults, **kwargs})


# ------------------------------------------------------------------ #
# Titre                                                                #
# ------------------------------------------------------------------ #

class TestSmartTitle:
    def test_basic_capitalisation(self, normalizer):
        p = _make_payload(raw_title="stage développeur python")
        r = normalizer.normalize(p)
        assert r.normalized_title == "Stage Développeur Python"

    def test_acronym_preserved(self, normalizer):
        p = _make_payload(raw_title="STAGE DÉVELOPPEUR FULL-STACK H/F")
        r = normalizer.normalize(p)
        # Acronymes entiers (STAGE, etc.) ne sont que des mots UPPER ≥ 2 alpha
        # "STAGE" est tout en majuscule → préservé
        assert "STAGE" in r.normalized_title

    def test_html_stripped(self, normalizer):
        p = _make_payload(raw_title="<b>Stage</b> <i>Python</i>")
        r = normalizer.normalize(p)
        assert "<" not in r.normalized_title
        assert "Stage" in r.normalized_title

    def test_extra_whitespace_cleaned(self, normalizer):
        p = _make_payload(raw_title="  Stage   Python  ")
        r = normalizer.normalize(p)
        assert "  " not in r.normalized_title


# ------------------------------------------------------------------ #
# Description                                                          #
# ------------------------------------------------------------------ #

class TestDescription:
    def test_html_stripped(self, normalizer):
        html = "<p>Mission <strong>principale</strong> : développer des APIs.</p>"
        p = _make_payload(raw_content=html)
        r = normalizer.normalize(p)
        assert "<p>" not in r.normalized_description
        assert "Mission" in r.normalized_description
        assert "principale" in r.normalized_description

    def test_empty_description(self, normalizer):
        p = _make_payload(raw_content="")
        r = normalizer.normalize(p)
        assert r.normalized_description == ""


# ------------------------------------------------------------------ #
# Work Mode                                                            #
# ------------------------------------------------------------------ #

class TestWorkMode:
    @pytest.mark.parametrize("text,expected", [
        ("Poste en télétravail complet", WorkMode.REMOTE),
        ("Full remote possible", WorkMode.REMOTE),
        ("Distanciel autorisé", WorkMode.REMOTE),
        ("Hybride 3j/2j", WorkMode.HYBRID),
        ("Travail hybride flexible", WorkMode.HYBRID),
        ("Présentiel uniquement", WorkMode.ONSITE),
        ("Bureau à Paris", WorkMode.ONSITE),
    ])
    def test_detection(self, normalizer, text, expected):
        p = _make_payload(raw_content=text)
        r = normalizer.normalize(p)
        assert r.work_mode == expected


# ------------------------------------------------------------------ #
# Contract Type                                                        #
# ------------------------------------------------------------------ #

class TestContractType:
    @pytest.mark.parametrize("text,expected", [
        ("Stage de 6 mois", "Stage"),
        ("Internship 3 months", "Stage"),
        ("Alternance en M2", "Alternance"),
        ("Contrat en CDI", "CDI"),
        ("CDD de 12 mois", "CDD"),
        ("Mission freelance", "Freelance"),
    ])
    def test_detection(self, normalizer, text, expected):
        p = _make_payload(raw_content=text)
        r = normalizer.normalize(p)
        assert r.contract_type == expected

    def test_no_match_returns_none(self, normalizer):
        p = _make_payload(raw_content="Description sans type de contrat particulier.")
        r = normalizer.normalize(p)
        assert r.contract_type is None


# ------------------------------------------------------------------ #
# Duration                                                             #
# ------------------------------------------------------------------ #

class TestDuration:
    @pytest.mark.parametrize("text,expected", [
        ("Stage de 6 mois", 6),
        ("Durée : 12 months", 12),
        ("3 mois renouvelable", 3),
    ])
    def test_extraction(self, normalizer, text, expected):
        p = _make_payload(raw_content=text)
        r = normalizer.normalize(p)
        assert r.duration_months == expected

    def test_no_duration(self, normalizer):
        p = _make_payload(raw_content="Poste en CDI permanent.")
        r = normalizer.normalize(p)
        assert r.duration_months is None


# ------------------------------------------------------------------ #
# Education Level                                                      #
# ------------------------------------------------------------------ #

class TestEducationLevel:
    @pytest.mark.parametrize("text,expected", [
        ("Niveau Bac+5 requis", "Bac+5"),
        ("Master en informatique", "Bac+5"),
        ("Ingénieur diplômé", "Bac+5"),
        ("Bac+3 minimum", "Bac+3"),
        ("Licence en gestion", "Bac+3"),
        ("BTS ou DUT", "Bac+2"),
    ])
    def test_detection(self, normalizer, text, expected):
        p = _make_payload(raw_content=text)
        r = normalizer.normalize(p)
        assert r.education_level == expected


# ------------------------------------------------------------------ #
# Checksum                                                             #
# ------------------------------------------------------------------ #

class TestChecksum:
    def test_checksum_is_64_chars(self, normalizer):
        p = _make_payload()
        r = normalizer.normalize(p)
        assert len(r.checksum) == 64

    def test_same_content_same_checksum(self, normalizer):
        p1 = _make_payload(raw_title="Stage Python", raw_content="Description A")
        p2 = _make_payload(raw_title="Stage Python", raw_content="Description A")
        r1 = normalizer.normalize(p1)
        r2 = normalizer.normalize(p2)
        assert r1.checksum == r2.checksum

    def test_different_content_different_checksum(self, normalizer):
        p1 = _make_payload(raw_title="Stage Python", raw_content="Description A")
        p2 = _make_payload(raw_title="Stage Java", raw_content="Description B")
        r1 = normalizer.normalize(p1)
        r2 = normalizer.normalize(p2)
        assert r1.checksum != r2.checksum


# ------------------------------------------------------------------ #
# Company name fallback                                                #
# ------------------------------------------------------------------ #

class TestCompanyName:
    def test_unknown_company_fallback(self, normalizer):
        p = _make_payload(raw_company_name=None)
        r = normalizer.normalize(p)
        assert r.company_name == "Entreprise inconnue"

    def test_company_whitespace_cleaned(self, normalizer):
        p = _make_payload(raw_company_name="  Acme   Corp  ")
        r = normalizer.normalize(p)
        assert r.company_name == "Acme Corp"
