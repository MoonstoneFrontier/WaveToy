"""Flask routes for the localhost-first lead workflow UI."""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for
from dotenv import load_dotenv

from app.services.lead_pipeline_service import LeadPipelineService


def create_app(test_config: dict | None = None) -> Flask:
    load_dotenv()
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.getenv("FLASK_SECRET_KEY", "dev-only-insecure-key"),
        LEADS_DATA_PATH=str(Path(__file__).resolve().parent / "data" / "leads.json"),
    )
    if test_config:
        app.config.update(test_config)

    def pipeline_service() -> LeadPipelineService:
        return LeadPipelineService(app.config["LEADS_DATA_PATH"])

    @app.get("/")
    def index():
        return redirect(url_for("results"))

    @app.get("/results")
    def results():
        service = pipeline_service()
        leads = service.list_leads()
        queues = service.queued_leads()
        return render_template("results.html", leads=leads, queues=queues)

    @app.post("/leads/<lead_id>/stage")
    def update_lead_stage(lead_id: str):
        lead, error = pipeline_service().update_stage(
            lead_id=lead_id,
            acquisition_stage=request.form.get("acquisition_stage", ""),
            reason=request.form.get("reason", ""),
            actor=request.form.get("actor", "manual_user"),
            source=request.form.get("source", "queue_ui"),
        )
        if error or not lead:
            flash(error or "Unable to update lead stage.", "error")
        else:
            flash("Lead stage updated.", "success")
        return redirect(url_for("results"))

    @app.post("/leads/<lead_id>/notes")
    def add_lead_note(lead_id: str):
        note = request.form.get("note", "")
        if not note.strip():
            flash("Note text is required.", "error")
            return redirect(url_for("results"))
        lead = pipeline_service().add_note(
            lead_id=lead_id,
            note_type=request.form.get("note_type", "general"),
            note=note,
            actor=request.form.get("actor", "manual_user"),
            source=request.form.get("source", "queue_ui"),
        )
        flash("Note added." if lead else "Lead not found.", "success" if lead else "error")
        return redirect(url_for("results"))

    @app.post("/leads/<lead_id>/risk")
    def flag_lead_risk(lead_id: str):
        reason = request.form.get("reason", "")
        if not reason.strip():
            flash("Risk flag reason is required.", "error")
            return redirect(url_for("results"))
        lead = pipeline_service().flag_risk(
            lead_id=lead_id,
            reason=reason,
            actor=request.form.get("actor", "manual_user"),
            source=request.form.get("source", "queue_ui"),
        )
        flash("Risk flag added." if lead else "Lead not found.", "success" if lead else "error")
        return redirect(url_for("results"))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host=os.getenv("APP_HOST", "127.0.0.1"), port=int(os.getenv("APP_PORT") or 47000))
