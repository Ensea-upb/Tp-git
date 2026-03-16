"""
Service de scoring déterministe des offres.

Règles explicites, pondérées, sans LLM.
Score final : 0–100 (entier).

Grille de points :
  +25  contrat Stage ou Alternance
  +20  mots-clés "data science / data analyst / data engineer"
  +15  mots-clés "machine learning / deep learning"
  +10  mots-clés "AI / IA / LLM / NLP"
  +10  mots-clés "économétrie / econometrics"
  +10  mots-clés "analytics / data viz / power bi / tableau"
  +10  télétravail (REMOTE)
  + 8  hybride (HYBRID)
  + 8  localisation IDF / Paris
  + 8  durée ≥ 6 mois
  -15  contrat CDI (non-stage)
  -10  profil senior dans un CDI (senior, lead, manager…)
"""

import re

from app.domain.dto.normalized_offer_payload import NormalizedOfferPayload
from app.domain.enums.work_mode import WorkMode
from app.infrastructure.db.models.offer import Offer

# ------------------------------------------------------------------ #
# Patterns de détection                                                #
# ------------------------------------------------------------------ #

_DATA_SCIENCE_RE = re.compile(
    r"\b(data[\s\-]?sci|data[\s\-]?analyst|data[\s\-]?engineer|scientist)\b", re.I
)
_ML_RE = re.compile(
    r"\b(machine[\s\-]?learning|deep[\s\-]?learning|apprentissage[\s\-]automatique|"
    r"random[\s\-]?forest|neural[\s\-]?net|réseau[\s\-]neuronal)\b",
    re.I,
)
_AI_RE = re.compile(
    r"\b(intelligence[\s\-]artificielle|\bai\b|\bia\b|llm|nlp|"
    r"natural[\s\-]?language|traitement[\s\-]du[\s\-]langage)\b",
    re.I,
)
_ECONOMETRICS_RE = re.compile(
    r"\b(économétr|econometr|microéconomie|macroéconomie|"
    r"séries[\s\-]temporelles|time[\s\-]series|causal[\s\-]inference|"
    r"stata|eviews)\b",
    re.I,
)
_ANALYTICS_RE = re.compile(
    r"\b(analytics|analyse[\s\-]de[\s\-]données|data[\s\-]viz|"
    r"tableau|power[\s\-]bi|looker|metabase|qlik)\b",
    re.I,
)
_IDF_RE = re.compile(
    r"\b(paris|île[\s\-]de[\s\-]france|idf|75|92|93|94|91|95|77|78|hauts[\s\-]de[\s\-]seine)\b",
    re.I,
)
_SENIOR_RE = re.compile(
    r"\b(senior|confirmé|expérimenté|lead|manager|directeur|head[\s\-]of|principal)\b",
    re.I,
)

# Map tag → label lisible (utilisé côté frontend)
TAG_DEFINITIONS: dict[str, re.Pattern] = {
    "data": _DATA_SCIENCE_RE,
    "ml": _ML_RE,
    "ai": _AI_RE,
    "analytics": _ANALYTICS_RE,
    "econometrics": _ECONOMETRICS_RE,
}

# Contrats considérés "stage / formation"
_INTERNSHIP_CONTRACTS = {"stage", "alternance", "intern", "internship"}


# ------------------------------------------------------------------ #
# Service                                                              #
# ------------------------------------------------------------------ #

class OfferScoringService:
    """
    Calcule et injecte le score de pertinence + tags sur un objet Offer.
    Opère en place (ne persiste pas — la persistance est de la responsabilité
    de la couche service appelante).
    """

    def score(self, offer: Offer, normalized: NormalizedOfferPayload) -> None:
        full_text = (
            f"{normalized.normalized_title} {normalized.normalized_description or ''}"
        )
        score = 0
        details: list[str] = []
        tags: list[str] = []

        # ── Contrat ────────────────────────────────────────────────────
        contract = (normalized.contract_type or "").strip().lower()
        if contract in _INTERNSHIP_CONTRACTS:
            score += 25
            details.append(f"+25 contrat {normalized.contract_type}")
        elif normalized.contract_type == "CDI":
            score -= 15
            details.append("-15 CDI (hors périmètre stage)")
            if _SENIOR_RE.search(full_text):
                score -= 10
                details.append("-10 profil senior détecté")

        # ── Domaines métier ────────────────────────────────────────────
        for tag, pattern in TAG_DEFINITIONS.items():
            if pattern.search(full_text):
                points = {"data": 20, "ml": 15, "ai": 10, "analytics": 10, "econometrics": 10}[tag]
                score += points
                details.append(f"+{points} domaine '{tag}'")
                tags.append(tag)

        # ── Mode de travail ────────────────────────────────────────────
        if normalized.work_mode == WorkMode.REMOTE:
            score += 10
            details.append("+10 télétravail complet")
        elif normalized.work_mode == WorkMode.HYBRID:
            score += 8
            details.append("+8 mode hybride")

        # ── Localisation IDF ───────────────────────────────────────────
        if normalized.location_text and _IDF_RE.search(normalized.location_text):
            score += 8
            details.append("+8 localisation IDF/Paris")

        # ── Durée ──────────────────────────────────────────────────────
        if normalized.duration_months and normalized.duration_months >= 6:
            score += 8
            details.append(f"+8 durée {normalized.duration_months} mois")

        # ── Clamp 0–100 ────────────────────────────────────────────────
        score = max(0, min(100, score))

        # ── Injection sur l'offre ──────────────────────────────────────
        offer.global_score = float(score)
        offer.tags = sorted(tags) if tags else None
        offer.score_justification = {
            "score": score,
            "résumé": f"{score}/100 — {len(details)} règle(s) appliquée(s)",
            "détails": details,
        }
