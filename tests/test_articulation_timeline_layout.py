import sys

try:
    import wave_toy
except ImportError:
    sys.modules.pop("wave_toy", None)
    from tests.test_performance_timeline_undo import _install_qt_stubs

    _install_qt_stubs()
    import wave_toy


def _source() -> str:
    return wave_toy.Path(wave_toy.__file__).read_text(encoding="utf-8")


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


def test_articulation_timeline_internal_subtab_labels_are_documented():
    assert wave_toy.ARTICULATION_TIMELINE_INTERNAL_SUBTAB_LABELS == (
        "Chain",
        "Timing",
        "Motion",
    )


def test_articulation_inspector_is_only_added_to_inspector_workflow():
    source = _source()
    assert source.count('inspector_layout.addWidget(self._build_articulation_inspector_panel())') == 1
    assert 'timeline_layout.addWidget(self._build_articulation_inspector_panel())' not in source
    assert 'render_layout.addWidget(self._build_articulation_inspector_panel())' not in source
    assert 'profiles_layout.addWidget(self._build_articulation_inspector_panel())' not in source
    assert source.count('self._build_articulation_inspector_panel()') == 1


def test_articulation_workspace_uses_compact_selector_policy():
    source = _source()
    assert 'def apply_compact_combo_policy' in source
    assert source.count('apply_compact_combo_policy(') >= 9


def test_speech_assets_sidebar_stays_compact_in_chain_workflow():
    source = _source()
    assert 'chain_split.addLayout(build_sidebar, 1)' in source
    assert 'apply_articulation_picker_sidebar_width_policy(speech_assets)' in source
    assert 'build_sidebar.addWidget(speech_assets)' in source


def test_motion_preview_only_appears_in_motion_workflow():
    source = _source()
    assert 'motion_page, motion_layout = make_internal_timeline_page("articulationTimelineMotionPage")' in source
    assert 'motion_layout.addWidget(motion_card, 1)' in source
    assert 'timing_layout.addWidget(motion_card' not in source
    assert 'chain_tab_layout.addWidget(motion_card' not in source


def test_visual_timeline_canvas_appears_in_timing_workflow():
    source = _source()
    assert 'timing_page, timing_layout = make_internal_timeline_page("articulationTimelineTimingPage")' in source
    assert 'timing_layout.addWidget(track_shell)' in source
    assert 'track_layout.addWidget(self.articulation_timeline_scroll)' in source
    assert 'chain_tab_layout.addWidget(track_shell)' not in source
    assert 'motion_layout.addWidget(track_shell)' not in source


def test_timing_track_lanes_start_collapsed_to_reduce_scroll():
    source = _source()
    assert 'CollapsibleSection("Envelope track canvas", self.articulation_envelope_canvas, expanded=False)' in source
    assert 'CollapsibleSection("Formant track canvas", self.articulation_formant_canvas, expanded=False)' in source


def test_motion_canvas_can_expand_vertically():
    source = _source()
    assert 'self.articulation_motion_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)' in source
