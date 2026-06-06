from pathlib import Path


DOCS = {
    "review": Path("docs/task_101_full_ux_code_review.md"),
    "plan": Path("docs/wavetoy_ux_reorganization_plan.md"),
    "inventory": Path("docs/control_inventory.md"),
    "workflow": Path("docs/workflow_map.md"),
}


def _all_task_101_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in DOCS.values())


def test_task_101_required_docs_exist():
    for path in DOCS.values():
        assert path.exists(), f"Missing required UX review doc: {path}"


def test_task_101_docs_cover_required_planning_topics():
    text = _all_task_101_text()
    for phrase in (
        "Selected Phoneme Workbench",
        "source assignment workflow",
        "global toolbar simplification",
        "storage/data directory UX",
    ):
        assert phrase in text


def test_task_101_docs_propose_tasks_102_through_110():
    text = _all_task_101_text().lower()
    for task_number in range(102, 111):
        assert f"task {task_number}" in text or f"task_{task_number}" in text


def test_control_inventory_has_required_columns_and_categories():
    text = DOCS["inventory"].read_text(encoding="utf-8")
    for column in (
        "Control label",
        "Current location",
        "Callback method",
        "Category",
        "User goal supported",
        "Should stay here",
        "Recommended location",
        "Visibility level",
        "Risk if moved",
    ):
        assert column in text
    for category in (
        "navigation",
        "primary_action",
        "secondary_action",
        "transport",
        "source_assignment",
        "timing_control",
        "expression_control",
        "destructive_action",
        "import_export",
        "diagnostic",
        "advanced_debug",
        "library_management",
        "project_storage",
        "status_display",
    ):
        assert category in text


def test_workflow_map_covers_primary_user_workflows():
    text = DOCS["workflow"].read_text(encoding="utf-8")
    for workflow in (
        "Create a basic sound",
        "Save a sound",
        "Create a saved voice preset",
        "Build a phoneme chain",
        "Assign saved voice per phoneme",
        "Play selected phoneme",
        "Play full word",
        "Render/export word",
        "Inspect waveform",
        "Inspect formants/resonance",
        "Edit timing/performance",
        "Arrange clips on timeline",
        "Save/open project",
        "Find saved assets",
        "Change data directory",
    ):
        assert workflow in text
