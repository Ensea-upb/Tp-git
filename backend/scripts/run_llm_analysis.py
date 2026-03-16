#!/usr/bin/env python
"""
CLI pour lancer l'analyse LLM des offres.

Usage:
    python scripts/run_llm_analysis.py [OPTIONS]

Options:
    --offer-id UUID      Analyser une seule offre
    --mode analysis      Mode: analysis | match | both (défaut: both)
    --active-only        Limiter aux offres actives
    --limit N            Limiter le nombre d'offres à traiter
    --dry-run            Afficher sans appeler l'API LLM

Exemples:
    python scripts/run_llm_analysis.py --active-only --limit 10
    python scripts/run_llm_analysis.py --offer-id abc123 --mode analysis
    python scripts/run_llm_analysis.py --active-only --dry-run
"""
import argparse
import asyncio
import logging
import sys
import uuid
from pathlib import Path

# Ajouter le répertoire backend au sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def run(
    offer_id: uuid.UUID | None,
    mode: str,
    active_only: bool,
    limit: int | None,
    dry_run: bool,
) -> None:
    from app.infrastructure.db.session import SessionLocal
    from app.repositories.offer_repository import OfferRepository
    from app.repositories.offer_llm_analysis_repository import OfferLLMAnalysisRepository
    from app.repositories.profile_match_llm_repository import ProfileMatchLLMRepository
    from app.services.offer_llm_analysis_service import OfferLLMAnalysisService
    from app.services.profile_matching_service import ProfileMatchingService

    db = SessionLocal()
    try:
        repo = OfferRepository(db)

        if offer_id is not None:
            offers = [o for o in [repo.get_by_id(offer_id)] if o is not None]
        else:
            offers, _ = repo.get_all(
                page=1,
                page_size=limit or 9999,
                is_active=True if active_only else None,
            )

        if limit:
            offers = offers[:limit]

        logger.info("Offres à traiter : %d (mode=%s, dry_run=%s)", len(offers), mode, dry_run)

        if dry_run:
            for o in offers:
                logger.info("  [dry-run] %s — %s", o.id, o.normalized_title)
            return

        analysis_done = analysis_failed = match_done = match_failed = 0

        for offer in offers:
            if mode in ("analysis", "both"):
                try:
                    service = OfferLLMAnalysisService(db)
                    result = await service.analyze_offer(offer.id)
                    if result.analysis_status == "DONE":
                        analysis_done += 1
                        logger.info("✓ Analyse OK — %s", offer.normalized_title[:60])
                    else:
                        analysis_failed += 1
                        logger.warning("✗ Analyse FAILED — %s", offer.normalized_title[:60])
                except Exception as e:
                    analysis_failed += 1
                    logger.error("  Erreur analyse %s: %s", offer.id, e)
                    db.rollback()

            if mode in ("match", "both"):
                try:
                    service = ProfileMatchingService(db)
                    result = await service.match_offer(offer.id)
                    if result.match_status == "DONE":
                        match_done += 1
                        logger.info(
                            "✓ Match OK (%.0f/100) — %s",
                            float(result.match_score or 0),
                            offer.normalized_title[:60],
                        )
                    else:
                        match_failed += 1
                        logger.warning("✗ Match FAILED — %s", offer.normalized_title[:60])
                except Exception as e:
                    match_failed += 1
                    logger.error("  Erreur match %s: %s", offer.id, e)
                    db.rollback()

        logger.info(
            "Résumé — Analyse: %d OK / %d échec | Match: %d OK / %d échec",
            analysis_done, analysis_failed, match_done, match_failed,
        )
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Analyse LLM des offres de stage")
    parser.add_argument("--offer-id", type=str, default=None)
    parser.add_argument(
        "--mode",
        choices=["analysis", "match", "both"],
        default="both",
    )
    parser.add_argument("--active-only", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    offer_id = uuid.UUID(args.offer_id) if args.offer_id else None

    asyncio.run(
        run(
            offer_id=offer_id,
            mode=args.mode,
            active_only=args.active_only,
            limit=args.limit,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    main()
