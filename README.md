# Agent Personnel de Recherche de Stage

Copilote intelligent de recherche de stage avec **human-in-the-loop** obligatoire.

## Stack technique

| Composant | Technologie |
|---|---|
| Frontend | Next.js 14 + TypeScript + Tailwind CSS |
| Backend API | FastAPI (Python 3.12) |
| Base de données | PostgreSQL 16 |
| Migrations | Alembic |
| ORM | SQLAlchemy 2.x |
| Déploiement | Docker / Docker Compose |

## Lancement rapide (Sprint 1)

### Prérequis

- Docker & Docker Compose installés

### Démarrage

```bash
# 1. Copier et adapter les variables d'environnement
cp .env.example .env

# 2. Démarrer la stack
docker compose up --build

# 3. (Premier lancement) Appliquer les migrations et charger les données de test
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/seed.py
```

### Accès

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Santé API | http://localhost:8000/v1/health |

### Authentification API

Tous les endpoints (sauf `/v1/health`) requièrent un header :
```
Authorization: Bearer <APP_API_KEY>
```
La valeur par défaut en développement : `dev-api-key-changeme`

## Structure du projet

```
Tp-git/
├── backend/           # FastAPI + SQLAlchemy + Alembic
│   ├── app/
│   │   ├── api/       # Endpoints et schémas
│   │   ├── domain/    # Enums et règles métier
│   │   ├── infrastructure/ # DB, modèles ORM
│   │   ├── repositories/   # Accès données
│   │   └── services/  # Logique métier
│   ├── alembic/       # Migrations
│   ├── scripts/       # Seed, utilitaires
│   └── tests/         # Tests pytest
└── frontend/          # Next.js App Router
    └── src/
        ├── app/       # Pages (liste offres, détail)
        ├── components/ # Composants réutilisables
        ├── lib/       # Client API
        └── types/     # Types TypeScript
```

## Tests

```bash
# Tests backend
docker compose exec backend pytest tests/ -v

# Ou localement (avec virtualenv activé)
cd backend && pytest tests/ -v
```

## Variables d'environnement

Voir `.env.example` pour la liste complète.

Variables critiques :
- `DATABASE_URL` — URL de connexion PostgreSQL
- `APP_API_KEY` — Clé d'authentification API
- `LLM_API_KEY` — Clé Anthropic (requis à partir du Sprint 3)

## Périmètre Sprint 1

- [x] Stack Docker Compose opérationnelle
- [x] PostgreSQL connecté, table `offers` créée
- [x] Seed de 10 offres fictives
- [x] `GET /v1/health` → 200
- [x] `GET /v1/offers` → liste paginée
- [x] `GET /v1/offers/{id}` → détail d'une offre
- [x] Frontend : page liste des offres
- [x] Frontend : page détail d'une offre

## Roadmap

| Sprint | Objectif |
|---|---|
| Sprint 1 | Socle technique + affichage offres fictives ✅ |
| Sprint 2 | Ingestion réelle (pages carrières + API France Travail) |
| Sprint 3 | Scoring LLM + qualification des offres |
| Sprint 4 | Génération brouillons de candidature |
| Sprint 5 | Validation humaine + soumission |
| Sprint 6 | Suivi candidatures + relances |
| Sprint 7 | Orchestration n8n + notifications |
| Sprint 8 | Agents LangGraph persistants |
