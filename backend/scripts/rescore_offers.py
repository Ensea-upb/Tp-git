#!/usr/bin/env python3
"""
Script de rescore batch des offres.

Recalcule global_score + personalized_score sur les offres existantes.
Utile quand les règles de scoring changent ou après mise à jour des préférences.

Usage :
    python scripts/rescore_offers.py
    python scripts/rescore_offers.py --active-only
    python scripts/rescore_offers.py --offer-id <uuid>
    python scripts/rescore_offers.py --dry-run
    python scripts/rescore_offers.py --personalized-only
"""

import argparse
import os
import sys
import uuid
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH pour les imports app.*
sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://agent_user:agent_password@localhost:5432/agent_db",
)
os.environ.setdefault("APP_API_KEY", "dev-api-key-changeme")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.config import settings  # noqa: E402
from app.domain.dto.normalized_offer_payload import NormalizedOfferPayload  # noqa: E402
from app.domain.enums.work_mode import WorkMode  # noqa: E402
from app.infrastructure.db.models import *  # noqa: E402, F401, F403 — ensure all models are imported
from app.repositories.offer_repository import OfferRepository  # noqa: E402
from app.repositories.user_preference_repository import UserPreferenceRepository  # noqa: E402
from app.services.offer_scoring_service import OfferScoringService  # noqa: E402
from app.services.personalized_offer_scoring_service import PersonalizedOfferScoringService  # noqa: E402


def _offer_to_normalized_payload(offer) -> NormalizedOfferPayload:
    """Reconstruit un NormalizedOfferPayload depuis une offre existante pour le scoring global."""
    return NormalizedOfferPayload(
        normalized_title=offer.normalized_title,
        normalized_description=offer.normalized_description,
        company_name=offer.company.name if offer.company else "",
        checksum=offer.checksum or "",
        contract_type=offer.contract_type,
        duration_months=offer.duration_months,
        location_text=offer.location_text,
        work_mode=WorkMode(offer.work_mode) if offer.work_mode else None,
        education_level=offer.education_level,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Rescore batch des offres")
    parser.add_argument(
        "--active-only",
        action="store_true",
        help="Rescorer uniquement les offres actives",
    )
    parser.add_argument(
        "--offer-id",
        type=str,
        default=None,
        help="UUID d'une offre spécifique à rescorer",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simuler sans persister (affiche les scores calculés)",
    )
    parser.add_argument(
        "--personalized-only",
        action="store_true",
        help="Recalculer uniquement le score personnalisé (ne touche pas global_score)",
    )
    args = parser.parse_args()

    offer_id = uuid.UUID(args.offer_id) if args.offer_id else None

    # ── Connexion ─────────────────────────────────────────────────────
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        offer_repo = OfferRepository(db)
        pref_repo = UserPreferenceRepository(db)
        global_scorer = OfferScoringService()
        personalized_scorer = PersonalizedOfferScoringService()

        prefs = pref_repo.get_default()
        if prefs is None and not args.personalized_only:
            print("Info : aucun profil de préférences trouvé — le score personnalisé ne sera pas calculé.")
        elif prefs is None:
            print("Erreur : --personalized-only mais aucun profil de préférences trouvé.", file=sys.stderr)
            sys.exit(1)

        # ── Récupération des offres ────────────────────────────────────
        offers = offer_repo.get_all_for_rescore(
            active_only=args.active_only,
            offer_id=offer_id,
        )

        if not offers:
            print("Aucune offre à rescorer.")
            return

        print(f"{'[DRY RUN] ' if args.dry_run else ''}Rescore de {len(offers)} offre(s)...")

        updated = 0
        for offer in offers:
            normalized = _offer_to_normalized_payload(offer)

            if not args.personalized_only:
                global_scorer.score(offer, normalized)

            if prefs is not None:
                personalized_scorer.score(offer, prefs)

            if args.dry_run:
                print(
                    f"  [DRY] {offer.id} | {offer.normalized_title[:50]:<50} | "
                    f"global={offer.global_score:.0f} | "
                    f"perso={offer.personalized_score:.0f if offer.personalized_score is not None else 'N/A'}"
                )
            else:
                updated += 1

        if not args.dry_run:
            db.commit()
            print(f"Rescore terminé — {updated} offre(s) mises à jour.")
        else:
            print(f"[DRY RUN] {len(offers)} offre(s) aurait(ent) été rescorée(s).")

    except Exception as exc:
        db.rollback()
        print(f"Erreur : {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
