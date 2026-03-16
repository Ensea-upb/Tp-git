# Agent Personnel de Recherche de Stage

Copilote IA local de recherche de stage avec analyse LLM, scoring personnalisé et assistance à la candidature.

## Stack technique

| Composant | Technologie |
|---|---|
| Frontend | Next.js 14 + TypeScript + Tailwind CSS |
| Backend API | FastAPI (Python 3.12) |
| Base de données | PostgreSQL 16 |
| Migrations | Alembic |
| ORM | SQLAlchemy 2.x |
| LLM local | Ollama (gemma3n:e2b + qwen2.5:7b-instruct) |
| Déploiement | Docker / Docker Compose |

## Lancement rapide

### Prérequis

- Docker & Docker Compose
- [Ollama](https://ollama.com) installé **sur la machine hôte** (pas dans Docker)

### 1. Installer et démarrer Ollama

```bash
# Installer Ollama (Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Télécharger les deux modèles requis
ollama pull gemma3n:e2b          # ~1.5 GB — analyse d'offres (rapide, CPU)
ollama pull qwen2.5:7b-instruct  # ~4.7 GB — matching profil + génération (plus précis)

# Vérifier qu'Ollama tourne
ollama list
# → doit afficher gemma3n:e2b et qwen2.5:7b-instruct
```

> **Contrainte matérielle** — Le projet est calibré pour CPU-only (Intel i7-1165G7, 16 GB RAM,
> Iris Xe intégré). Les modèles choisis respectent cette contrainte :
> `gemma3n:e2b` ≈ 2B params (~2 GB RAM), `qwen2.5:7b-instruct` ≈ 7B params (~5 GB RAM).
> Les deux ne tournent **jamais simultanément**.

### 2. Démarrer la stack

```bash
cp .env.example .env
docker compose up --build

# Premier lancement uniquement
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/seed.py
```

### 3. Accès

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Santé API | http://localhost:8000/v1/health |

### Authentification API

Tous les endpoints (sauf `/v1/health`) requièrent :
```
Authorization: Bearer <APP_API_KEY>
```
Valeur par défaut en développement : `dev-api-key-changeme`

---

## Smoke test LLM (après premier lancement)

Ces commandes permettent de vérifier que le pipeline LLM fonctionne de bout en bout.
Remplacer `<OFFER_ID>` par l'UUID d'une offre existante (visible dans la liste des offres).

```bash
API="http://localhost:8000/v1"
AUTH="Authorization: Bearer dev-api-key-changeme"
OID="<OFFER_ID>"   # remplacer par un UUID réel

# 1. Créer un profil candidat
curl -s -X PUT "$API/candidate" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{
    "full_name": "Alice Martin",
    "current_level": "Master 2 Data Science",
    "school": "Paris Dauphine",
    "skills": ["Python", "Machine Learning", "SQL"],
    "tech_stack": ["Python", "Pandas", "scikit-learn", "PyTorch"],
    "target_domains": ["data", "ml"],
    "availability": "Avril 2026"
  }' | python3 -m json.tool

# 2. Déclencher l'analyse LLM de l'offre (retourne immédiatement 202)
curl -s -X POST "$API/offers/$OID/analyze" -H "$AUTH" | python3 -m json.tool

# 3. Attendre ~15–60 s (CPU inference), puis récupérer l'analyse
curl -s "$API/offers/$OID/analysis" -H "$AUTH" | python3 -m json.tool
# → analysis_status doit valoir "DONE"
# → summary, missions, skills_required, tech_stack doivent être renseignés

# 4. Déclencher le matching profil
curl -s -X POST "$API/offers/$OID/match-profile" -H "$AUTH" | python3 -m json.tool

# 5. Récupérer le résultat de matching (attendre ~30–90 s)
curl -s "$API/offers/$OID/match" -H "$AUTH" | python3 -m json.tool
# → match_status doit valoir "DONE"
# → match_score entre 0 et 100

# 6. Générer une lettre de motivation (bloquant, retourne le résultat directement)
curl -s -X POST "$API/offers/$OID/cover-letter" -H "$AUTH" | python3 -m json.tool
# → subject et body doivent être renseignés
```

### Via CLI (alternative)

```bash
# Analyser les 5 premières offres actives
docker compose exec backend python scripts/run_llm_analysis.py \
  --active-only --limit 5 --mode both

# Dry-run : afficher les offres sans appeler Ollama
docker compose exec backend python scripts/run_llm_analysis.py \
  --active-only --dry-run

# Ré-analyser une seule offre après modification du profil
docker compose exec backend python scripts/run_llm_analysis.py \
  --offer-id <UUID> --mode match
```

---

## Structure du projet

```
Tp-git/
├── backend/
│   ├── app/
│   │   ├── api/            # Endpoints et schémas Pydantic
│   │   ├── domain/         # Enums et règles métier
│   │   ├── infrastructure/ # DB, modèles ORM (11 tables)
│   │   ├── repositories/   # Accès données
│   │   └── services/
│   │       ├── llm/        # llm_service.py, prompt_builder.py
│   │       ├── offer_llm_analysis_service.py
│   │       ├── profile_matching_service.py
│   │       ├── application_assistant_service.py
│   │       ├── offer_scoring_service.py
│   │       └── personalized_offer_scoring_service.py
│   ├── alembic/            # Migrations 001→005
│   ├── scripts/            # seed.py, rescore_offers.py, run_llm_analysis.py
│   └── tests/
├── frontend/
│   └── src/
│       ├── app/            # Pages : offres, détail, préférences, profil
│       ├── components/     # OfferCard, FilterBar, OfferActions,
│       │                   # LLMAnalysisPanel, ProfileMatchPanel,
│       │                   # ApplicationAssistant
│       ├── lib/            # api.ts, constants.ts
│       └── types/          # offer.ts, preferences.ts, analysis.ts
└── DETTE_TECHNIQUE.md
```

## Tests

```bash
# Dans le conteneur (avec PostgreSQL disponible)
docker compose exec backend pytest tests/ -v

# Tests unitaires sans DB (LLM mocké)
docker compose exec backend pytest tests/test_llm_service.py \
  tests/test_normalize_list.py tests/test_offer_analysis.py -v
```

## Variables d'environnement

Voir `.env.example` pour la liste complète.

Variables critiques :

| Variable | Rôle | Défaut |
|---|---|---|
| `DATABASE_URL` | Connexion PostgreSQL | — |
| `APP_API_KEY` | Authentification API | `dev-api-key-changeme` |
| `LLM_BASE_URL` | Endpoint Ollama | `http://localhost:11434` |
| `LLM_MODEL_DEFAULT` | Modèle analyse (rapide) | `gemma3n:e2b` |
| `LLM_MODEL_HQ` | Modèle matching/génération | `qwen2.5:7b-instruct` |
| `LLM_TIMEOUT_SECONDS` | Timeout requête Ollama | `120` |

## Périmètre par sprint

| Sprint | Objectif | Statut |
|---|---|---|
| Sprint 1 | Socle Docker, affichage offres fictives | ✅ |
| Sprint 2 | Ingestion réelle (France Travail + pages carrières) | ✅ |
| Sprint 3 | Observabilité, scoring déterministe, admin API, filtres frontend | ✅ |
| Sprint 4 | Préférences utilisateur, scoring personnalisé, actions offres | ✅ |
| Sprint 5 | Copilote IA local (Ollama) : analyse, matching, assistant candidature | ✅ |
| Sprint 6 | — | 🔜 |
