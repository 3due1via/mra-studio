from dataclasses import dataclass
from datetime import datetime, timezone

TRANSITIONS = {
    "open": frozenset({"planned", "in_progress", "cancelled"}),
    "planned": frozenset({"open", "in_progress", "blocked", "cancelled"}),
    "in_progress": frozenset({"blocked", "completed", "cancelled"}),
    "blocked": frozenset({"planned", "in_progress", "cancelled"}),
    "completed": frozenset({"in_progress"}),
    "cancelled": frozenset(),
}


class InvalidTransitionError(ValueError): pass


@dataclass(frozen=True)
class TransitionResult:
    started_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    resolution_summary: str | None
    resolution_summary_snapshot: str | None
    event_type: str


def apply_transition(*, current: str, target: str, role: str, has_active_assignee: bool, note: str | None, resolution_summary: str | None, started_at: datetime | None, current_resolution: str | None, now: datetime | None = None) -> TransitionResult:
    now = now or datetime.now(timezone.utc)
    note = note.strip() if note else None
    resolution_summary = resolution_summary.strip() if resolution_summary else None
    if target == current or target not in TRANSITIONS.get(current, frozenset()):
        raise InvalidTransitionError("Transizione non consentita.")
    if target in {"planned", "in_progress"} and not has_active_assignee:
        raise InvalidTransitionError("La transizione richiede un assegnatario attivo.")
    if target in {"blocked", "cancelled"} and not note:
        raise InvalidTransitionError("La transizione richiede una nota.")
    if target == "completed" and not resolution_summary:
        raise InvalidTransitionError("La chiusura richiede una risoluzione.")
    if target == "cancelled" and role != "admin":
        raise InvalidTransitionError("Transizione riservata all'amministratore.")
    reopened = current == "completed" and target == "in_progress"
    if reopened and (role != "admin" or not note):
        raise InvalidTransitionError("La riapertura richiede amministratore e nota.")
    return TransitionResult(
        started_at=started_at or (now if target == "in_progress" else None),
        completed_at=now if target == "completed" else None,
        cancelled_at=now if target == "cancelled" else None,
        resolution_summary=resolution_summary if target == "completed" else (None if reopened else current_resolution),
        resolution_summary_snapshot=current_resolution if reopened else None,
        event_type="reopened" if reopened else "status_changed",
    )
