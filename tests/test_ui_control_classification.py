from pathlib import Path
import sys

try:
    import wave_toy
except ImportError:
    sys.modules.pop("wave_toy", None)
    from tests.test_performance_timeline_undo import _install_qt_stubs

    _install_qt_stubs()
    import wave_toy


AUDIT_PATH = Path("docs/task_098_ui_cleanup_workflow_audit.md")


def test_task_098_ui_audit_document_exists_and_classifies_controls():
    text = AUDIT_PATH.read_text(encoding="utf-8")
    for category in (
        "primary_action",
        "secondary_action",
        "transport",
        "destructive_action",
        "navigation",
        "editor_control",
        "selector",
        "diagnostic",
        "export_import",
        "library_asset",
        "debug_advanced",
        "status_only",
    ):
        assert category in text


def test_task_098_ui_audit_covers_required_major_areas():
    text = AUDIT_PATH.read_text(encoding="utf-8")
    for area in (
        "Global command bar",
        "Classic Controls",
        "Articulation Timeline → Timeline → Chain",
        "Articulation Timeline → Timeline → Timing / Performance",
        "Articulation Timeline → Render",
        "Voice Font",
        "Performance Timeline",
        "Graphical Editor",
        "Speech Asset Library",
        "Wave Explorer",
        "Note picker / music theory dialog",
    ):
        assert area in text


def test_task_098_visual_design_constants_are_defined():
    for name in (
        "UI_BUTTON_HEIGHT_COMPACT",
        "UI_BUTTON_HEIGHT_PRIMARY",
        "UI_CARD_PADDING_COMPACT",
        "UI_SECTION_SPACING_COMPACT",
        "UI_TAB_HEIGHT_COMPACT",
        "UI_PRIMARY_ACTION_COLOR",
        "UI_SECONDARY_ACTION_COLOR",
        "UI_DESTRUCTIVE_ACTION_COLOR",
        "UI_TRANSPORT_ACTION_COLOR",
        "UI_DIAGNOSTIC_COLOR",
    ):
        assert hasattr(wave_toy, name)
