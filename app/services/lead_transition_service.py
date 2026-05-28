"""Stage transition guardrails for local lead workflow actions."""

STAGE_ORDER = ["new", "screening", "due_diligence", "offer", "closed"]


def can_transition(current_stage: str, next_stage: str) -> tuple[bool, str]:
    """Return whether a stage transition is allowed and a user-facing reason."""
    current = current_stage or "new"
    if next_stage not in STAGE_ORDER:
        return False, f"Unknown acquisition stage: {next_stage}."
    if current not in STAGE_ORDER:
        current = "new"
    if next_stage == current:
        return True, "Stage unchanged."
    if STAGE_ORDER.index(next_stage) < STAGE_ORDER.index(current):
        return False, "Stage transitions cannot move backward from this queue action."
    return True, "Stage updated."
