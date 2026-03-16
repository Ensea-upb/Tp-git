import hashlib
import re

from bs4 import BeautifulSoup

from app.domain.dto.normalized_offer_payload import NormalizedOfferPayload
from app.domain.dto.raw_offer_payload import RawOfferPayload
from app.domain.enums.work_mode import WorkMode

# ------------------------------------------------------------------ #
# Mappings déterministes                                               #
# ------------------------------------------------------------------ #

_WORK_MODE_PATTERNS: list[tuple[re.Pattern, WorkMode]] = [
    (re.compile(r"\b(t[eé]l[eé]travail|remote|full.?remote|distanciel)\b", re.I), WorkMode.REMOTE),
    (re.compile(r"\b(hybride|hybrid|flexible|partiel)\b", re.I), WorkMode.HYBRID),
]

_CONTRACT_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(stage|internship|intern)\b", re.I), "Stage"),
    (re.compile(r"\b(alternance|apprentissage|contrat\s+d.?apprentissage)\b", re.I), "Alternance"),
    (re.compile(r"\b(cdi|permanent|unbefristet)\b", re.I), "CDI"),
    (re.compile(r"\b(cdd|temporaire|contrat\s+dur[eé]e\s+d[eé]termin[eé]e)\b", re.I), "CDD"),
    (re.compile(r"\b(freelance|ind[eé]pendant|mission)\b", re.I), "Freelance"),
]

_DURATION_RE = re.compile(r"(\d+)\s*(mois|months?)", re.I)

_EDUCATION_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bbac\s*[+]?\s*5\b|\bmaster\b|\bm[12]\b|\bing[eé]nieur\b", re.I), "Bac+5"),
    (re.compile(r"\bbac\s*[+]?\s*4\b|\bm1\b|\blicence\s+pro\b", re.I), "Bac+4"),
    (re.compile(r"\bbac\s*[+]?\s*3\b|\blicence\b|\bbach\b", re.I), "Bac+3"),
    (re.compile(r"\bbac\s*[+]?\s*2\b|\bbts\b|\biut\b|\bdut\b", re.I), "Bac+2"),
]

# Mots à ne pas mettre en majuscule lors du title-casing
_LOWERCASE_WORDS = frozenset(
    ["de", "du", "des", "le", "la", "les", "et", "en", "au", "aux",
     "un", "une", "sur", "par", "pour", "dans", "avec", "à", "l", "d"]
)


# ------------------------------------------------------------------ #
# Fonctions utilitaires                                                #
# ------------------------------------------------------------------ #

def _strip_html(text: str) -> str:
    soup = BeautifulSoup(text, "lxml")
    return soup.get_text(separator=" ")


def _clean_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _smart_title(text: str) -> str:
    """
    Title-case préservant les acronymes et les mots courts.
    Ex: 'STAGE DÉVELOPPEUR FULL-STACK (H/F)' → 'Stage Développeur Full-Stack (H/F)'
    """
    words = text.split()
    result = []
    for i, word in enumerate(words):
        # Conserver les acronymes (tout majuscule, longueur 2+)
        if word.isupper() and len(word) >= 2 and word.isalpha():
            result.append(word)
        elif i == 0 or word.lower() not in _LOWERCASE_WORDS:
            result.append(word.capitalize())
        else:
            result.append(word.lower())
    return " ".join(result)


def _detect_work_mode(text: str) -> WorkMode | None:
    for pattern, mode in _WORK_MODE_PATTERNS:
        if pattern.search(text):
            return mode
    return None


def _detect_contract_type(text: str) -> str | None:
    for pattern, contract in _CONTRACT_PATTERNS:
        if pattern.search(text):
            return contract
    return None


def _detect_duration(text: str) -> int | None:
    match = _DURATION_RE.search(text)
    if match:
        return int(match.group(1))
    return None


def _detect_education_level(text: str) -> str | None:
    for pattern, level in _EDUCATION_PATTERNS:
        if pattern.search(text):
            return level
    return None


def _compute_checksum(title: str, company: str, location: str, description: str) -> str:
    """SHA-256 déterministe sur les champs clés normalisés."""
    canonical = f"{title.lower()}|{company.lower()}|{location.lower()}|{description[:500].lower()}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ------------------------------------------------------------------ #
# Normaliseur                                                          #
# ------------------------------------------------------------------ #

class OfferNormalizer:
    """
    Transforme un RawOfferPayload en NormalizedOfferPayload.
    Logique entièrement déterministe — aucune dépendance LLM.
    """

    def normalize(self, payload: RawOfferPayload) -> NormalizedOfferPayload:
        # --- Titre ---
        raw_title = payload.raw_title or ""
        clean_title = _smart_title(_clean_whitespace(_strip_html(raw_title)))

        # --- Description ---
        raw_content = payload.raw_content or ""
        clean_description = _clean_whitespace(_strip_html(raw_content))

        # --- Entreprise ---
        company_name = _clean_whitespace(payload.raw_company_name or "Entreprise inconnue")

        # --- Localisation ---
        location_text = _clean_whitespace(payload.raw_location or "") or None

        # Texte combiné pour les détections
        full_text = f"{clean_title} {clean_description}"

        # --- Détections ---
        work_mode = _detect_work_mode(full_text)
        contract_type = _detect_contract_type(full_text)
        duration_months = _detect_duration(full_text)
        education_level = _detect_education_level(full_text)

        # --- Checksum ---
        checksum = _compute_checksum(
            clean_title,
            company_name,
            location_text or "",
            clean_description,
        )

        return NormalizedOfferPayload(
            normalized_title=clean_title,
            normalized_description=clean_description,
            company_name=company_name,
            checksum=checksum,
            contract_type=contract_type,
            duration_months=duration_months,
            location_text=location_text,
            work_mode=work_mode,
            education_level=education_level,
        )
