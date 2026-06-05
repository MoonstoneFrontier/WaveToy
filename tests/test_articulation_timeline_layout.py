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


def test_articulation_workspace_subtab_labels_are_documented():
    assert wave_toy.ARTICULATION_TIMELINE_SUBTAB_LABELS == (
        "Timeline",
        "Render",
        "Inspector",
        "Profiles",
    )


def test_articulation_inspector_is_only_added_to_inspector_workflow():
    source = wave_toy.Path(wave_toy.__file__).read_text(encoding="utf-8")
    assert source.count('inspector_layout.addWidget(self._build_articulation_inspector_panel())') == 1
    assert 'timeline_layout.addWidget(self._build_articulation_inspector_panel())' not in source
    assert 'render_layout.addWidget(self._build_articulation_inspector_panel())' not in source
    assert 'profiles_layout.addWidget(self._build_articulation_inspector_panel())' not in source


def test_articulation_workspace_uses_compact_selector_policy():
    source = wave_toy.Path(wave_toy.__file__).read_text(encoding="utf-8")
    assert 'def apply_compact_combo_policy' in source
    assert source.count('apply_compact_combo_policy(') >= 9
