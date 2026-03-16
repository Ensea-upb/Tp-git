import hashlib
import re
import uuid

from rapidfuzz import fuzz

from app.domain.dto.deduplication_decision import DeduplicationDecision
from app.domain.dto.normalized_offer_payload import NormalizedOfferPayload
from app.domain.dto.raw_offer_payload import RawOfferPayload
from app.domain.text_normalizer import normalize_city, normalize_company, normalize_title
from app.repositories.offer_raw_repository import OfferRawRepository
from app.repositories.offer_repository import OfferRepository
from app.repositories.source_repository import SourceRepository

# Seuil de similarité fuzzy pour le titre de poste (L5)
_FUZZY_TITLE_THRESHOLD = 85.0


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
    Déduplication en cascade sur 5 niveaux :
      L1 — URL exacte              : offers.offer_url
      L2 — Source + ID ext.        : offers_raw.(source_id, external_offer_id)
      L3 — Checksum SHA-256        : offers.checksum (contenu exact)
      L4 — Hash sémantique inter-sources : offers.semantic_hash
               hash(normalize(titre) | normalize(société) | normalize(ville))
               Détecte la même offre publiée sur plusieurs jobboards.
      L5 — Similarité fuzzy titre  : rapidfuzz.fuzz.token_sort_ratio > 85
               même société (normalisée, correspondance exacte) + titre similaire
               Détecte les variantes légèrement reformulées du même poste.

    Note L4/L5 : efficaces uniquement si offers.semantic_hash est peuplé lors de
    l'ingestion (OfferIngestionService — Sprint 8).
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

        # ── Niveau 5 : Similarité fuzzy titre + société identique ─────────
        company_normalized = normalize_company(normalized.company_name or "")
        if company_normalized:
            candidates = self.offer_repo.get_candidates_for_fuzzy_match(company_normalized)
            title_normalized = normalize_title(normalized.normalized_title)
            for candidate in candidates:
                candidate_title = normalize_title(candidate.normalized_title or "")
                similarity = fuzz.token_sort_ratio(title_normalized, candidate_title)
                if similarity >= _FUZZY_TITLE_THRESHOLD:
                    return DeduplicationDecision(
                        decision="duplicate",
                        reason=f"L5:fuzzy_title_match(score={similarity:.0f})",
                        confidence=similarity / 100.0,
                        matched_offer_id=candidate.id,
                    )

        # ── Aucun doublon ──────────────────────────────────────────────────
        return DeduplicationDecision(
            decision="create",
            reason="no_match",
            confidence=1.0,
            matched_offer_id=None,
        )
