import hashlib
import re
import uuid

from app.domain.dto.deduplication_decision import DeduplicationDecision
from app.domain.dto.normalized_offer_payload import NormalizedOfferPayload
from app.domain.dto.raw_offer_payload import RawOfferPayload
from app.repositories.offer_raw_repository import OfferRawRepository
from app.repositories.offer_repository import OfferRepository
from app.repositories.source_repository import SourceRepository


def _normalize_text(text: str) -> str:
    """Minuscule, retire ponctuation, collapse espaces — pour comparaison sémantique."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def compute_cross_source_hash(title: str, company: str, city: str) -> str:
    """
    Hash déterministe pour déduplication inter-sources.
    Stratégie : sha256(normalize(title) | normalize(company) | normalize(city))
    """
    key = "|".join([_normalize_text(title), _normalize_text(company), _normalize_text(city)])
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


class OfferDeduplicator:
    """
    Déduplication en cascade sur 4 niveaux :
      L1 — URL exacte              : offers.offer_url
      L2 — Source + ID ext.        : offers_raw.(source_id, external_offer_id)
      L3 — Checksum SHA-256        : offers.checksum (contenu exact)
      L4 — Hash sémantique inter-sources : offers.semantic_hash
               hash(normalize(titre) | normalize(société) | normalize(ville))
               Détecte la même offre publiée sur plusieurs jobboards.

    Note L4 : nécessite que offers.semantic_hash soit peuplé lors de l'ingestion.
    La colonne existe sur le modèle Offer ; l'écriture est déléguée à OfferIngestionService
    via NormalizedOfferPayload.semantic_hash (Sprint 8).
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

        # ── Niveau 3 : Checksum SHA-256 (contenu exact) ────────────────────
        existing_by_checksum = self.offer_repo.get_by_checksum(normalized.checksum)
        if existing_by_checksum:
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

        # ── Niveau 4 : Hash sémantique inter-sources ──────────────────────
        city = normalized.location_text or raw.raw_location or ""
        semantic_hash = compute_cross_source_hash(
            normalized.normalized_title,
            normalized.company_name,
            city,
        )
        existing_by_semantic = self.offer_repo.get_by_semantic_hash(semantic_hash)
        if existing_by_semantic:
            return DeduplicationDecision(
                decision="duplicate",
                reason="L4:cross_source_semantic_match",
                confidence=0.85,
                matched_offer_id=existing_by_semantic.id,
            )

        # ── Aucun doublon ──────────────────────────────────────────────────
        return DeduplicationDecision(
            decision="create",
            reason="no_match",
            confidence=1.0,
            matched_offer_id=None,
        )
