"""
Prompt templates for all LLM features.
All prompts request JSON output to enable reliable parsing.
Prompts are kept concise for CPU inference (gemma3n:e2b @ ~2B params).
"""
from app.infrastructure.db.models.offer import Offer
from app.infrastructure.db.models.candidate_profile import CandidateProfile


def build_offer_analysis_prompt(offer: Offer) -> str:
    title = offer.normalized_title or ""
    description = (offer.normalized_description or "")[:1500]
    company = offer.company.name if offer.company else "inconnue"
    contract = offer.contract_type or ""
    duration = f"{offer.duration_months} mois" if offer.duration_months else ""
    location = offer.location_text or ""

    return f"""Analyse cette offre de stage/emploi et extrais les informations structurées.
Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ou après.

Offre:
Titre: {title}
Entreprise: {company}
Contrat: {contract} {duration}
Lieu: {location}
Description: {description}

JSON attendu:
{{
  "summary": "résumé en 2-3 phrases de ce que propose le poste",
  "missions": ["mission 1", "mission 2", "mission 3"],
  "skills_required": ["compétence 1", "compétence 2"],
  "tech_stack": ["Python", "SQL", "..."],
  "seniority_level": "junior|mid|senior|non précisé"
}}"""


def build_profile_match_prompt(offer: Offer, profile: CandidateProfile) -> str:
    title = offer.normalized_title or ""
    description = (offer.normalized_description or "")[:800]
    company = offer.company.name if offer.company else "inconnue"

    profile_skills = ", ".join(profile.skills or [])
    profile_tech = ", ".join(profile.tech_stack or [])
    profile_summary = profile.summary or ""
    profile_level = profile.current_level or ""
    profile_domains = ", ".join(profile.target_domains or [])

    return f"""Évalue la compatibilité entre ce candidat et cette offre.
Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ou après.

Candidat:
Niveau: {profile_level}
Compétences: {profile_skills}
Technologies: {profile_tech}
Domaines cibles: {profile_domains}
Bio: {profile_summary}

Offre:
Titre: {title} @ {company}
Description: {description}

JSON attendu:
{{
  "match_score": 75,
  "strengths": ["point fort 1", "point fort 2"],
  "gaps": ["lacune 1", "lacune 2"],
  "recommendation": "phrase de conseil en 1-2 lignes"
}}"""


def build_cover_letter_prompt(offer: Offer, profile: CandidateProfile) -> str:
    title = offer.normalized_title or ""
    company = offer.company.name if offer.company else "l'entreprise"
    description = (offer.normalized_description or "")[:600]

    profile_name = profile.full_name or "le candidat"
    profile_level = profile.current_level or ""
    profile_school = profile.school or ""
    profile_skills = ", ".join(profile.skills or [])
    profile_tech = ", ".join(profile.tech_stack or [])
    profile_summary = profile.summary or ""
    availability = profile.availability or ""

    return f"""Rédige une lettre de motivation professionnelle pour ce poste.
Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ou après.

Candidat: {profile_name}, {profile_level} @ {profile_school}
Compétences: {profile_skills}
Technologies: {profile_tech}
Disponibilité: {availability}
Bio: {profile_summary}

Poste: {title} @ {company}
Description: {description}

JSON attendu:
{{
  "subject": "Candidature — {title} @ {company}",
  "body": "Madame, Monsieur,\\n\\n[corps de la lettre en 3-4 paragraphes]\\n\\nCordialement,\\n{profile_name}"
}}"""


def build_application_email_prompt(offer: Offer, profile: CandidateProfile) -> str:
    title = offer.normalized_title or ""
    company = offer.company.name if offer.company else "l'entreprise"
    profile_name = profile.full_name or "le candidat"
    availability = profile.availability or ""

    return f"""Rédige un email de candidature court et percutant.
Réponds UNIQUEMENT avec un objet JSON valide.

Candidat: {profile_name}, disponible {availability}
Poste: {title} @ {company}

JSON attendu:
{{
  "subject": "Candidature {title} — {profile_name}",
  "body": "Bonjour,\\n\\n[2-3 phrases maximum, accroche + valeur ajoutée + disponibilité]\\n\\nCordialement,\\n{profile_name}"
}}"""


def build_interview_prep_prompt(offer: Offer, profile: CandidateProfile) -> str:
    title = offer.normalized_title or ""
    company = offer.company.name if offer.company else "l'entreprise"
    description = (offer.normalized_description or "")[:600]
    profile_skills = ", ".join(profile.skills or [])
    profile_tech = ", ".join(profile.tech_stack or [])

    return f"""Prépare des questions d'entretien pour ce poste.
Réponds UNIQUEMENT avec un objet JSON valide.

Poste: {title} @ {company}
Description: {description}
Compétences candidat: {profile_skills}
Technologies: {profile_tech}

JSON attendu:
{{
  "technical_questions": ["question 1", "question 2", "question 3"],
  "behavioral_questions": ["question 1", "question 2"],
  "questions_to_ask": ["question à poser au recruteur 1", "question 2"],
  "preparation_tips": ["conseil 1", "conseil 2"]
}}"""
