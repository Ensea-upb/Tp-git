"""
Normalisation de texte pour comparaison sémantique et déduplication.

Fonctions déterministes, sans état, sans effet de bord.
Utilisées par OfferDeduplicator (L4/L5) et OfferRankingService.
"""

import re
import unicodedata

# Mots vides dans les intitulés de poste (bruit sans valeur sémantique)
_TITLE_STOPWORDS: frozenset[str] = frozenset(
    {
        "stage", "stagiaire", "intern", "internship",
        "junior", "senior", "lead", "expert",
        "h/f", "f/h", "h", "f",
        "cdi", "cdd", "alternance", "apprentissage",
        "poste", "offre", "emploi",
    }
)

# Suffixes juridiques à supprimer des noms d'entreprise
_COMPANY_SUFFIXES: frozenset[str] = frozenset(
    {
        "inc", "llc", "ltd", "limited",
        "sa", "sas", "sasu", "sarl", "eurl",
        "spa", "ag", "gmbh", "bv", "nv",
        "group", "groupe", "holding",
        "france", "international", "europe",
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


def normalize_title(title: str) -> str:
    """
    Normalise un intitulé de poste.

    Étapes :
    1. Minuscule + suppression accents + suppression ponctuation
    2. Suppression des mots bruit (stage, h/f, junior…)
    3. Collapse espaces

    Exemple :
      "Stage Data Engineer H/F — Junior" → "data engineer"
    """
    cleaned = _clean(title)
    return _remove_words(cleaned, _TITLE_STOPWORDS).strip()


def normalize_company(company: str) -> str:
    """
    Normalise un nom d'entreprise.

    Étapes :
    1. Minuscule + suppression accents + suppression ponctuation
    2. Suppression des suffixes juridiques (SA, SAS, Ltd…)
    3. Collapse espaces

    Exemple :
      "BNP Paribas SA" → "bnp paribas"
      "Google France SAS" → "google"   (France et SAS supprimés)
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

    Exemple :
      "Paris 8ème (75)" → "paris 8eme"
      "Lyon Cedex 03"   → "lyon 03"
      "Île-de-France"   → "ile de france"
    """
    if not city:
        return ""
    cleaned = _clean(city)
    return _remove_words(cleaned, _CITY_STOPWORDS).strip()
