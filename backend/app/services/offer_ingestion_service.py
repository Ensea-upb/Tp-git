"""
Service d'orchestration de l'ingestion des offres.

Pour chaque source active :
  1. Créer un IngestionRun en état RUNNING
  2. Récupérer le connecteur adapté
  3. connector.fetch() → list[RawOfferPayload]
  4. Pour chaque payload :
     a. Persister OfferRaw (status=PENDING)
     b. Normaliser → NormalizedOfferPayload
     c. Dédupliquer → DeduplicationDecision
     d. Scorer → global_score + tags
     e. create / update / duplicate selon décision
     f. Mettre à jour OfferRaw.parsing_status
  5. Finaliser IngestionRun avec le bilan
  6. commit()
  7. Retourner IngestionResult
"""

import logging
import time
import uuid

from sqlalchemy.orm import Session

from app.domain.dto.ingestion_result import IngestionResult
from app.domain.dto.raw_offer_payload import RawOfferPayload
from app.domain.enums.ingestion_status import IngestionStatus
from app.domain.enums.offer_state import OfferState
from app.infrastructure.db.models.offer import Offer
from app.infrastructure.db.models.offer_raw import OfferRaw
from app.repositories.company_repository import CompanyRepository
from app.repositories.ingestion_run_repository import IngestionRunRepository
from app.repositories.offer_raw_repository import OfferRawRepository
from app.repositories.offer_repository import OfferRepository
from app.repositories.source_repository import SourceRepository
from app.repositories.user_preference_repository import UserPreferenceRepository
from app.services.offer_deduplicator import OfferDeduplicator
from app.services.offer_normalizer import OfferNormalizer
from app.services.offer_scoring_service import OfferScoringService
from app.services.personalized_offer_scoring_service import PersonalizedOfferScoringService
from app.services.source_connector_manager import SourceConnectorManager

logger = logging.getLogger(__name__)


class OfferIngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.source_repo = SourceRepository(db)
        self.offer_repo = OfferRepository(db)
        self.offer_raw_repo = OfferRawRepository(db)
        self.company_repo = CompanyRepository(db)
        self.ingestion_run_repo = IngestionRunRepository(db)
        self.normalizer = OfferNormalizer()
        self.scorer = OfferScoringService()
        self.personalized_scorer = PersonalizedOfferScoringService()
        self.pref_repo = UserPreferenceRepository(db)
        self.deduplicator = OfferDeduplicator(
            offer_repo=self.offer_repo,
            offer_raw_repo=self.offer_raw_repo,
            source_repo=self.source_repo,
        )
        self.connector_manager = SourceConnectorManager()

    # ------------------------------------------------------------------ #
    # Points d'entrée                                                      #
    # ------------------------------------------------------------------ #

    def run_all(self) -> list[IngestionResult]:
        """Lance l'ingestion pour toutes les sources actives."""
        sources = self.source_repo.get_all_active()
        if not sources:
            logger.info("Aucune source active — ingestion terminée")
            return []
        return [self.run_source(source.id) for source in sources]

    def run_source(self, source_id: uuid.UUID) -> IngestionResult:
        """Lance l'ingestion pour une source donnée."""
        source = self.source_repo.get_by_id(source_id)
        if not source:
            logger.error("Source introuvable : %s", source_id)
            return IngestionResult(
                source_name=str(source_id),
                errors=1,
                error_details=[f"Source introuvable : {source_id}"],
            )

        result = IngestionResult(source_name=source.name)
        t0 = time.monotonic()

        # Créer le run dès le départ pour tracer le début
        run = self.ingestion_run_repo.create_running(source_id)
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            # Pas bloquant — continuer sans run persisté
            run = None

        connector = self.connector_manager.get_connector(source)
        if not connector:
            logger.info("Pas de connecteur disponible pour '%s' — source ignorée", source.name)
            result.duration_seconds = time.monotonic() - t0
            self._finalize_run(run, result, result.duration_seconds)
            return result

        logger.info("Ingestion démarrée pour '%s'", source.name)

        try:
            payloads = connector.fetch()
        except Exception as exc:
            logger.exception("Erreur fetch pour '%s' : %s", source.name, exc)
            result.errors += 1
            result.error_details.append(f"fetch error: {exc}")
            result.duration_seconds = time.monotonic() - t0
            self._finalize_run(run, result, result.duration_seconds)
            return result

        result.total_fetched = len(payloads)
        logger.info("'%s' — %d offres récupérées", source.name, result.total_fetched)

        for payload in payloads:
            try:
                self._process_one(payload, source.id, result)
            except Exception as exc:
                logger.exception("Erreur traitement offre '%s' : %s", payload.raw_title, exc)
                result.errors += 1
                result.error_details.append(
                    f"process error [{payload.external_offer_id}]: {exc}"
                )

        duration = time.monotonic() - t0
        result.duration_seconds = duration

        try:
            self._finalize_run(run, result, duration)
            self.db.commit()
        except Exception as exc:
            logger.exception("Erreur commit pour '%s' : %s", source.name, exc)
            self.db.rollback()
            result.errors += 1
            result.error_details.append(f"commit error: {exc}")

        logger.info(
            "'%s' terminé — new=%d updated=%d dup=%d err=%d (%.1fs)",
            source.name,
            result.new_offers,
            result.updated_offers,
            result.duplicates,
            result.errors,
            result.duration_seconds,
        )
        return result

    # ------------------------------------------------------------------ #
    # Traitement d'une offre                                               #
    # ------------------------------------------------------------------ #

    def _process_one(
        self,
        payload: RawOfferPayload,
        source_id: uuid.UUID,
        result: IngestionResult,
    ) -> None:
        # a. Persister l'offre brute
        offer_raw = self._upsert_offer_raw(payload, source_id)

        # b. Normaliser
        normalized = self.normalizer.normalize(payload)

        # c. Dédupliquer
        decision = self.deduplicator.deduplicate(payload, normalized, source_id)

        # d. Agir selon la décision
        if decision.decision == "create":
            company = self.company_repo.get_or_create(
                name=normalized.company_name,
                location=normalized.location_text,
            )
            offer = Offer(
                raw_offer_id=offer_raw.id,
                company_id=company.id,
                primary_source_id=source_id,
                normalized_title=normalized.normalized_title,
                normalized_description=normalized.normalized_description,
                contract_type=normalized.contract_type,
                duration_months=normalized.duration_months,
                location_text=normalized.location_text,
                work_mode=normalized.work_mode,
                education_level=normalized.education_level,
                offer_url=payload.offer_url,
                external_offer_id=payload.external_offer_id,
                checksum=normalized.checksum,
                published_at=payload.published_at_detected,
                current_state=OfferState.NORMALIZED,
                is_active=True,
            )
            # e. Scorer global
            self.scorer.score(offer, normalized)
            # f. Scorer personnalisé si profil existe
            prefs = self.pref_repo.get_default()
            if prefs is not None:
                self.personalized_scorer.score(offer, prefs)
            self.offer_repo.create(offer)
            self._update_raw_status(offer_raw, "PARSED")
            result.new_offers += 1

        elif decision.decision == "update":
            if decision.matched_offer_id:
                existing = self.offer_repo.get_by_id(decision.matched_offer_id)
                if existing:
                    existing.checksum = normalized.checksum
                    existing.raw_offer_id = offer_raw.id
                    self.scorer.score(existing, normalized)
                    prefs = self.pref_repo.get_default()
                    if prefs is not None:
                        self.personalized_scorer.score(existing, prefs)
                    self.db.flush()
            self._update_raw_status(offer_raw, "PARSED")
            result.updated_offers += 1

        else:  # duplicate
            self._update_raw_status(offer_raw, "PARSED")
            result.duplicates += 1

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _upsert_offer_raw(self, payload: RawOfferPayload, source_id: uuid.UUID) -> OfferRaw:
        if payload.offer_url:
            existing = self.offer_raw_repo.get_by_url(payload.offer_url)
            if existing:
                return existing

        if payload.external_offer_id:
            existing = self.offer_raw_repo.get_by_source_and_external_id(
                source_id, payload.external_offer_id
            )
            if existing:
                return existing

        offer_raw = OfferRaw(
            source_id=source_id,
            external_offer_id=payload.external_offer_id,
            offer_url=payload.offer_url,
            raw_title=payload.raw_title,
            raw_content=payload.raw_content,
            raw_location=payload.raw_location,
            raw_company_name=payload.raw_company_name,
            published_at_detected=payload.published_at_detected,
            parsing_status="PENDING",
            metadata_json=payload.metadata or None,
        )
        return self.offer_raw_repo.create(offer_raw)

    def _update_raw_status(self, offer_raw: OfferRaw, status: str) -> None:
        self.offer_raw_repo.update_parsing_status(offer_raw, status)

    def _finalize_run(
        self,
        run,
        result: IngestionResult,
        duration_seconds: float,
    ) -> None:
        if run is None:
            return
        if result.errors > 0 and result.new_offers == 0 and result.updated_offers == 0:
            status = IngestionStatus.FAILED
        elif result.errors > 0:
            status = IngestionStatus.PARTIAL
        else:
            status = IngestionStatus.SUCCESS

        self.ingestion_run_repo.finish(run, result, status)
        result.run_id = run.id
