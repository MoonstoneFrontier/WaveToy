from pathlib import Path

import pytest

from app.main import create_app
from app.services.lead_pipeline_service import LeadPipelineService


@pytest.fixture()
def client(tmp_path):
    data_path = tmp_path / "leads.json"
    service = LeadPipelineService(data_path)
    service.save_leads(
        [
            {
                "id": "lead-1",
                "name": "Queue Lead",
                "acquisition_stage": "new",
                "acquisition_priority": "normal",
                "risk_score": 0.2,
                "lead_notes": [],
                "timeline": [],
                "dedupe_warning": {"message": "Possible duplicate", "risk_level": "medium"},
            }
        ]
    )
    app = create_app({"TESTING": True, "LEADS_DATA_PATH": str(data_path), "SECRET_KEY": "test"})
    app.config["TEST_DATA_PATH"] = data_path
    with app.test_client() as test_client:
        yield test_client


def test_env_example_contains_runtime_variables():
    env_text = Path(".env.example").read_text(encoding="utf-8")

    assert "APP_ENV=development" in env_text
    assert "PORT_RANGE_START=47000" in env_text
    assert "FLASK_SECRET_KEY=dev-only-insecure-key" in env_text


def test_requirements_contains_local_test_dependencies():
    requirements = Path("requirements.txt").read_text(encoding="utf-8")

    assert "Flask" in requirements
    assert "python-dotenv" in requirements
    assert "pytest" in requirements


def test_post_risk_with_reason_adds_visible_risk_state(client):
    response = client.post("/leads/lead-1/risk", data={"reason": "Floodplain concern"}, follow_redirects=True)

    assert response.status_code == 200
    assert b"Risk flag added." in response.data
    assert b"Priority: high" in response.data
    assert b"risk_flag_added" in response.data


def test_post_risk_without_reason_flashes_error(client):
    response = client.post("/leads/lead-1/risk", data={"reason": "  "}, follow_redirects=True)

    assert response.status_code == 200
    assert b"Risk flag reason is required." in response.data


def test_queue_ui_renders_operational_action_forms(client):
    response = client.get("/results")

    assert response.status_code == 200
    assert b"Update Stage" in response.data
    assert b'name="acquisition_stage"' in response.data
    assert b"Add Note" in response.data
    assert b'name="note"' in response.data
    assert b"Move To Due Diligence" in response.data
    assert b'value="due_diligence"' in response.data
    assert b"Flag Risk" in response.data
    assert b'/leads/lead-1/risk' in response.data
