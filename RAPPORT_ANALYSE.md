# Rapport d'analyse — Agent Personnel de Recherche de Stage

> Généré le 2026-03-17 — Sprint 10 complet

---

## Résumé exécutif

Ce projet est une application web fullstack de gestion de candidatures de stage/alternance, composée
d'un backend FastAPI (Python 3.11 + SQLAlchemy 2.x + PostgreSQL 16) et d'un frontend Next.js 14
(TypeScript + Tailwind CSS). L'application intègre un moteur de scraping multi-sources (APEC, France
Travail, LinkedIn, WTTJ), un pipeline de déduplication en 5 niveaux, un module LLM local (Ollama),
une machine d'états pour les candidatures et un moteur de recommandations stratégiques (Sprint 10).
L'état global est bon : architecture solide, séparation des responsabilités respectée, tests présents,
mais plusieurs bugs mineurs et incohérences documentaires ont été détectés et corrigés.

---

## Ce qui est bien fait ✅

### 1. Architecture en couches strictement respectée
**Fichiers :** `app/api/v1/*.py`, `app/services/*.py`, `app/repositories/*.py`, `app/domain/`

Le pattern `Router → Service → Repository → ORM` est cohérent dans tout le projet. Les services
ne font jamais de requêtes SQL directes (ils passent par les repositories), les routers ne contiennent
pas de logique métier. Cette séparation facilite les tests et la maintenabilité.

### 2. Machine d'états applicative robuste
**Fichier :** `app/domain/state_machine.py`

Le graphe de transitions `ALLOWED_TRANSITIONS` est explicite, exhaustif et documenté. La fonction
`validate_transition()` lève `BusinessRuleError` (→ HTTP 400) avant toute mutation. Tous les statuts
terminaux (ARCHIVED) sont bien modélisés (ensemble vide de cibles). Testé et fonctionnel.

### 3. Déduplication en cascade 5 niveaux
**Fichier :** `app/services/offer_deduplicator.py`

L1 (URL exacte) → L2 (source+id externe) → L3 (SHA-256 contenu) → L4 (hash sémantique
inter-sources) → L5 (fuzzy title + société). Chaque niveau est documenté, a une confidence score
et retourne un `DeduplicationDecision` typé. Architecture sans effets de bord, testée.

### 4. Validation des entrées utilisateur avec Pydantic
**Fichier :** `app/api/schemas/application.py`

`RecruiterReplyCreate.message_text` est contraint avec `Field(min_length=1, max_length=5000)`.
Le champ `channel` est typé `Literal["email", "phone", "linkedin", "other"] | None`. Le validator
`FollowupCreate.must_be_future` rejette les dates dans le passé. Tout ceci produit des erreurs 422
automatiques sans code explicite dans les routers.

### 5. Service LLM avec cache à deux niveaux
**Fichier :** `app/services/llm/llm_service.py`

Cache in-memory (instantané) + cache DB (persistant entre redémarrages). Extraction JSON robuste
avec 3 fallbacks. Pas de dépendance externe au SDK Anthropic — utilise `httpx` pour appeler Ollama
directement. La fonction `normalize_list()` gère tous les types de réponses LLM (list, str CSV, None).

### 6. Eager-loading systématique pour éviter le N+1
**Fichiers :** `app/repositories/offer_repository.py`, `app/services/offer_priority_service.py`

`OfferRepository.get_all()` charge `company`, `primary_source` et `user_status` en une seule requête.
`OfferPriorityService.get_prioritized()` charge `llm_analysis` pour éviter le N+1 dans `SkillGapService`.
`OfferRepository.get_by_id()` charge toutes les relations liées à l'offre.

### 7. Gestion des erreurs domaine propre
**Fichier :** `app/domain/errors.py`, `app/api/v1/*.py`

`NotFoundError` → 404, `BusinessRuleError` → 400. Les routers transforment systématiquement ces
exceptions en HTTPException avec le bon code. Pas de logique de status code dans les services.

### 8. Event sourcing pour la timeline candidature
**Fichiers :** `app/repositories/application_event_repository.py`, `app/services/application_service.py`

Table `application_events` append-only. Le pattern `emit() + flush()` (sans commit) est respecté
dans le service — le commit est délégué à la fin de la transaction. Les events sont horodatés
et portent un payload JSON structuré.

### 9. Formule priority_score sans double-comptage
**Fichier :** `app/services/offer_priority_service.py`

Formule documentée et justifiée : `priority_score = 0.6 × ranking_score + 0.4 × matching_score`.
Freshness est déjà intégrée dans `ranking_score` (25/100 pts) — ne pas la recompter.

### 10. Tests unitaires couvrant les cas limites
**Fichiers :** `tests/test_sprint10.py`, `tests/test_sprint9.py`, `tests/test_deduplicator.py`

22 tests Sprint 10 couvrent les 4 types d'actions, la détection stale, le priority_score,
les skill gaps avec profil vide, et l'API `/v1/strategy/recommendations`. Les validations
Pydantic sont testées avec des cas positifs et négatifs.

---

## Bugs et erreurs ❌

### BUG 1 — `models/__init__.py` : `Application` et `ApplicationFollowup` manquants
**Fichier :** `app/infrastructure/db/models/__init__.py`

Les modèles `Application` et `ApplicationFollowup` ne sont pas importés dans l'`__init__.py`
du package `models`. SQLAlchemy doit enregistrer tous les modèles ORM avant de configurer les
relations. Lorsqu'un test ou un script importe `Offer` ou `ApplicationEvent` sans passer par
l'application complète, SQLAlchemy lève `InvalidRequestError` car il ne trouve pas `Application`
ou `ApplicationFollowup` pour résoudre les relations de type string (`"ApplicationFollowup"`).

**Code actuel (`__init__.py`) :**
```python
from app.infrastructure.db.models.application_event import ApplicationEvent
from app.infrastructure.db.models.candidate_profile import CandidateProfile
# ... (Application et ApplicationFollowup ABSENTS)
```

**Code corrigé :**
```python
from app.infrastructure.db.models.application import Application  # noqa: F401
from app.infrastructure.db.models.application_event import ApplicationEvent  # noqa: F401
from app.infrastructure.db.models.application_followup import ApplicationFollowup  # noqa: F401
from app.infrastructure.db.models.candidate_profile import CandidateProfile  # noqa: F401
# ...
```

---

### BUG 2 — Docstring obsolète dans `/v1/offers.py` (formule priority_score erronée)
**Fichier :** `app/api/v1/offers.py`, ligne 60

La docstring de l'endpoint `/prioritized` mentionne encore l'ancienne formule
`0.4 × ranking_score + 0.4 × matching_score + 0.2 × freshness_score` qui a été remplacée
lors des corrections Sprint 10. La formule effective dans `OfferPriorityService` est
`0.6 × ranking + 0.4 × matching`.

**Code actuel :**
```python
"""
Retourne les offres actives triées par priority_score décroissant.

priority_score = 0.4 × ranking_score + 0.4 × matching_score + 0.2 × freshness_score
"""
```

**Code corrigé :**
```python
"""
Retourne les offres actives triées par priority_score décroissant.

priority_score = 0.6 × ranking_score + 0.4 × matching_score
"""
```

---

### BUG 3 — Docstring obsolète dans `/v1/strategy.py` (même formule erronée)
**Fichier :** `app/api/v1/strategy.py`, ligne 41

Même problème que BUG 2 — l'ancienne formule avec freshness figure dans la docstring de
`get_strategy_recommendations()`.

**Code actuel :**
```python
- **prioritized_offers** : top offres actives selon priority_score composite
  (0.4 × ranking_score + 0.4 × matching_score + 0.2 × freshness)
```

**Code corrigé :**
```python
- **prioritized_offers** : top offres actives selon priority_score composite
  (0.6 × ranking_score + 0.4 × matching_score)
```

---

### BUG 4 — `app/main.py` : version et description obsolètes
**Fichier :** `app/main.py`, ligne 26

```python
# Actuel
description="API backend — Sprint 5",

# Corrigé
description="API backend — Sprint 10",
```

---

### BUG 5 — `.env.example` : variables LLM incorrectes (référencent Claude/Anthropic)
**Fichier :** `.env.example`, lignes 27-29

Le fichier `.env.example` mentionne `LLM_API_KEY` (clé Anthropic) et `LLM_MODEL=claude-sonnet-4-20250514`
mais le backend utilise Ollama local (`llm_base_url`, `llm_model_default`, `llm_model_hq`).
Ces variables ne sont pas lues par `config.py` et induisent les développeurs en erreur.

**Code actuel :**
```bash
# --- LLM (hors Sprint 1) ---
LLM_API_KEY=your-anthropic-api-key-here
LLM_MODEL=claude-sonnet-4-20250514
```

**Code corrigé :**
```bash
# --- LLM — Ollama local ---
# Ollama doit tourner localement (docker run -p 11434:11434 ollama/ollama)
LLM_BASE_URL=http://localhost:11434
LLM_MODEL_DEFAULT=gemma3n:e2b
LLM_MODEL_HQ=qwen2.5:7b-instruct
LLM_TIMEOUT_SECONDS=120
```

---

## Code de mauvaise qualité ⚠️

### 1. `OfferRankingService.score_all()` — commit direct
**Fichier :** `app/services/offer_ranking_service.py`, ligne 86

`score_all()` appelle `self.db.commit()` directement, alors que `score_offer()` (son homologue)
utilise correctement `self.db.flush()`. Cette incohérence rend `score_all()` incompatible avec
les transactions de test qui s'appuient sur le rollback final. Le commit doit être délégué à l'appelant.

```python
# Actuel — commit dans le service (mauvaise pratique)
def score_all(self, active_only: bool = True) -> int:
    # ...
    self.db.commit()  # ← problématique

# Conseillé — flush + commit délégué à l'appelant
def score_all(self, active_only: bool = True) -> int:
    # ...
    self.db.flush()
    logger.info("OfferRankingService: %d offres re-scorées", len(offers))
    return len(offers)
```

### 2. `_IN_MEMORY_CACHE` dans `llm_service.py` — cache non borné
**Fichier :** `app/services/llm/llm_service.py`, ligne 18

```python
_IN_MEMORY_CACHE: dict[str, str] = {}
```

Ce dictionnaire croît sans limite et sans TTL. En production avec des milliers de prompts
différents, cela peut saturer la RAM. Un `functools.lru_cache` ou une `maxsize` explicite
serait préférable.

**Solution recommandée :**
```python
from collections import OrderedDict
_MAX_CACHE_SIZE = 1000
_IN_MEMORY_CACHE: OrderedDict[str, str] = OrderedDict()

# Dans la fonction :
if len(_IN_MEMORY_CACHE) >= _MAX_CACHE_SIZE:
    _IN_MEMORY_CACHE.popitem(last=False)  # Éviction FIFO
_IN_MEMORY_CACHE[cache_key] = result_text
```

### 3. `/v1/offers/prioritized` — `response_model=list[dict]`
**Fichier :** `app/api/v1/offers.py`, ligne 52

`response_model=list[dict]` désactive complètement la validation de sortie et la génération
OpenAPI. L'endpoint `/v1/strategy/recommendations` utilise correctement `PrioritizedOfferOut`.
Ces deux endpoints exposant le même service devrait avoir le même schéma de sortie.

### 4. `get_candidates_for_fuzzy_match()` — charge 300 offres en mémoire
**Fichier :** `app/repositories/offer_repository.py`, ligne 175

La stratégie "charger 300 offres récentes puis filtrer en Python" est acceptable pour le volume
actuel mais ne passe pas à l'échelle. Si le volume dépasse 10 000 offres, cette méthode devient
un goulot d'étranglement. Une colonne `company_name_normalized` indexée serait plus efficace.

### 5. `conftest.py` — imports manuels de `Application` et `ApplicationFollowup`
**Fichier :** `tests/conftest.py`, lignes 30-31

Le conftest importe manuellement `Application` et `ApplicationFollowup` avec `# noqa: F401`
car ils ne figurent pas dans `models/__init__.py`. C'est un contournement du BUG 1.

---

## Ce qui manque / incomplet 🔧

### 1. Pas de rate limiting sur les endpoints API
Notamment sur `GET /v1/strategy/recommendations` qui appelle 3 services simultanément
(ApplicationStrategyService + OfferPriorityService + SkillGapService). Un utilisateur
malveillant peut saturer le backend avec des appels répétés.

### 2. `OfferPriorityService` charge toutes les offres actives en RAM
Sans pagination, cette méthode charge la totalité des offres actives pour les trier en Python.
À 10 000+ offres, la consommation mémoire devient problématique.

### 3. Aucun test unitaire pour les connecteurs
Les connecteurs (`apec.py`, `france_travail.py`, `indeed.py`, etc.) n'ont pas de tests.
Les erreurs de parsing HTML ou d'API externe ne sont pas couvertes.

### 4. Pas de monitoring des ingestions en temps réel
L'`IngestionRun` trace le résultat final mais il n'y a pas de moyen de suivre la progression
en temps réel (pas de webhook, pas de SSE, pas de polling endpoint).

### 5. Transition `SENT → INTERVIEW` manquante dans la machine d'états
Le graphe de transitions ne permet pas `SENT → INTERVIEW` directement — il faut passer par
`FOLLOW_UP_DUE`. Dans la réalité, un candidat peut recevoir une convocation directement après
l'envoi, sans relance.

### 6. `pytest.ini` — tests ne peuvent pas tourner sans PostgreSQL
```ini
# Le conftest tente de créer la base de test au démarrage
# Si PostgreSQL est absent → ImportError non rattrapé
```
Il n'existe pas de mode de test "SQLite" pour les développeurs sans Docker.

---

## Sécurité 🔒

### 1. ✅ Clé API statique — acceptable pour une V1 locale
La clé `APP_API_KEY` est transmise via header `Authorization: Bearer <key>`. Pour un outil
personnel en réseau local, c'est suffisant. À faire évoluer vers JWT/OAuth2 pour un déploiement
public.

### 2. ✅ Pas d'injection SQL
Toutes les requêtes utilisent SQLAlchemy ORM avec des paramètres liés. Pas de f-string dans
les requêtes. La recherche `func.lower(Offer.location_text).contains(city.lower())` est sûre
(contains() → LIKE avec binding).

### 3. ⚠️ Valeurs par défaut hardcodées dans `config.py`
```python
database_url: str = "postgresql://agent_user:agent_password@localhost:5432/agent_db"
app_api_key: str = "dev-api-key-changeme"
```
Ces valeurs par défaut "faibles" sont exposées si `.env` n'est pas configuré. Acceptable en
développement mais risqué si l'application est déployée sans configuration explicite.
**Recommandation :** Utiliser `None` comme défaut et lever une erreur au démarrage si absent.

### 4. ⚠️ `CORS allow_origins` sans restriction par défaut en développement
`allow_credentials=False` est correct, mais `cors_origins` inclut `http://localhost:3000`
par défaut. S'assurer que `BACKEND_CORS_ORIGINS` est explicitement configuré en production.

### 5. ✅ Pas de clés API dans le code source (`.gitignore` complet)
Le `.gitignore` exclut `.env`, `*.env`, les fichiers de credentials. Le `.env.example` ne
contient que des placeholders.

### 6. ✅ France Travail — OAuth2 client_credentials
Le connecteur FT utilise correctement OAuth2 avec token court-durée. Les credentials ne sont
jamais loggués.

---

## Résultats des tests 🧪

### Tests existants
- **Résultat :** Échoués au chargement — impossible de se connecter à PostgreSQL
- **Cause :** `conftest.py` tente de créer la base de test au démarrage du module
  (`_ensure_test_db_exists()` appelée à l'import). En dehors de Docker Compose, le host
  `postgres` est injoignable.
- **Nombre de fichiers de tests :** 20 fichiers, ~150+ cas de tests
- **Commande :** `python -m pytest tests/ -v` (nécessite PostgreSQL sur `postgres:5432`)

### Modules importables (sans DB)
| Module | Status |
|--------|--------|
| `app.domain.enums.*` | ✅ |
| `app.domain.state_machine` | ✅ |
| `app.domain.text_normalizer` | ✅ |
| `app.domain.errors` | ✅ |
| `app.config` | ✅ |
| `app.services.offer_scoring_service` | ✅ (avec imports manuels des modèles) |
| `app.services.application_strategy_service` | ✅ |
| `app.api.schemas.application` | ✅ |

### Tests fonctionnels manuels réalisés
| Test | Résultat |
|------|----------|
| `validate_transition()` — 6 cas | ✅ |
| `RecruiterReplyCreate` — validation vide/invalide/valide | ✅ |
| `OfferScoringService.score()` — Stage Data Scientist Paris | ✅ score=94, tags=[ai,data,ml] |
| `normalize_title_for_dedup()` et `normalize_title_for_search()` | ✅ |
| Imports domaine complets | ✅ |

### Erreurs rencontrées
- `psycopg2.OperationalError: could not translate host name "postgres"` — PostgreSQL absent
- `InvalidRequestError: Application failed to locate` — BUG 1 (corrigé)

---

## Améliorations prioritaires 🚀

1. **[Critique]** Ajouter `Application` et `ApplicationFollowup` dans `models/__init__.py`
   pour éviter les `InvalidRequestError` lors d'imports partiels de modèles ORM.

2. **[Critique]** Corriger les 2 docstrings avec l'ancienne formule `priority_score`
   (`offers.py` et `strategy.py`) — risque de confiance erronée dans la documentation.

3. **[Haute]** Corriger `.env.example` — remplacer les variables LLM Anthropic (inexistantes
   dans `config.py`) par les vraies variables Ollama.

4. **[Haute]** `OfferRankingService.score_all()` — remplacer `commit()` par `flush()`
   pour respecter la convention du projet et permettre les tests sans side-effects.

5. **[Haute]** Borner `_IN_MEMORY_CACHE` dans `llm_service.py` avec une taille maximale
   (ex. `OrderedDict` LRU à 1000 entrées) pour éviter les fuites mémoire en production.

6. **[Moyenne]** Remplacer `response_model=list[dict]` dans `/v1/offers/prioritized` par
   `response_model=list[PrioritizedOfferOut]` pour la documentation OpenAPI.

7. **[Moyenne]** Mettre à jour `main.py` description de "Sprint 5" à "Sprint 10".

8. **[Moyenne]** Ajouter la transition `SENT → INTERVIEW` dans la machine d'états
   pour couvrir les convocations directes.

9. **[Basse]** Ajouter un mode de test SQLite via une fixture alternative pour éviter
   la dépendance stricte à PostgreSQL en développement.

10. **[Basse]** Ajouter des tests pour les connecteurs (APEC, France Travail) avec
    des mocks httpx.

---

## Code amélioré

### Amélioration 1 — `models/__init__.py` complet (Critique)

```python
"""Import all ORM models to ensure they are registered with SQLAlchemy metadata."""
from app.infrastructure.db.models.application import Application  # noqa: F401
from app.infrastructure.db.models.application_event import ApplicationEvent  # noqa: F401
from app.infrastructure.db.models.application_followup import ApplicationFollowup  # noqa: F401
from app.infrastructure.db.models.candidate_profile import CandidateProfile  # noqa: F401
from app.infrastructure.db.models.company import Company  # noqa: F401
from app.infrastructure.db.models.ingestion_run import IngestionRun  # noqa: F401
from app.infrastructure.db.models.llm_cache import LLMCache  # noqa: F401
from app.infrastructure.db.models.offer import Offer  # noqa: F401
from app.infrastructure.db.models.offer_llm_analysis import OfferLLMAnalysis  # noqa: F401
from app.infrastructure.db.models.offer_raw import OfferRaw  # noqa: F401
from app.infrastructure.db.models.offer_user_status import OfferUserStatus  # noqa: F401
from app.infrastructure.db.models.profile_match_llm import ProfileMatchLLM  # noqa: F401
from app.infrastructure.db.models.source import Source  # noqa: F401
from app.infrastructure.db.models.user_preference import UserPreference  # noqa: F401
```

---

### Amélioration 2 — `llm_service.py` cache borné (Haute)

```python
from collections import OrderedDict

_MAX_CACHE_SIZE = 1_000  # Entrées max en mémoire (LRU-like)
_IN_MEMORY_CACHE: OrderedDict[str, str] = OrderedDict()


def _cache_put(key: str, value: str) -> None:
    """Insère dans le cache avec éviction FIFO si max atteint."""
    if key in _IN_MEMORY_CACHE:
        _IN_MEMORY_CACHE.move_to_end(key)
    else:
        if len(_IN_MEMORY_CACHE) >= _MAX_CACHE_SIZE:
            _IN_MEMORY_CACHE.popitem(last=False)
        _IN_MEMORY_CACHE[key] = value


# Remplacer toutes les occurrences :
# _IN_MEMORY_CACHE[cache_key] = result_text  →  _cache_put(cache_key, result_text)
```

---

### Amélioration 3 — `offers.py` endpoint prioritized typé (Moyenne)

```python
from app.api.schemas.strategy import PrioritizedOfferOut

@router.get(
    "/prioritized",
    response_model=list[PrioritizedOfferOut],
    summary="Offres priorisées par score composite",
)
def get_prioritized_offers(
    limit: int = Query(default=10, ge=1, le=50, description="Nombre d'offres à retourner"),
    db: Session = Depends(get_db),
) -> list[PrioritizedOfferOut]:
    """
    Retourne les offres actives triées par priority_score décroissant.

    priority_score = 0.6 × ranking_score + 0.4 × matching_score
    """
    items = OfferPriorityService(db).get_prioritized(limit=limit)
    return [
        PrioritizedOfferOut(
            offer_id=item["offer"].id,
            title=item["offer"].normalized_title,
            priority_score=item["priority_score"],
            ranking_score=item["ranking_score"],
            matching_score=item["matching_score"],
            location_text=item["offer"].location_text,
            company_name=item["offer"].company.name if item["offer"].company else None,
        )
        for item in items
    ]
```
