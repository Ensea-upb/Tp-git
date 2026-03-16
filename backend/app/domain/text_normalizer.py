"""
Normalisation de texte pour comparaison sémantique et déduplication.

Fonctions déterministes, sans état, sans effet de bord.
Utilisées par OfferDeduplicator (L4/L5) et OfferRankingService.
"""

import re
import unicodedata

# Mots vides pour la recherche plein texte : suppression agressive
# Supprime genre (h/f), intitulés vagues, type de contrat, niveau
_SEARCH_STOPWORDS: frozenset[str] = frozenset(
    {
        "stage", "stagiaire", "intern", "internship",
        "junior", "senior", "lead", "expert",
        "h/f", "f/h", "h", "f",
        "cdi", "cdd", "alternance", "apprentissage",
        "poste", "offre", "emploi",
    }
)

# Mots vides pour la déduplication : supprime uniquement le bruit générique
# Conserve les indicateurs de type de contrat (stage, cdi…) et de niveau (junior, senior…)
# afin d'éviter les faux positifs entre offres de nature différente.
_DEDUP_STOPWORDS: frozenset[str] = frozenset(
    {
        "h/f", "f/h", "h", "f",
        "poste", "offre", "emploi",
    }
)

# Suffixes juridiques à supprimer des noms d'entreprise
# "france" retiré : trop destructeur pour des noms propres comme "France Travail"
_COMPANY_SUFFIXES: frozenset[str] = frozenset(
    {
        "inc", "llc", "ltd", "limited",
        "sa", "sas", "sasu", "sarl", "eurl",
        "spa", "ag", "gmbh", "bv", "nv",
        "group", "groupe", "holding",
        "international", "europe",
    }
)

# Mots inutiles dans les noms de ville
_CITY_STOPWORDS: frozenset[str] = frozenset(
    {"cedex", "arrondissement", "saint", "ste", "st"}
)


def _strip_accents(text: str) -> str:
    """Supprime les diacritiques : é→e, ç→c, etc."""
    normalized = unicodedata.normalize("NFD", text)
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn")


def _clean(text: str) -> str:
    """Minuscule + suppression accents + suppression ponctuation + collapse espaces."""
    text = _strip_accents(text.lower().strip())
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _remove_words(text: str, stopwords: frozenset[str]) -> str:
    """Retire les mots présents dans stopwords."""
    words = [w for w in text.split() if w not in stopwords]
    return " ".join(words)


def normalize_title_for_dedup(title: str) -> str:
    """
    Normalise un intitulé de poste pour la déduplication.

    Supprime uniquement le bruit générique (genre h/f, mots vides).
    Conserve les indicateurs de type de contrat (stage, cdi, alternance…)
    et de niveau (junior, senior, lead…) pour éviter les faux positifs
    entre offres de nature différente.

    Exemples :
      "Stage Data Engineer H/F"         → "stage data engineer"
      "Data Engineer CDI Senior"         → "data engineer cdi senior"
      "Data Engineer H/F — Offre Paris"  → "data engineer paris"
    """
    cleaned = _clean(title)
    return _remove_words(cleaned, _DEDUP_STOPWORDS).strip()


def normalize_title_for_search(title: str) -> str:
    """
    Normalise un intitulé de poste pour la recherche plein texte.

    Suppression agressive : retire le type de contrat, le niveau et le bruit
    pour maximiser les correspondances sémantiques.

    Exemples :
      "Stage Data Engineer H/F — Junior" → "data engineer"
      "Senior Data Scientist CDI"        → "data scientist"
    """
    cleaned = _clean(title)
    return _remove_words(cleaned, _SEARCH_STOPWORDS).strip()


# Alias de compatibilité — préférer normalize_title_for_search explicitement
normalize_title = normalize_title_for_search


def normalize_company(company: str) -> str:
    """
    Normalise un nom d'entreprise.

    Étapes :
    1. Minuscule + suppression accents + suppression ponctuation
    2. Suppression des suffixes juridiques (SA, SAS, Ltd…)
    3. Collapse espaces

    Note : "france" n'est PAS supprimé pour préserver les noms propres
    contenant ce mot (ex: "France Travail", "France TV").

    Exemples :
      "BNP Paribas SA"       → "bnp paribas"
      "Google France"        → "google france"
      "L'Oréal Group"        → "loreal"
      "France Travail"       → "france travail"
    """
    cleaned = _clean(company)
    return _remove_words(cleaned, _COMPANY_SUFFIXES).strip()


def normalize_city(city: str) -> str:
    """
    Normalise un nom de ville.

    Étapes :
    1. Minuscule + suppression accents + suppression ponctuation
    2. Extraction du premier token significatif (avant virgule/parenthèse dans le texte nettoyé)
    3. Suppression des mots inutiles (cedex, saint…)

    Exemples :
      "Paris 8ème (75)" → "paris 8eme"
      "Lyon Cedex 03"   → "lyon 03"
      "Île-de-France"   → "ile de france"
    """
    if not city:
        return ""
    cleaned = _clean(city)
    return _remove_words(cleaned, _CITY_STOPWORDS).strip()
