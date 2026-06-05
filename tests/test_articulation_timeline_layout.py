import sys

try:
    import wave_toy
except ImportError:
    sys.modules.pop("wave_toy", None)
    from tests.test_performance_timeline_undo import _install_qt_stubs

    _install_qt_stubs()
    import wave_toy


def test_articulation_picker_width_policy_is_compact_sidebar():
    policy = wave_toy.articulation_picker_width_policy()

    assert policy == {"minimum": 220, "preferred": 300, "maximum": 380}
    assert policy["minimum"] <= policy["preferred"] <= policy["maximum"]


def test_articulation_timeline_internal_subtab_labels_are_documented():
    assert wave_toy.ARTICULATION_TIMELINE_SUBTAB_LABELS == (
        "Build",
        "Visual Timeline",
        "Render / Export",
        "Performance",
        "Advanced",
    )
