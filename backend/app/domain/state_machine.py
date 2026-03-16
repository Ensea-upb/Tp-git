"""
Machine de transitions pour ApplicationStatus.

Chaque statut possède un ensemble explicite de cibles autorisées.
Toute transition absente de ce graphe lève BusinessRuleError.

Règle spéciale : ANY → ARCHIVED (tout statut peut être archivé,
sauf ARCHIVED lui-même qui est terminal).
"""
from app.domain.enums.application_status import ApplicationStatus as S
from app.domain.errors import BusinessRuleError

# Graphe de transitions : source → {cibles autorisées}
ALLOWED_TRANSITIONS: dict[S, frozenset[S]] = {
    S.DRAFT:          frozenset({S.READY_TO_SEND, S.ARCHIVED}),
    S.READY_TO_SEND:  frozenset({S.SENT,          S.ARCHIVED}),
    S.SENT:           frozenset({S.FOLLOW_UP_DUE,  S.ARCHIVED}),
    S.FOLLOW_UP_DUE:  frozenset({S.INTERVIEW, S.REJECTED, S.ARCHIVED}),
    S.INTERVIEW:      frozenset({S.ACCEPTED,  S.REJECTED, S.ARCHIVED}),
    S.REJECTED:       frozenset({S.ARCHIVED}),
    S.ACCEPTED:       frozenset({S.ARCHIVED}),
    S.ARCHIVED:       frozenset(),          # terminal — aucune sortie
}


def validate_transition(current: S, target: S) -> None:
    """
    Lève BusinessRuleError si la transition current → target est interdite.
    Appeler avant toute mutation du statut.
    """
    allowed = ALLOWED_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        allowed_labels = ", ".join(s.value for s in allowed) if allowed else "aucune"
        raise BusinessRuleError(
            f"Transition '{current.value}' → '{target.value}' interdite. "
            f"Transitions autorisées depuis '{current.value}' : {allowed_labels}."
        )
