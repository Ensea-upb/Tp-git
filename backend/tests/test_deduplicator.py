"""Tests du service de déduplication en cascade."""

import uuid

import pytest

from app.domain.dto.deduplication_decision import DeduplicationDecision
from app.domain.dto.normalized_offer_payload import NormalizedOfferPayload
from app.domain.dto.raw_offer_payload import RawOfferPayload
from app.domain.enums.offer_state import OfferState
from app.domain.enums.work_mode import WorkMode
from app.infrastructure.db.models.company import Company
from app.infrastructure.db.models.offer import Offer
from app.infrastructure.db.models.offer_raw import OfferRaw
from app.infrastructure.db.models.source import Source
from app.repositories.offer_raw_repository import OfferRawRepository
from app.repositories.offer_repository import OfferRepository
from app.repositories.source_repository import SourceRepository
from app.services.offer_deduplicator import OfferDeduplicator


# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #

@pytest.fixture
def source(db) -> Source:
    s = Source(
        id=uuid.uuid4(),
        name="Dedup Test Source",
        source_type="test",
        is_active=True,
        check_frequency_hours=3,
    )
    db.add(s)
    db.flush()
    return s


@pytest.fixture
def company(db) -> Company:
    c = Company(
        id=uuid.uuid4(),
        name="Dedup Corp",
        company_status="neutre",
    )
    db.add(c)
    db.flush()
    return c


@pytest.fixture
def deduplicator(db) -> OfferDeduplicator:
    return OfferDeduplicator(
        offer_repo=OfferRepository(db),
        offer_raw_repo=OfferRawRepository(db),
        source_repo=SourceRepository(db),
    )


def _raw(
    offer_url: str | None = None,
    external_id: str | None = None,
) -> RawOfferPayload:
    return RawOfferPayload(
        source_name="test",
        source_type="test",
        raw_title="Stage Python",
        raw_content="Description",
        offer_url=offer_url,
        external_offer_id=external_id,
    )


def _normalized(checksum: str = "abc123") -> NormalizedOfferPayload:
    return NormalizedOfferPayload(
        normalized_title="Stage Python",
        normalized_description="Description",
        company_name="Dedup Corp",
        checksum=checksum,
    )


# ------------------------------------------------------------------ #
# Tests                                                                #
# ------------------------------------------------------------------ #

class TestLevel1UrlMatch:
    def test_duplicate_when_url_matches(self, db, source, company, deduplicator):
        existing_offer = Offer(
            id=uuid.uuid4(),
            normalized_title="Stage Python",
            company_id=company.id,
            primary_source_id=source.id,
            offer_url="https://example.com/stage/1",
            current_state=OfferState.NORMALIZED,
            is_active=True,
        )
        db.add(existing_offer)
        db.flush()

        raw = _raw(offer_url="https://example.com/stage/1")
        decision = deduplicator.deduplicate(raw, _normalized(), source.id)

        assert decision.decision == "duplicate"
        assert decision.reason == "L1:url_match"
        assert decision.matched_offer_id == existing_offer.id
        assert decision.confidence == 1.0

    def test_no_duplicate_when_url_absent(self, db, source, deduplicator):
        raw = _raw(offer_url=None)
        decision = deduplicator.deduplicate(raw, _normalized("unique_hash_1"), source.id)
        assert decision.decision == "create"


class TestLevel2ExternalIdMatch:
    def test_duplicate_when_source_external_id_matches(self, db, source, company, deduplicator):
        # Créer une OfferRaw + Offer liés
        offer_raw = OfferRaw(
            id=uuid.uuid4(),
            source_id=source.id,
            external_offer_id="EXT-999",
            offer_url="https://example.com/stage/999",
            raw_title="Stage Python",
            raw_content="Desc",
            parsing_status="PARSED",
        )
        db.add(offer_raw)
        db.flush()

        existing_offer = Offer(
            id=uuid.uuid4(),
            normalized_title="Stage Python",
            company_id=company.id,
            primary_source_id=source.id,
            raw_offer_id=offer_raw.id,
            offer_url="https://example.com/stage/999",
            current_state=OfferState.NORMALIZED,
            is_active=True,
        )
        db.add(existing_offer)
        db.flush()

        # Requête avec même source + external_id, mais URL différente
        raw = _raw(offer_url="https://other.com/stage/999", external_id="EXT-999")
        decision = deduplicator.deduplicate(raw, _normalized("unique_hash_2"), source.id)

        assert decision.decision == "duplicate"
        assert decision.reason == "L2:source_external_id_match"
        assert decision.matched_offer_id == existing_offer.id


class TestLevel3ChecksumMatch:
    def test_duplicate_when_same_checksum_same_url(self, db, source, company, deduplicator):
        checksum = "a" * 64
        existing_offer = Offer(
            id=uuid.uuid4(),
            normalized_title="Stage Python",
            company_id=company.id,
            primary_source_id=source.id,
            offer_url="https://example.com/stage/2",
            checksum=checksum,
            current_state=OfferState.NORMALIZED,
            is_active=True,
        )
        db.add(existing_offer)
        db.flush()

        raw = _raw(offer_url="https://example.com/stage/2", external_id=None)
        # L1 match → duplicate (avant même d'atteindre L3)
        decision = deduplicator.deduplicate(raw, _normalized(checksum), source.id)
        assert decision.decision == "duplicate"

    def test_update_when_same_checksum_different_url(self, db, source, company, deduplicator):
        checksum = "b" * 64
        existing_offer = Offer(
            id=uuid.uuid4(),
            normalized_title="Stage Python",
            company_id=company.id,
            primary_source_id=source.id,
            offer_url="https://source-a.com/stage/3",
            checksum=checksum,
            current_state=OfferState.NORMALIZED,
            is_active=True,
        )
        db.add(existing_offer)
        db.flush()

        raw = _raw(offer_url="https://source-b.com/stage/3", external_id=None)
        decision = deduplicator.deduplicate(raw, _normalized(checksum), source.id)

        assert decision.decision == "update"
        assert decision.reason == "L3:checksum_match_different_url"
        assert decision.matched_offer_id == existing_offer.id
        assert decision.confidence == 0.95


class TestNoMatch:
    def test_create_when_no_match(self, deduplicator, source):
        raw = _raw(
            offer_url=f"https://new.example.com/stage/{uuid.uuid4()}",
            external_id=f"NEW-{uuid.uuid4()}",
        )
        normalized = _normalized("c" * 64)
        decision = deduplicator.deduplicate(raw, normalized, source.id)

        assert decision.decision == "create"
        assert decision.matched_offer_id is None
        assert decision.confidence == 1.0
