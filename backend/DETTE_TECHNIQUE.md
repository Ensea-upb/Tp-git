# Dette Technique

Suivi des dettes techniques acceptées, triées par sprint d'introduction.
Format : `DT-XX | Description | Sévérité | Sprint cible`

---

## Sprint 5 — LLM Copilot

| Réf | Description | Sévérité | Sprint cible |
|---|---|---|---|
| DT-01 | `_IN_MEMORY_CACHE` (dict) non borné — peut croître sans limite en prod longue durée | Medium | Sprint 7 |
| DT-02 | `raw_response` absent de `OfferLLMAnalysis` en cas de succès — impossibilité de rejouer le parsing sans ré-appel LLM | Medium | Sprint 6 ✅ reporté Sprint 7 |
| DT-03 | `temperature` exclue de la clé de cache — deux appels avec températures différentes retournent le même résultat mis en cache | Low | Sprint 7+ |
| DT-04 | Tests d'intégration couplés à PostgreSQL — impossible de lancer sans Docker Compose | High | Sprint 6 ✅ inchangé |

---

## Sprint 6 — Pipeline de candidatures

### Corrections appliquées en post-review

Les points suivants identifiés lors de la revue Sprint 6 ont été **corrigés avant Sprint 7** :

- **Fix 1** : `add_followup` rendu atomique — commit unique pour le follow-up + la mise à jour de statut.
- **Fix 2** : `update_status` protège les états terminaux (`REJECTED`, `ACCEPTED`, `ARCHIVED`) — `BusinessRuleError` → HTTP 400.
- **Fix 3** : Champ `drafts_ready` ajouté au modèle + migration 008 — l'UI distingue désormais "génération en cours", "brouillons disponibles" et "LLM indisponible".
- **Fix 4** : `scheduled_at` validé strictement dans le futur par `@field_validator` Pydantic — HTTP 422 si date passée.
- **Fix 5** : `add_followup` restreint aux statuts `SENT`, `FOLLOW_UP_DUE`, `INTERVIEW` — `BusinessRuleError` → HTTP 400 sinon.
- **Fix 6** : Introduction de `domain/errors.py` (`NotFoundError`, `BusinessRuleError`) — séparation claire 404 / 400 dans le router.

### Dettes restantes Sprint 6

| Réf | Description | Sévérité | Sprint cible |
|---|---|---|---|
| DT-S6-01 | Pas de graphe de transitions complet — seuls les états terminaux sont bloqués. Transitions incohérentes restantes : ex. `INTERVIEW → DRAFT` | Medium | Sprint 7 |
| DT-S6-02 | `ApplicationAssistantService` appelle `db.commit()` en interne (pour le cache LLM) alors qu'il est utilisé dans une session background isolée — couplage implicite | Low | Sprint 7 |
| DT-S6-03 | Pas de contrainte d'unicité DB sur `(offer_id)` dans `applications` — plusieurs candidatures pour la même offre acceptées silencieusement | Low | Sprint 8 |
| DT-S6-04 | `scheduleFollowup()` côté frontend fixe systématiquement J+7 sans input utilisateur | Low | Sprint 7 |
| DT-S6-05 | `GET /v1/applications` sans filtre ni pagination — liste complète retournée à chaque render Kanban | Medium | Sprint 7 |
