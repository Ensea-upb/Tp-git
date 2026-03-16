"""
Service de scoring personnalisé des offres.

Calcule un score dérivé du global_score en appliquant les préférences
utilisateur comme modificateurs (delta). Score final clampé à 0–100.

Grille de modification :
  +20  contract_type dans preferred_contract_types
  +15  work_mode dans preferred_work_modes
  +10  location match preferred_locations (substring, case-insensitive)
  + 5  par preferred_keyword trouvé dans titre+description (max +15)
  +10  par preferred_domain tag correspondant (max +30)
  -15  par exclude_keyword trouvé (max -30)
  -15  duration < minimum_duration_months

Le score part du global_score et lui applique le delta.
Si global_score est None, part de 50 (score neutre).
"""

from app.infrastructure.db.models.offer import Offer
from app.infrastructure.db.models.user_preference import UserPreference


class PersonalizedOfferScoringService:
    """
    Calcule et injecte personalized_score + personalized_justification
    sur un objet Offer (en place). Ne persiste pas — la persistance est
    la responsabilité de l'appelant.
    """

    def score(self, offer: Offer, prefs: UserPreference) -> None:
        base = float(offer.global_score) if offer.global_score is not None else 50.0
        delta = 0
        details: list[str] = []

        full_text = (
            f"{offer.normalized_title} {offer.normalized_description or ''}"
        ).lower()
        offer_tags = offer.tags or []

        # ── Contrat ────────────────────────────────────────────────────
        if prefs.preferred_contract_types and offer.contract_type:
            if offer.contract_type in prefs.preferred_contract_types:
                delta += 20
                details.append(f"+20 contrat '{offer.contract_type}' préféré")

        # ── Mode de travail ────────────────────────────────────────────
        if prefs.preferred_work_modes and offer.work_mode:
            if str(offer.work_mode) in prefs.preferred_work_modes:
                delta += 15
                details.append(f"+15 mode '{offer.work_mode}' préféré")

        # ── Localisation ───────────────────────────────────────────────
        if prefs.preferred_locations and offer.location_text:
            loc = offer.location_text.lower()
            for preferred in prefs.preferred_locations:
                if preferred.lower() in loc:
                    delta += 10
                    details.append(f"+10 localisation '{preferred}' correspondante")
                    break  # une seule localisation suffit

        # ── Mots-clés préférés (max +15) ───────────────────────────────
        if prefs.preferred_keywords:
            kw_bonus = 0
            matched_kws = []
            for kw in prefs.preferred_keywords:
                if kw.lower() in full_text and kw_bonus < 15:
                    kw_bonus += 5
                    matched_kws.append(kw)
            if kw_bonus:
                delta += kw_bonus
                details.append(f"+{kw_bonus} mots-clés préférés : {', '.join(matched_kws)}")

        # ── Domaines tags (max +30) ────────────────────────────────────
        if prefs.preferred_domains:
            domain_bonus = 0
            matched_domains = []
            for domain in prefs.preferred_domains:
                if domain in offer_tags and domain_bonus < 30:
                    domain_bonus += 10
                    matched_domains.append(domain)
            if domain_bonus:
                delta += domain_bonus
                details.append(f"+{domain_bonus} domaines : {', '.join(matched_domains)}")

        # ── Mots-clés exclus (max -30) ─────────────────────────────────
        if prefs.exclude_keywords:
            exclusion_malus = 0
            excluded_found = []
            for kw in prefs.exclude_keywords:
                if kw.lower() in full_text and exclusion_malus > -30:
                    exclusion_malus -= 15
                    excluded_found.append(kw)
            if exclusion_malus:
                delta += exclusion_malus
                details.append(f"{exclusion_malus} mots-clés exclus : {', '.join(excluded_found)}")

        # ── Durée minimale ─────────────────────────────────────────────
        if prefs.minimum_duration_months and offer.duration_months is not None:
            if offer.duration_months < prefs.minimum_duration_months:
                delta -= 15
                details.append(
                    f"-15 durée {offer.duration_months} mois "
                    f"< minimum {prefs.minimum_duration_months} mois"
                )

        # ── Score final ────────────────────────────────────────────────
        score = max(0.0, min(100.0, base + delta))

        offer.personalized_score = score
        offer.personalized_justification = {
            "base_score": base,
            "delta": delta,
            "score": score,
            "résumé": f"{score:.0f}/100 (base {base:.0f} {'+' if delta >= 0 else ''}{delta})",
            "détails": details,
        }
