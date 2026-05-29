"""JSON-backed lead pipeline service for localhost-first workflow actions."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.lead_transition_service import can_transition

DEFAULT_LEADS_PATH = Path(__file__).resolve().parents[1] / "data" / "leads.json"


class LeadPipelineService:
    """Persist and mutate lead records in a local JSON file."""

    def __init__(self, data_path: str | Path | None = None) -> None:
        self.data_path = Path(data_path) if data_path else DEFAULT_LEADS_PATH
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

    def list_leads(self) -> list[dict[str, Any]]:
        if not self.data_path.exists():
            return []
        try:
            payload = json.loads(self.data_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        if isinstance(payload, dict):
            return list(payload.get("leads", []))
        if isinstance(payload, list):
            return payload
        return []

    def save_leads(self, leads: list[dict[str, Any]]) -> None:
        self.data_path.write_text(json.dumps({"leads": leads}, indent=2, sort_keys=True), encoding="utf-8")

    def get_lead(self, lead_id: str) -> dict[str, Any] | None:
        return next((lead for lead in self.list_leads() if str(lead.get("id")) == str(lead_id)), None)

    def _replace_lead(self, updated_lead: dict[str, Any]) -> dict[str, Any]:
        leads = self.list_leads()
        for index, lead in enumerate(leads):
            if str(lead.get("id")) == str(updated_lead.get("id")):
                leads[index] = updated_lead
                self.save_leads(leads)
                return updated_lead
        leads.append(updated_lead)
        self.save_leads(leads)
        return updated_lead

    def _append_timeline_event(
        self,
        lead: dict[str, Any],
        event_type: str,
        summary: str,
        actor: str,
        source: str,
    ) -> None:
        lead.setdefault("timeline", []).append(
            {
                "event_type": event_type,
                "summary": summary,
                "actor": actor,
                "source": source,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    def update_stage(
        self,
        lead_id: str,
        acquisition_stage: str,
        reason: str,
        actor: str = "manual_user",
        source: str = "queue_ui",
    ) -> tuple[dict[str, Any] | None, str | None]:
        lead = self.get_lead(lead_id)
        if not lead:
            return None, "Lead not found."
        allowed, message = can_transition(str(lead.get("acquisition_stage", "new")), acquisition_stage)
        if not allowed:
            return None, message
        lead["acquisition_stage"] = acquisition_stage
        self._append_timeline_event(lead, "stage_updated", reason or message, actor, source)
        return self._replace_lead(lead), None

    def add_note(
        self,
        lead_id: str,
        note_type: str,
        note: str,
        actor: str = "manual_user",
        source: str = "queue_ui",
    ) -> dict[str, Any] | None:
        lead = self.get_lead(lead_id)
        clean_note = (note or "").strip()
        if not lead or not clean_note:
            return lead
        formatted_note = f"[{note_type or 'general'}] {clean_note}"
        lead.setdefault("lead_notes", []).append(formatted_note)
        self._append_timeline_event(lead, "note_added", formatted_note, actor, source)
        return self._replace_lead(lead)

    def flag_risk(
        self,
        lead_id: str,
        reason: str,
        actor: str = "manual_user",
        source: str = "queue_ui",
    ) -> dict[str, Any] | None:
        """Append a risk flag without overwriting existing risk signals."""
        lead = self.get_lead(lead_id)
        clean_reason = (reason or "").strip()
        if not lead:
            return None
        if not clean_reason:
            return lead

        lead.setdefault("lead_notes", []).append(f"[risk_flag] {clean_reason}")
        self._append_timeline_event(lead, "risk_flag_added", clean_reason, actor, source)
        try:
            existing_risk_score = float(lead.get("risk_score") or 0)
        except (TypeError, ValueError):
            existing_risk_score = 0.0
        lead["risk_score"] = max(existing_risk_score, 0.75)
        if lead["risk_score"] >= 0.75:
            lead["acquisition_priority"] = "high"
        return self._replace_lead(lead)

    def queued_leads(self) -> dict[str, list[dict[str, Any]]]:
        leads = self.list_leads()
        return {
            "new": [lead for lead in leads if lead.get("acquisition_stage", "new") == "new"],
            "screening": [lead for lead in leads if lead.get("acquisition_stage") == "screening"],
            "due_diligence": [lead for lead in leads if lead.get("acquisition_stage") == "due_diligence"],
        }
