#!/usr/bin/env python3
"""
Script de seed — Sprint 1
Charge 10 offres fictives dans PostgreSQL pour validation du Sprint 1.
Usage : python scripts/seed.py
"""

import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, "/app")

from app.domain.enums.offer_state import OfferState
from app.domain.enums.work_mode import WorkMode
from app.infrastructure.db.base import SessionLocal
from app.infrastructure.db.models.company import Company
from app.infrastructure.db.models.offer import Offer
from app.infrastructure.db.models.source import Source


def seed() -> None:
    db = SessionLocal()
    try:
        # Vérifier si des données existent déjà
        existing = db.query(Offer).count()
        if existing > 0:
            print(f"Seed déjà effectué — {existing} offres en base. Skip.")
            return

        # --- Sources ---
        source_ft = Source(
            id=uuid.uuid4(),
            name="France Travail",
            source_type="api_officielle",
            base_url="https://api.francetravail.io",
            is_active=True,
            check_frequency_hours=3,
            legal_status="autorisé",
        )
        source_career = Source(
            id=uuid.uuid4(),
            name="Pages Carrières Entreprises",
            source_type="scraping_http",
            base_url=None,
            is_active=True,
            check_frequency_hours=6,
            legal_status="autorisé",
        )
        db.add_all([source_ft, source_career])

        # --- Entreprises ---
        companies_data = [
            {"name": "Thales", "sector": "Défense & Aéronautique", "location": "Paris, Île-de-France"},
            {"name": "Airbus", "sector": "Aéronautique", "location": "Toulouse, Occitanie"},
            {"name": "Dassault Systèmes", "sector": "Logiciels industriels", "location": "Vélizy-Villacoublay"},
            {"name": "Capgemini", "sector": "Conseil & IT", "location": "Paris, Île-de-France"},
            {"name": "Ubisoft", "sector": "Jeux vidéo", "location": "Paris, Île-de-France"},
            {"name": "BNP Paribas", "sector": "Finance & Banque", "location": "Paris, Île-de-France"},
            {"name": "Renault Group", "sector": "Automobile", "location": "Boulogne-Billancourt"},
            {"name": "Veolia", "sector": "Environnement", "location": "Aubervilliers, Île-de-France"},
            {"name": "Orange", "sector": "Télécommunications", "location": "Paris, Île-de-France"},
            {"name": "SNCF", "sector": "Transport ferroviaire", "location": "Saint-Denis, Île-de-France"},
        ]
        companies = []
        for c in companies_data:
            company = Company(
                id=uuid.uuid4(),
                name=c["name"],
                sector=c["sector"],
                main_location=c["location"],
                priority_level=1,
                company_status="neutre",
            )
            companies.append(company)
        db.add_all(companies)
        db.flush()  # Pour avoir les IDs

        # --- Offres fictives ---
        offers_data = [
            {
                "title": "Stage Ingénieur Développement Logiciel Embarqué (F/H)",
                "description": (
                    "Au sein de la Direction des Systèmes Embarqués, vous participez au "
                    "développement de logiciels temps-réel pour systèmes avioniques. "
                    "Vous travaillerez en C/C++ sur des cibles bare-metal et RTOS. "
                    "Compétences requises : C/C++, notions de systèmes embarqués, rigueur."
                ),
                "contract_type": "Stage",
                "duration_months": 6,
                "location": "Paris, Île-de-France",
                "work_mode": WorkMode.HYBRID,
                "state": OfferState.QUALIFIED,
                "global_score": 87.5,
                "action_score": 82.0,
                "justification": {
                    "résumé": "Très bonne adéquation profil/offre",
                    "points_forts": ["C/C++ maîtrisé", "Systèmes embarqués", "Entreprise cible"],
                    "points_faibles": ["Expérience RTOS limitée"],
                    "recommandation": "Postuler en priorité",
                },
                "company_idx": 0,
                "source": source_ft,
                "url": "https://francetravail.io/offres/stage-thales-embarque-2026",
                "education_level": "Bac+5",
                "published_at": datetime(2026, 3, 10, tzinfo=timezone.utc),
            },
            {
                "title": "Stage Data Science — Analyse prédictive maintenance aéronefs",
                "description": (
                    "Vous rejoignez l'équipe Data & IA pour développer des modèles prédictifs "
                    "de maintenance sur données capteurs. Environnement Python/Spark. "
                    "Compétences : Python, scikit-learn, pandas, SQL, statistiques."
                ),
                "contract_type": "Stage",
                "duration_months": 5,
                "location": "Toulouse, Occitanie",
                "work_mode": WorkMode.ONSITE,
                "state": OfferState.ANALYZED,
                "global_score": 79.0,
                "action_score": 74.0,
                "justification": {
                    "résumé": "Bonne adéquation sur les compétences data",
                    "points_forts": ["Python", "Machine learning", "Secteur aéro intéressant"],
                    "points_faibles": ["Spark peu maîtrisé", "Toulouse éloigné"],
                    "recommandation": "Postuler si ouvert à Toulouse",
                },
                "company_idx": 1,
                "source": source_career,
                "url": "https://careers.airbus.com/stage-data-science-2026",
                "education_level": "Bac+5",
                "published_at": datetime(2026, 3, 8, tzinfo=timezone.utc),
            },
            {
                "title": "Stage Développeur Full-Stack — Plateforme 3DEXPERIENCE",
                "description": (
                    "Contribution au développement de widgets pour la plateforme 3DEXPERIENCE. "
                    "Stack : JavaScript/TypeScript, React, Java Spring Boot, REST APIs. "
                    "Environnement agile, code reviews, CI/CD."
                ),
                "contract_type": "Stage",
                "duration_months": 6,
                "location": "Vélizy-Villacoublay, Île-de-France",
                "work_mode": WorkMode.HYBRID,
                "state": OfferState.READY_FOR_REVIEW,
                "global_score": 91.0,
                "action_score": 88.5,
                "justification": {
                    "résumé": "Excellente adéquation — entreprise top, stack parfaite",
                    "points_forts": ["React", "TypeScript", "Java Spring", "Agile"],
                    "points_faibles": [],
                    "recommandation": "Candidature prioritaire — prête à soumettre",
                },
                "company_idx": 2,
                "source": source_career,
                "url": "https://careers.3ds.com/stage-fullstack-2026",
                "education_level": "Bac+5",
                "published_at": datetime(2026, 3, 12, tzinfo=timezone.utc),
            },
            {
                "title": "Stage Consultant Cloud & DevOps",
                "description": (
                    "Accompagnement de clients dans leur transformation cloud (AWS/Azure). "
                    "Missions : déploiement infrastructure as code, CI/CD, monitoring. "
                    "Compétences : Terraform, Docker, Kubernetes, Python/Bash."
                ),
                "contract_type": "Stage",
                "duration_months": 6,
                "location": "Paris, Île-de-France",
                "work_mode": WorkMode.HYBRID,
                "state": OfferState.NORMALIZED,
                "global_score": 68.0,
                "action_score": 60.0,
                "justification": {
                    "résumé": "Adéquation correcte mais profil consultant non prioritaire",
                    "points_forts": ["Docker", "Cloud", "Paris"],
                    "points_faibles": ["Kubernetes peu maîtrisé", "Conseil peu recherché"],
                    "recommandation": "Secondaire — postuler si manque d'options",
                },
                "company_idx": 3,
                "source": source_ft,
                "url": "https://francetravail.io/offres/stage-capgemini-cloud-2026",
                "education_level": "Bac+4/5",
                "published_at": datetime(2026, 3, 5, tzinfo=timezone.utc),
            },
            {
                "title": "Stage Programmeur Gameplay — Jeu PC/Console",
                "description": (
                    "Rejoindre une équipe de développement sur un jeu AAA. "
                    "Implémentation de mécaniques gameplay en C++/Unreal Engine 5. "
                    "Compétences : C++, passion jeux vidéo, algorithmique."
                ),
                "contract_type": "Stage",
                "duration_months": 6,
                "location": "Paris, Île-de-France",
                "work_mode": WorkMode.ONSITE,
                "state": OfferState.DETECTED,
                "global_score": None,
                "action_score": None,
                "justification": None,
                "company_idx": 4,
                "source": source_career,
                "url": "https://careers.ubisoft.com/stage-gameplay-2026",
                "education_level": "Bac+3/5",
                "published_at": datetime(2026, 3, 14, tzinfo=timezone.utc),
            },
            {
                "title": "Stage Développeur Logiciel — Core Banking Platform",
                "description": (
                    "Développement de fonctionnalités sur la plateforme core banking. "
                    "Java 21, Spring Boot 3, PostgreSQL, Kafka. Méthodes agiles Scrum. "
                    "Environnement exigeant, fort niveau technique attendu."
                ),
                "contract_type": "Stage",
                "duration_months": 6,
                "location": "Paris, Île-de-France",
                "work_mode": WorkMode.HYBRID,
                "state": OfferState.ANALYZED,
                "global_score": 72.0,
                "action_score": 65.0,
                "justification": {
                    "résumé": "Bon match technique, secteur bancaire moins attractif",
                    "points_forts": ["Java Spring Boot", "PostgreSQL", "Kafka"],
                    "points_faibles": ["Secteur finance peu motivant", "Environnement corporate lourd"],
                    "recommandation": "Postuler si besoin de diversifier",
                },
                "company_idx": 5,
                "source": source_ft,
                "url": "https://francetravail.io/offres/stage-bnp-core-banking-2026",
                "education_level": "Bac+5",
                "published_at": datetime(2026, 3, 7, tzinfo=timezone.utc),
            },
            {
                "title": "Stage Ingénieur Développement Systèmes Embarqués Véhicule",
                "description": (
                    "Participation au développement des systèmes ADAS (aide à la conduite). "
                    "C/C++ temps-réel, AUTOSAR, communication CAN/LIN. "
                    "Simulation HIL/SIL, tests unitaires et intégration."
                ),
                "contract_type": "Stage",
                "duration_months": 5,
                "location": "Boulogne-Billancourt, Île-de-France",
                "work_mode": WorkMode.ONSITE,
                "state": OfferState.QUALIFIED,
                "global_score": 84.0,
                "action_score": 79.5,
                "justification": {
                    "résumé": "Très bonne adéquation systèmes embarqués automobile",
                    "points_forts": ["C/C++", "Embarqué temps-réel", "ADAS très demandé"],
                    "points_faibles": ["AUTOSAR pas encore maîtrisé"],
                    "recommandation": "Postuler — bon retour sur investissement apprentissage",
                },
                "company_idx": 6,
                "source": source_career,
                "url": "https://careers.renaultgroup.com/stage-embarque-adas-2026",
                "education_level": "Bac+5",
                "published_at": datetime(2026, 3, 9, tzinfo=timezone.utc),
            },
            {
                "title": "Stage Data Engineer — Optimisation IoT eau & déchets",
                "description": (
                    "Traitement de flux de données IoT pour optimiser la gestion des réseaux d'eau. "
                    "Python, Apache Kafka, InfluxDB, Grafana. "
                    "Projet à fort impact environnemental."
                ),
                "contract_type": "Stage",
                "duration_months": 6,
                "location": "Aubervilliers, Île-de-France",
                "work_mode": WorkMode.HYBRID,
                "state": OfferState.NORMALIZED,
                "global_score": 61.0,
                "action_score": 52.0,
                "justification": {
                    "résumé": "Adéquation partielle — IoT intéressant mais stack peu familière",
                    "points_forts": ["Python", "Impact environnemental positif"],
                    "points_faibles": ["InfluxDB inconnu", "Kafka peu maîtrisé", "Secteur peu prioritaire"],
                    "recommandation": "Faible priorité",
                },
                "company_idx": 7,
                "source": source_ft,
                "url": "https://francetravail.io/offres/stage-veolia-iot-2026",
                "education_level": "Bac+4/5",
                "published_at": datetime(2026, 3, 4, tzinfo=timezone.utc),
            },
            {
                "title": "Stage Développeur Backend — Plateforme 5G Network Slicing",
                "description": (
                    "Contribution au développement de l'API de gestion du network slicing 5G. "
                    "Python FastAPI, gRPC, Kubernetes, cloud-native. "
                    "Environnement R&D avec publication possible."
                ),
                "contract_type": "Stage",
                "duration_months": 6,
                "location": "Paris, Île-de-France",
                "work_mode": WorkMode.HYBRID,
                "state": OfferState.DRAFT_PREPARED,
                "global_score": 88.0,
                "action_score": 85.0,
                "justification": {
                    "résumé": "Excellente adéquation — stack moderne, R&D, Paris",
                    "points_forts": ["FastAPI", "Python", "5G/cloud-native", "R&D"],
                    "points_faibles": ["gRPC nouveau"],
                    "recommandation": "Candidature prioritaire — brouillon prêt",
                },
                "company_idx": 8,
                "source": source_career,
                "url": "https://careers.orange.com/stage-5g-backend-2026",
                "education_level": "Bac+5",
                "published_at": datetime(2026, 3, 11, tzinfo=timezone.utc),
            },
            {
                "title": "Stage Ingénieur Systèmes — Supervision digitale infrastructure ferroviaire",
                "description": (
                    "Développement d'outils de supervision et monitoring de l'infrastructure ferroviaire. "
                    "Python, React, bases de données temps-réel, APIs REST. "
                    "Stage polyvalent avec exposition aux systèmes critiques."
                ),
                "contract_type": "Stage",
                "duration_months": 6,
                "location": "Saint-Denis, Île-de-France",
                "work_mode": WorkMode.HYBRID,
                "state": OfferState.ANALYZED,
                "global_score": 70.0,
                "action_score": 63.0,
                "justification": {
                    "résumé": "Bonne adéquation technique, secteur ferroviaire moins prioritaire",
                    "points_forts": ["Python", "React", "REST APIs", "Systèmes critiques"],
                    "points_faibles": ["Secteur moins attractif", "Environnement SNCF bureaucratique"],
                    "recommandation": "Postuler en complément",
                },
                "company_idx": 9,
                "source": source_ft,
                "url": "https://francetravail.io/offres/stage-sncf-supervision-2026",
                "education_level": "Bac+4/5",
                "published_at": datetime(2026, 3, 6, tzinfo=timezone.utc),
            },
        ]

        offers = []
        for data in offers_data:
            offer = Offer(
                id=uuid.uuid4(),
                company_id=companies[data["company_idx"]].id,
                primary_source_id=data["source"].id,
                normalized_title=data["title"],
                normalized_description=data["description"],
                contract_type=data["contract_type"],
                duration_months=data["duration_months"],
                location_text=data["location"],
                work_mode=data["work_mode"],
                education_level=data["education_level"],
                published_at=data["published_at"],
                current_state=data["state"],
                is_active=True,
                global_score=data["global_score"],
                action_score=data["action_score"],
                score_justification=data["justification"],
                offer_url=data["url"],
            )
            offers.append(offer)

        db.add_all(offers)
        db.commit()
        print(f"Seed terminé — {len(offers)} offres insérées.")

    except Exception as e:
        db.rollback()
        print(f"Erreur lors du seed : {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
