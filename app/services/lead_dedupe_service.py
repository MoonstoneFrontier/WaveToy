"""Small helper for exposing dedupe warning metadata in templates."""


def dedupe_warning_for(lead: dict) -> dict | None:
    """Return a normalized dedupe warning, if one exists on the lead."""
    warning = lead.get("dedupe_warning")
    if not warning:
        return None
    if isinstance(warning, dict):
        return warning
    return {"message": str(warning), "risk_level": lead.get("dedupe_risk_level", "unknown")}
