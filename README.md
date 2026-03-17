# Agent Personnel de Recherche de Stage

Copilote IA local de recherche de stage/emploi avec ingestion multi-sources, scoring personnalisé, pipeline de candidature avec machine à états, et moteur de stratégie.

---

## Stack technique

| Composant | Technologie | Version |
|-----------|-------------|---------|
| Frontend | Next.js + TypeScript + Tailwind CSS | 14.2 / 18.3 / 5.7 |
| Backend API | FastAPI + Uvicorn | 0.115 / 0.32 |
| ORM | SQLAlchemy | 2.0.36 |
| Migrations | Alembic | 1.14 |
| Base de données | PostgreSQL | 16-alpine |
| LLM local | Ollama (gemma3n:e2b + qwen2.5:7b-instruct) | — |
| Déduplication fuzzy | RapidFuzz | 3.10 |
| Scraping | BeautifulSoup4 + lxml | 4.12 / 5.3 |
| Tests | Pytest | 8.3 |
| Déploiement | Docker Compose | — |

---

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
ollama pull qwen2.5:7b-instruct  # ~4.7 GB — matching profil + génération (précis)

# Vérifier qu'Ollama est actif
ollama list
# → doit afficher gemma3n:e2b et qwen2.5:7b-instruct
```

> **Contrainte matérielle** — Le projet est calibré pour CPU-only (Intel i7-1165G7, 16 GB RAM).
> `gemma3n:e2b` ≈ 2B params (~2 GB RAM), `qwen2.5:7b-instruct` ≈ 7B params (~5 GB RAM).
> Les deux modèles ne tournent **jamais simultanément**.

### 2. Démarrer la stack

```bash
cp .env.example .env
docker compose up --build

# Premier lancement uniquement — migrations + données de seed
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/seed.py
```

### 3. Accès

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| Redoc | http://localhost:8000/redoc |
| Santé API | http://localhost:8000/v1/health |

### Authentification API

Tous les endpoints (sauf `GET /v1/health`) requièrent :
```
Authorization: Bearer <APP_API_KEY>
```
Valeur par défaut en développement : `dev-api-key-changeme`

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Frontend  (Next.js 14 + TypeScript)            │
│  Pages : offres, candidatures, profil, stratégie│
└───────────────────┬─────────────────────────────┘
                    │ HTTP / Bearer auth
┌───────────────────▼─────────────────────────────┐
│  API Layer  (FastAPI + Pydantic v2)             │
│  13 routers — validation, sérialisation         │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│  Service Layer  (17 services)                   │
│  Logique métier, orchestration LLM, stratégie   │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│  Repository Layer  (14 repositories)            │
│  Accès données, requêtes SQLAlchemy             │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│  PostgreSQL 16  (14 tables, 10 migrations)      │
│  JSONB · ARRAY · UUID · CASCADE · index         │
└─────────────────────────────────────────────────┘

                    +
┌─────────────────────────────────────────────────┐
│  Ollama  (hôte, hors Docker)                    │
│  gemma3n:e2b  ·  qwen2.5:7b-instruct            │
└─────────────────────────────────────────────────┘
```

**Règle d'architecture strictement respectée** : `Router → Service → Repository → ORM`.
Aucune logique métier dans les routers ou repositories. Aucun accès DB direct depuis les services sans passer par un repository.

---

## Structure du projet

```
Tp-git/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── schemas/        # DTOs Pydantic (offer, application, strategy…)
│   │   │   └── v1/             # 13 routers FastAPI
│   │   │       ├── offers.py         # GET /offers, /offers/prioritized
│   │   │       ├── offer_actions.py  # favorite, shortlist, apply, reject
│   │   │       ├── analysis.py       # LLM analyze, match-profile
│   │   │       ├── assistant.py      # cover-letter, email, interview-prep
│   │   │       ├── applications.py   # pipeline, timeline, stats
│   │   │       ├── strategy.py       # GET /strategy/recommendations
│   │   │       ├── sources.py
│   │   │       ├── ingestion.py
│   │   │       ├── preferences.py
│   │   │       ├── candidate.py
│   │   │       └── health.py
│   │   ├── connectors/         # 6 adaptateurs sources d'offres
│   │   │   ├── france_travail.py
│   │   │   ├── apec.py
│   │   │   ├── indeed.py
│   │   │   ├── linkedin.py
│   │   │   ├── welcome_to_the_jungle.py
│   │   │   └── http_career_page.py
│   │   ├── domain/
│   │   │   ├── enums/          # 7 enums StrEnum
│   │   │   ├── dto/            # 5 DTOs (raw/normalized offer, ingestion…)
│   │   │   ├── state_machine.py  # transitions ApplicationStatus
│   │   │   ├── errors.py         # NotFoundError, BusinessRuleError
│   │   │   └── text_normalizer.py
│   │   ├── infrastructure/
│   │   │   └── db/
│   │   │       ├── models/     # 14 modèles ORM
│   │   │       ├── base.py
│   │   │       └── session.py
│   │   ├── repositories/       # 14 repositories
│   │   └── services/           # 17 services
│   │       ├── llm/            # llm_service.py, prompt_builder.py
│   │       ├── offer_ingestion_service.py
│   │       ├── offer_normalizer.py
│   │       ├── offer_deduplicator.py
│   │       ├── offer_ranking_service.py
│   │       ├── offer_scoring_service.py
│   │       ├── offer_priority_service.py
│   │       ├── personalized_offer_scoring_service.py
│   │       ├── application_service.py
│   │       ├── application_strategy_service.py
│   │       ├── application_assistant_service.py
│   │       ├── followup_recommendation_service.py
│   │       ├── interview_preparation_service.py
│   │       ├── skill_gap_service.py
│   │       ├── offer_llm_analysis_service.py
│   │       ├── profile_matching_service.py
│   │       └── source_connector_manager.py
│   ├── alembic/
│   │   └── versions/           # 10 migrations (001 → 010)
│   ├── scripts/                # seed.py, rescore_offers.py, run_llm_analysis.py
│   └── tests/                  # 22 modules, ~180+ assertions
├── frontend/
│   └── src/
│       ├── app/                # 7 pages Next.js
│       │   ├── page.tsx              # Dashboard
│       │   ├── offers/page.tsx       # Liste des offres
│       │   ├── offers/[id]/page.tsx  # Détail offre
│       │   ├── applications/page.tsx # Pipeline Kanban + StrategyPanel
│       │   ├── profile/page.tsx
│       │   └── preferences/page.tsx
│       ├── components/         # 13 composants React
│       │   ├── OfferCard.tsx
│       │   ├── FilterBar.tsx
│       │   ├── OfferActions.tsx
│       │   ├── LLMAnalysisPanel.tsx
│       │   ├── ProfileMatchPanel.tsx
│       │   ├── ApplicationAssistant.tsx
│       │   ├── ApplicationPipeline.tsx   # Kanban 7 colonnes
│       │   ├── ApplicationColumn.tsx
│       │   ├── ApplicationCard.tsx
│       │   ├── ApplicationTimeline.tsx
│       │   ├── StrategyPanel.tsx
│       │   └── StateChip.tsx
│       ├── lib/
│       │   ├── api.ts          # Client HTTP centralisé (Bearer auth)
│       │   └── constants.ts
│       └── types/              # offer.ts, application.ts, analysis.ts,
│                               # preferences.ts, strategy.ts
└── docker-compose.yml
```

---

## Domaine métier

### Machine à états — `ApplicationStatus`

```
DRAFT ──→ READY_TO_SEND ──→ SENT ──→ FOLLOW_UP_DUE ──┬──→ INTERVIEW
  │              │             │            │          │       │
  └──────────────┴─────────────┴────────────┴──→ ARCHIVED ←───┤
                                                               ├──→ REJECTED ──→ ARCHIVED
                                                               └──→ ACCEPTED ──→ ARCHIVED
```

Toute transition non listée lève `BusinessRuleError`. `ARCHIVED` est terminal.

### Pipeline d'offre — `OfferState` (13 états)

```
DETECTED → RAW_STORED → NORMALIZED → DEDUPLICATED → ANALYZED
                                                        ↓
                                        REJECTED    QUALIFIED
                                                        ↓
                                        DRAFT_REQUESTED → DRAFT_PREPARED
                                                               ↓
                                                    READY_FOR_REVIEW
                                                               ↓
                                        SUBMISSION_IN_PROGRESS → SUBMITTED → CLOSED
```

### Déduplication en cascade (5 niveaux)

| Niveau | Critère | Mécanisme |
|--------|---------|-----------|
| L1 | URL exacte | Contrainte UNIQUE |
| L2 | `source_id + external_offer_id` | Contrainte composite |
| L3 | SHA-256 du contenu normalisé | Champ `checksum` |
| L4 | Hash sémantique cross-sources | Champ `semantic_hash` (calculé à l'ingestion) |
| L5 | Titre fuzzy ≥ 85% | RapidFuzz + `normalize_title_for_dedup()` |

`normalize_title_for_dedup()` préserve les indicateurs de type (stage/CDI/alternance/junior/senior) pour éviter les faux positifs entre contrats différents.

---

## Scoring des offres

### `ranking_score` (0–100) — calculé à l'ingestion

| Composante | Poids | Critères |
|------------|-------|---------|
| Fraîcheur | 25 pts | < 7 j = 25, décroissance linéaire jusqu'à 0 à 90 j |
| Pertinence titre | 25 pts | Mots-clés data/ML/AI/Python/SQL… (≥ 3 = 25 pts) |
| Localisation | 25 pts | Paris/IDF/remote = 25, villes secondaires = 15, HYBRID = 12 |
| Fiabilité source | 25 pts | WTTJ/LinkedIn = 25, APEC = 22, Indeed = 18, inconnu = 12 |

### `priority_score` (0–100) — calculé à la demande

```
priority_score = 0.6 × ranking_score + 0.4 × matching_score
```

- `ranking_score` intègre déjà la fraîcheur — aucun double comptage
- `matching_score` = `personalized_score` si disponible, sinon `global_score`

---

## API — Référence des endpoints

Tous les endpoints requièrent `Authorization: Bearer <APP_API_KEY>` sauf `/v1/health`.

### Offres

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/v1/offers` | Liste paginée (filtres : état, source, ville, score, work_mode, user_status, tri) |
| `GET` | `/v1/offers/prioritized` | Top offres par `priority_score` composite |
| `GET` | `/v1/offers/{id}` | Détail complet |
| `POST/DELETE` | `/v1/offers/{id}/favorite` | Marquer/retirer favori |
| `POST/DELETE` | `/v1/offers/{id}/shortlist` | Ajouter/retirer de la shortlist |
| `POST/DELETE` | `/v1/offers/{id}/apply` | Marquer/annuler candidature directe |
| `POST/DELETE` | `/v1/offers/{id}/reject` | Rejeter/annuler rejet |

### Analyse LLM

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/v1/offers/{id}/analyze` | Déclenche l'analyse (202 — tâche de fond) |
| `GET` | `/v1/offers/{id}/analysis` | Résultat (`analysis_status: DONE`) |
| `POST` | `/v1/offers/{id}/match-profile` | Déclenche le matching (202 — tâche de fond) |
| `GET` | `/v1/offers/{id}/match` | Résultat (`match_status: DONE`, `match_score: 0–100`) |

### Assistant candidature (LLM sync)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/v1/offers/{id}/cover-letter` | Génère une lettre de motivation |
| `POST` | `/v1/offers/{id}/email` | Génère un email de candidature |
| `POST` | `/v1/offers/{id}/interview-prep` | Génère des questions d'entretien |

### Candidatures

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/v1/applications` | Crée une candidature (DRAFT + drafts LLM en background) |
| `GET` | `/v1/applications` | Liste paginée avec filtre statut |
| `GET` | `/v1/applications/stats` | Statistiques (total, entretiens, refus, taux réponse) |
| `GET` | `/v1/applications/{id}` | Détail |
| `PATCH` | `/v1/applications/{id}/status` | Transition via machine à états |
| `POST` | `/v1/applications/{id}/followup` | Planifie une relance |
| `GET` | `/v1/applications/{id}/timeline` | Historique chronologique des événements |
| `POST` | `/v1/applications/{id}/recruiter-reply` | Enregistre une réponse recruteur |
| `GET` | `/v1/applications/{id}/followup-recommendation` | Recommande un délai de relance |
| `POST` | `/v1/applications/{id}/interview-prep` | Préparation contextuelle (LLM, non persisté) |

### Stratégie

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/v1/strategy/recommendations` | Actions recommandées + offres priorisées + skill gaps |

### Administration

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET/POST/PATCH` | `/v1/sources` | Gestion des sources d'offres |
| `POST` | `/v1/ingestion/run` | Déclenche un run d'ingestion |
| `GET` | `/v1/ingestion/runs` | Historique des runs |
| `GET/PUT` | `/v1/preferences` | Préférences utilisateur (singleton) |
| `GET/PUT` | `/v1/candidate` | Profil candidat (singleton) |
| `GET` | `/v1/health` | Santé de l'API (public) |

---

## Module stratégie

`GET /v1/strategy/recommendations` retourne en une seule réponse :

```json
{
  "actions": [
    {
      "action_type": "PREPARE_INTERVIEW",
      "reason": "Candidature en phase d'entretien — préparez vos réponses.",
      "priority": 3,
      "application_id": "..."
    },
    {
      "action_type": "APPLY_NOW",
      "reason": "Offre très bien notée (score 84/100) — postulez sans attendre.",
      "priority": 3,
      "offer_id": "..."
    },
    {
      "action_type": "SEND_FOLLOWUP",
      "reason": "Relance planifiée en attente d'envoi.",
      "priority": 2,
      "application_id": "..."
    },
    {
      "action_type": "ARCHIVE_STALE",
      "reason": "Sans nouvelles depuis plus de 21 jours.",
      "priority": 1,
      "application_id": "..."
    }
  ],
  "prioritized_offers": [
    {
      "offer_id": "...",
      "title": "Data Engineer",
      "priority_score": 78.4,
      "ranking_score": 82.0,
      "matching_score": 72.0,
      "company_name": "Acme Corp",
      "location_text": "Paris"
    }
  ],
  "skill_gaps": [
    {
      "offer_id": "...",
      "offer_title": "Data Engineer",
      "missing_skills": ["airflow", "dbt", "kafka"]
    }
  ]
}
```

**Règles de déclenchement** :

| Action | Condition |
|--------|-----------|
| `PREPARE_INTERVIEW` (priorité 3) | `status = INTERVIEW` |
| `APPLY_NOW` (priorité 3) | `ranking_score ≥ 70`, actif, pas de candidature en cours (DRAFT→INTERVIEW) |
| `SEND_FOLLOWUP` (priorité 2) | `status = FOLLOW_UP_DUE` |
| `ARCHIVE_STALE` (priorité 1) | `status = SENT` + dernier événement > 21 jours (ou aucun événement) |

---

## Événements timeline (`application_events`)

| Type | Émis par | Payload exemple |
|------|----------|-----------------|
| `APPLICATION_CREATED` | `create()` | `{"source_channel": "linkedin"}` |
| `STATUS_CHANGED` | `update_status()`, `add_followup()` | `{"from": "SENT", "to": "FOLLOW_UP_DUE"}` |
| `FOLLOWUP_SCHEDULED` | `add_followup()` | `{"scheduled_at": "2024-05-15T10:00:00Z"}` |
| `RECRUITER_REPLIED` | `add_recruiter_reply()` | `{"message_text": "...", "channel": "email"}` |
| `DRAFTS_READY` | background LLM task | `{"cover_letter_ready": true}` |

Les événements sont append-only. Émis avec `flush()` sans `commit()` — le service parent committe de façon atomique (opération + événement dans la même transaction).

---

## Tests

```bash
# Tous les tests (nécessite PostgreSQL actif)
docker compose exec backend pytest tests/ -v

# Tests unitaires sans DB (LLM mocké)
docker compose exec backend pytest tests/test_llm_service.py \
  tests/test_normalize_list.py tests/test_offer_analysis.py -v

# Tests d'un sprint spécifique
docker compose exec backend pytest tests/test_sprint10.py -v

# Avec couverture
docker compose exec backend pytest tests/ --cov=app --cov-report=term-missing
```

### Modules de tests

| Module | Domaine couvert |
|--------|-----------------|
| `test_sprint8.py` | Normalisation titre (dedup vs search), ranking à l'ingestion, COALESCE score_min |
| `test_sprint9.py` | Timeline, réponse recruteur (validation), stats, recommandation relance |
| `test_sprint10.py` | Stratégie (4 actions), stale detection 21 j, priority_score, skill gaps |
| `test_applications.py` | CRUD candidatures, transitions machine à états |
| `test_scoring.py` | Scoring déterministe et personnalisé |
| `test_deduplicator.py` | Fuzzy matching L5, seuil 85%, faux positifs |
| `test_normalizer.py` | `normalize_title_for_dedup` vs `normalize_title_for_search` |
| `test_llm_service.py` | Intégration Ollama (mocké, sans GPU requis) |
| `test_candidate.py` | Profil candidat singleton |
| `test_preferences.py` | Préférences utilisateur |
| `test_offer_actions.py` | Actions offres (favorite, apply, reject) |

---

## Variables d'environnement

Voir `.env.example` pour la liste complète.

| Variable | Rôle | Défaut |
|----------|------|--------|
| `DATABASE_URL` | Connexion PostgreSQL | — |
| `APP_API_KEY` | Authentification Bearer | `dev-api-key-changeme` |
| `LLM_BASE_URL` | Endpoint Ollama | `http://localhost:11434` |
| `LLM_MODEL_DEFAULT` | Modèle analyse rapide | `gemma3n:e2b` |
| `LLM_MODEL_HQ` | Modèle matching/génération | `qwen2.5:7b-instruct` |
| `LLM_TIMEOUT_SECONDS` | Timeout inference CPU | `120` |
| `BACKEND_CORS_ORIGINS` | Origines CORS autorisées | `http://localhost:3000` |
| `NEXT_PUBLIC_API_URL` | URL API depuis le frontend | `http://localhost:8000` |
| `APP_ENV` | Environnement (`development`/`production`) | `development` |

---

## Smoke test LLM (après premier lancement)

```bash
API="http://localhost:8000/v1"
AUTH="Authorization: Bearer dev-api-key-changeme"
OID="<OFFER_ID>"   # remplacer par un UUID réel (visible dans /v1/offers)

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

# 2. Déclencher l'analyse LLM (retourne 202 immédiatement)
curl -s -X POST "$API/offers/$OID/analyze" -H "$AUTH" | python3 -m json.tool

# 3. Récupérer l'analyse (~15–60 s sur CPU)
curl -s "$API/offers/$OID/analysis" -H "$AUTH" | python3 -m json.tool
# → analysis_status: "DONE", skills_required, missions renseignés

# 4. Matching profil/offre
curl -s -X POST "$API/offers/$OID/match-profile" -H "$AUTH" | python3 -m json.tool
curl -s "$API/offers/$OID/match" -H "$AUTH" | python3 -m json.tool
# → match_status: "DONE", match_score: 0–100

# 5. Recommandations stratégiques du jour
curl -s "$API/strategy/recommendations" -H "$AUTH" | python3 -m json.tool
```

### Via script CLI

```bash
# Analyser les 5 premières offres actives
docker compose exec backend python scripts/run_llm_analysis.py \
  --active-only --limit 5 --mode both

# Dry-run (sans appel Ollama)
docker compose exec backend python scripts/run_llm_analysis.py \
  --active-only --dry-run

# Re-scorer toutes les offres (ranking_score)
docker compose exec backend python scripts/rescore_offers.py
```

---

## Base de données — 14 tables

| Table | Rôle |
|-------|------|
| `sources` | Sources d'offres (France Travail, APEC, LinkedIn…) |
| `companies` | Entreprises |
| `offers_raw` | Offres brutes avant normalisation |
| `offers` | Offres normalisées (entité centrale) |
| `offer_user_statuses` | Statut utilisateur par offre (FAVORITE, APPLIED…) |
| `offer_llm_analyses` | Analyses LLM structurées (missions, skills, tech_stack…) |
| `profile_match_llm` | Résultats matching profil/offre |
| `candidate_profiles` | Profil candidat (singleton `DEFAULT_CANDIDATE_ID`) |
| `user_preferences` | Préférences de recherche (singleton) |
| `llm_cache` | Cache requêtes LLM (évite les re-inférences) |
| `applications` | Candidatures créées par l'utilisateur |
| `application_events` | Timeline append-only (event sourcing léger) |
| `application_followups` | Relances planifiées |
| `ingestion_runs` | Historique et métriques des runs d'ingestion |

---

## Périmètre par sprint

| Sprint | Objectif | Statut |
|--------|----------|--------|
| Sprint 1 | Socle Docker, affichage offres fictives | ✅ |
| Sprint 2 | Ingestion réelle (France Travail + pages carrières) | ✅ |
| Sprint 3 | Observabilité, scoring déterministe, admin API, filtres frontend | ✅ |
| Sprint 4 | Préférences utilisateur, scoring personnalisé, actions offres | ✅ |
| Sprint 5 | Copilote IA local (Ollama) : analyse LLM, matching profil, assistant candidature | ✅ |
| Sprint 6 | Pipeline candidature : machine à états, Kanban frontend 7 colonnes | ✅ |
| Sprint 7 | Lettre de motivation, email, préparation entretien (LLM + drafts background) | ✅ |
| Sprint 8 | Normalisation texte (dedup vs search), déduplication fuzzy L5, ranking à l'ingestion, COALESCE score_min | ✅ |
| Sprint 9 | Timeline événements, réponse recruteur validée, recommandation relance, stats candidatures, préparation entretien contextuelle | ✅ |
| Sprint 10 | Moteur de stratégie (APPLY_NOW/SEND_FOLLOWUP/PREPARE_INTERVIEW/ARCHIVE_STALE), offres priorisées, skill gaps, StrategyPanel | ✅ |
| Sprint 11 | — | 🔜 |
