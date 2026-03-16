#!/usr/bin/env python
"""
CLI d'ingestion des offres.

Usage :
  # Toutes les sources actives
  python scripts/run_ingestion.py

  # Source spécifique par UUID
  python scripts/run_ingestion.py --source-id <uuid>

  # Dry-run (fetch uniquement, pas de persistance)
  python scripts/run_ingestion.py --dry-run
"""

import argparse
import logging
import sys
import uuid
from pathlib import Path

# Ajout de la racine backend au path
_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

from app.infrastructure.db.base import SessionLocal  # noqa: E402
from app.services.offer_ingestion_service import OfferIngestionService  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("run_ingestion")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lance le pipeline d'ingestion des offres")
    parser.add_argument(
        "--source-id",
        type=str,
        default=None,
        help="UUID de la source à ingérer (défaut : toutes les sources actives)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch uniquement, sans persistance en base",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.dry_run:
        logger.info("Mode dry-run : aucune écriture en base")

    db = SessionLocal()
    try:
        service = OfferIngestionService(db)

        if args.source_id:
            try:
                source_id = uuid.UUID(args.source_id)
            except ValueError:
                logger.error("UUID invalide : %s", args.source_id)
                return 1

            if args.dry_run:
                _dry_run_source(service, source_id)
                return 0

            result = service.run_source(source_id)
            results = [result]
        else:
            if args.dry_run:
                _dry_run_all(service)
                return 0

            results = service.run_all()

    finally:
        db.close()

    # Affichage du bilan
    print("\n" + "=" * 60)
    print("BILAN D'INGESTION")
    print("=" * 60)

    total_new = total_dup = total_err = 0
    for r in results:
        print(
            f"  {r.source_name:<30} "
            f"fetch={r.total_fetched:>4}  "
            f"new={r.new_offers:>4}  "
            f"upd={r.updated_offers:>4}  "
            f"dup={r.duplicates:>4}  "
            f"err={r.errors:>3}  "
            f"({r.duration_seconds:.1f}s)"
        )
        if r.error_details:
            for detail in r.error_details[:3]:
                print(f"    ! {detail}")
        total_new += r.new_offers
        total_dup += r.duplicates
        total_err += r.errors

    print("-" * 60)
    print(f"  TOTAL  new={total_new}  dup={total_dup}  err={total_err}")
    print("=" * 60 + "\n")

    return 0 if total_err == 0 else 1


def _dry_run_source(service: OfferIngestionService, source_id: uuid.UUID) -> None:
    source = service.source_repo.get_by_id(source_id)
    if not source:
        logger.error("Source introuvable : %s", source_id)
        return

    connector = service.connector_manager.get_connector(source)
    if not connector:
        logger.info("Pas de connecteur pour '%s'", source.name)
        return

    payloads = connector.fetch()
    logger.info("DRY-RUN '%s' — %d offres récupérées", source.name, len(payloads))
    for p in payloads[:5]:
        logger.info("  · %s | %s | %s", p.raw_title[:60], p.raw_company_name, p.offer_url)
    if len(payloads) > 5:
        logger.info("  … et %d autres", len(payloads) - 5)


def _dry_run_all(service: OfferIngestionService) -> None:
    sources = service.source_repo.get_all_active()
    for source in sources:
        _dry_run_source(service, source.id)


if __name__ == "__main__":
    sys.exit(main())
