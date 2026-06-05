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


def test_articulation_inspector_is_only_added_to_render_export_workflow():
    source = wave_toy.Path(wave_toy.__file__).read_text(encoding="utf-8")
    assert source.count('render_layout.addWidget(self._build_articulation_inspector_panel())') == 1
    assert 'build_layout.addWidget(self._build_articulation_inspector_panel())' not in source
    assert 'advanced_layout.addWidget(self._build_articulation_inspector_panel())' not in source
