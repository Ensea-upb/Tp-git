# Dette technique — Sprint 5

Document de suivi des dettes acceptées lors de Sprint 5.
À traiter avant mise en service réelle ou selon la priorité indiquée.

---

## DT-01 — Cache mémoire LLM non borné

**Fichier :** `backend/app/services/llm/llm_service.py:18`

```python
_IN_MEMORY_CACHE: dict[str, str] = {}
```

**Problème :** Dictionnaire global de processus, sans TTL, sans taille maximale, sans éviction.
Chaque prompt unique (≈ 2–5 KB par entrée) est retenu pour toute la durée de vie du processus.
À 1 000 offres analysées, la consommation mémoire additionnelle est de l'ordre de 5–50 MB —
acceptable aujourd'hui, non acceptable en production continue.

**Correction cible :** Remplacer par une structure LRU bornée (500 entrées maximum) :

```python
from functools import lru_cache
# ou
from collections import OrderedDict

MAX_MEMORY_CACHE = 500
```

**Priorité :** Moyenne. À corriger avant Sprint 7 ou si la base d'offres dépasse 2 000 entrées.

---

## DT-02 — `raw_response` absent sur les analyses réussies

**Fichiers :** `offer_llm_analysis_service.py`, `profile_matching_service.py`

**Problème :** Le champ `raw_response` (colonne Text en DB) n'est renseigné que sur `FAILED`.
Sur `DONE`, le texte brut généré par le modèle est perdu après parsing. Il est impossible de :
- diagnostiquer une mauvaise extraction sans relancer l'inférence,
- auditer ce que le modèle a réellement produit,
- détecter des dérives de qualité entre deux versions de modèle.

**Correction cible :** Stocker systématiquement le texte brut, tronqué à 512 caractères :

```python
analysis.raw_response = raw[:512] if raw else None  # raw = résultat brut de call_llm()
```

Nécessite de faire remonter la valeur brute de `call_llm_json` vers les services
(actuellement `call_llm_json` retourne uniquement le JSON parsé).

**Priorité :** Moyenne. Bloquant pour tout travail de qualité modèle en Sprint 6+.

---

## DT-03 — Température absente de la clé de cache LLM

**Fichier :** `backend/app/services/llm/llm_service.py:21-23`

```python
def _build_cache_key(model: str, prompt: str) -> str:
    raw = f"{model}:{prompt}"   # temperature et max_tokens exclus
    return hashlib.sha256(raw.encode()).hexdigest()
```

**Problème :** Un appel `temperature=0.0` et un appel `temperature=0.3` sur le même prompt
retournent le résultat mis en cache par le premier appel. En pratique, les prompts diffèrent
entre features (analyse vs lettre de motivation), donc aucune collision réelle aujourd'hui.
Mais l'invariant est fragile : si deux features utilisent le même prompt avec des températures
différentes, le comportement est silencieusement incorrect.

**Correction cible :**

```python
def _build_cache_key(model: str, prompt: str, temperature: float) -> str:
    raw = f"{model}:{temperature}:{prompt}"
    return hashlib.sha256(raw.encode()).hexdigest()
```

**Priorité :** Faible. Aucun cas de collision actuel. À corriger si la clé de cache est exposée
dans une API d'audit ou si `temperature` devient paramétrable par l'utilisateur.

---

## DT-04 — Tests d'intégration dépendants de PostgreSQL

**Fichiers :** `backend/tests/conftest.py`, `backend/tests/test_offer_analysis.py` (idempotence),
`backend/tests/test_candidate.py`, `backend/tests/test_preferences.py`, etc.

**Problème :** Le `conftest.py` appelle `_ensure_test_db_exists()` au chargement du module,
ce qui rend **tous** les tests — y compris les tests unitaires purs — non exécutables sans
une instance PostgreSQL disponible. En l'absence de base de données (CI minimal, développement
hors ligne), toute la suite de tests échoue à l'import du conftest.

Conséquences concrètes :
- Les tests unitaires de `test_normalize_list.py` et `test_llm_service.py` nécessitent une DB
  alors qu'ils n'en ont pas besoin.
- Il n'est pas possible de valider la logique métier pure en environnement sans Docker.

**Correction cible :** Séparer les tests unitaires des tests d'intégration via une structure
de répertoires distincte ou un marqueur pytest, avec un conftest léger pour les tests unitaires :

```
tests/
├── unit/          # conftest minimal, aucune DB
│   ├── test_normalize_list.py
│   ├── test_llm_service.py
│   └── test_offer_analysis.py  # (partie service uniquement)
└── integration/   # conftest avec DB
    ├── test_idempotency.py
    ├── test_candidate.py
    └── ...
```

**Priorité :** Haute pour la maintenabilité. À traiter en début de Sprint 6 si des pipelines CI
sont mis en place. Acceptée pour l'instant car l'environnement de développement cible inclut
Docker Compose avec PostgreSQL.

---

## Récapitulatif

| ID | Libellé | Impact | Priorité | Sprint cible |
|---|---|---|---|---|
| DT-01 | Cache mémoire non borné | Mémoire | Moyenne | Sprint 7 |
| DT-02 | `raw_response` absent sur succès | Auditabilité | Moyenne | Sprint 6 |
| DT-03 | Température hors clé de cache | Correction silencieuse | Faible | Sprint 7+ |
| DT-04 | Tests unitaires couplés à PostgreSQL | Maintenabilité CI | Haute | Sprint 6 |
