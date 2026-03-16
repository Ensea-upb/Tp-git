import uuid

from app.domain.dto.deduplication_decision import DeduplicationDecision
from app.domain.dto.normalized_offer_payload import NormalizedOfferPayload
from app.domain.dto.raw_offer_payload import RawOfferPayload
from app.repositories.offer_raw_repository import OfferRawRepository
from app.repositories.offer_repository import OfferRepository
from app.repositories.source_repository import SourceRepository


class OfferDeduplicator:
    """
    Déduplication en cascade sur 3 niveaux :
      L1 — URL exacte         : offers.offer_url
      L2 — Source + ID ext.   : offers_raw.(source_id, external_offer_id)
      L3 — Checksum SHA-256   : offers.checksum
    """

    def __init__(
        self,
        offer_repo: OfferRepository,
        offer_raw_repo: OfferRawRepository,
        source_repo: SourceRepository,
    ) -> None:
        self.offer_repo = offer_repo
        self.offer_raw_repo = offer_raw_repo
        self.source_repo = source_repo

    def deduplicate(
        self,
        raw: RawOfferPayload,
        normalized: NormalizedOfferPayload,
        source_id: uuid.UUID,
    ) -> DeduplicationDecision:
        # ── Niveau 1 : URL exacte ──────────────────────────────────────────
        if raw.offer_url:
            existing = self.offer_repo.get_by_url(raw.offer_url)
            if existing:
                return DeduplicationDecision(
                    decision="duplicate",
                    reason="L1:url_match",
                    confidence=1.0,
                    matched_offer_id=existing.id,
                )

        # ── Niveau 2 : Source + identifiant externe ────────────────────────
        if raw.external_offer_id:
            existing_raw = self.offer_raw_repo.get_by_source_and_external_id(
                source_id, raw.external_offer_id
            )
            if existing_raw and existing_raw.normalized_offer:
                return DeduplicationDecision(
                    decision="duplicate",
                    reason="L2:source_external_id_match",
                    confidence=1.0,
                    matched_offer_id=existing_raw.normalized_offer.id,
                )

        # ── Niveau 3 : Checksum SHA-256 ────────────────────────────────────
        existing_by_checksum = self.offer_repo.get_by_checksum(normalized.checksum)
        if existing_by_checksum:
            # Même contenu mais URL différente → offre multi-source
            if raw.offer_url and existing_by_checksum.offer_url != raw.offer_url:
                return DeduplicationDecision(
                    decision="update",
                    reason="L3:checksum_match_different_url",
                    confidence=0.95,
                    matched_offer_id=existing_by_checksum.id,
                )
            return DeduplicationDecision(
                decision="duplicate",
                reason="L3:checksum_match",
                confidence=1.0,
                matched_offer_id=existing_by_checksum.id,
            )

        # ── Aucun doublon ──────────────────────────────────────────────────
        return DeduplicationDecision(
            decision="create",
            reason="no_match",
            confidence=1.0,
            matched_offer_id=None,
        )
