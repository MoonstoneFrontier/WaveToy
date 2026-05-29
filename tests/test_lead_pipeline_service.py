from app.services.lead_pipeline_service import LeadPipelineService


def make_service(tmp_path, risk_score=0.1):
    service = LeadPipelineService(tmp_path / "leads.json")
    service.save_leads(
        [
            {
                "id": "lead-1",
                "name": "Test Lead",
                "acquisition_stage": "new",
                "acquisition_priority": "normal",
                "risk_score": risk_score,
                "risk_signals": ["existing signal"],
                "lead_notes": [],
                "timeline": [],
            }
        ]
    )
    return service


def test_flag_risk_appends_risk_timeline_event(tmp_path):
    service = make_service(tmp_path)

    lead = service.flag_risk("lead-1", "Title concern")

    assert lead is not None
    assert lead["timeline"][-1]["event_type"] == "risk_flag_added"
    assert lead["timeline"][-1]["summary"] == "Title concern"


def test_flag_risk_sets_score_to_at_least_threshold(tmp_path):
    service = make_service(tmp_path, risk_score=0.2)

    lead = service.flag_risk("lead-1", "Environmental concern")

    assert lead["risk_score"] >= 0.75


def test_flag_risk_preserves_higher_existing_risk_score(tmp_path):
    service = make_service(tmp_path, risk_score=0.9)

    lead = service.flag_risk("lead-1", "Priority concern")

    assert lead["risk_score"] == 0.9


def test_flag_risk_sets_priority_high_when_risk_score_is_high(tmp_path):
    service = make_service(tmp_path, risk_score=0.4)

    lead = service.flag_risk("lead-1", "Legal concern")

    assert lead["acquisition_priority"] == "high"


def test_blank_reason_does_not_corrupt_lead(tmp_path):
    service = make_service(tmp_path, risk_score=0.4)
    before = service.get_lead("lead-1")

    lead = service.flag_risk("lead-1", "   ")

    assert lead == before
    assert lead["lead_notes"] == []
    assert lead["timeline"] == []


def test_flag_risk_handles_unparseable_existing_risk_score(tmp_path):
    service = make_service(tmp_path, risk_score="needs review")

    lead = service.flag_risk("lead-1", "Manual concern")

    assert lead["risk_score"] == 0.75
    assert lead["acquisition_priority"] == "high"
