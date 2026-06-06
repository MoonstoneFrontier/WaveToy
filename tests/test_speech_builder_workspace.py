import sys
from types import MethodType

try:
    import wave_toy
except ImportError:
    sys.modules.pop("wave_toy", None)
    from tests.test_performance_timeline_undo import _install_qt_stubs

    _install_qt_stubs()
    import wave_toy

from tests.test_articulation_chain_card_workflow import _phoneme, _window_with_chain


def _source() -> str:
    return wave_toy.Path(wave_toy.__file__).read_text(encoding="utf-8")


def test_chain_card_inline_actions():
    source = _source()

    assert 'duration_spin.setObjectName("chainCardDurationSpin")' in source
    assert 'duration_spin.valueChanged.connect(lambda value, i=index: self._set_chain_item_duration_ms(i, value))' in source
    assert 'variation_combo.setObjectName("chainCardVoiceWaveVariationSelector")' in source
    assert '("Duplicate", lambda checked=False, i=index: self._duplicate_articulation_chain_item(i), False)' in source
    assert '("Move Left", lambda checked=False, i=index: self._move_articulation_chain_item(i, -1), False)' in source
    assert '("Move Right", lambda checked=False, i=index: self._move_articulation_chain_item(i, 1), False)' in source
    assert '("Remove", lambda checked=False, i=index: self._remove_articulation_chain_item(i), True)' in source


def test_speech_builder_layout():
    source = _source()

    assert 'chain_split.setObjectName("speechBuilderWorkspace")' in source
    assert 'speechBuilderPhonemeLibraryColumn' in source
    assert 'speechBuilderChainEditorColumn' in source
    assert 'speechBuilderSelectedPhonemeColumn' in source
    assert 'library_header = QLabel("Phoneme Library")' in source
    assert 'chain_header = QLabel("Chain Editor")' in source
    assert 'selected_header = QLabel("Selected Phoneme")' in source


def test_selected_phoneme_panel_docked():
    source = _source()

    assert 'build_sidebar.addWidget(self._build_selected_phoneme_workbench())' in source
    assert 'timing_layout.addWidget(self._build_selected_phoneme_workbench())' not in source
    assert 'chain_tab_layout.addWidget(self._build_selected_phoneme_workbench())' not in source
    assert 'panel.setObjectName("selectedPhonemeWorkbench")' in source


def test_cv_vc_library_not_in_chain():
    source = _source()

    assert 'library_column.addWidget(CollapsibleSection("CV / VC Library", cv_vc_card, expanded=True))' in source
    assert 'chain_tab_layout.addWidget(CollapsibleSection("CV / VC Library"' not in source
    assert 'build_primary.addWidget(CollapsibleSection("CV / VC Library"' not in source


def test_manual_qa_workflow_without_tab_switching_helpers():
    win = _window_with_chain()
    win.articulation_word_render_settings = {"auto_apply_current_wave_to_new_chain_items": True}
    win.current_phoneme = _phoneme("M")
    win._phoneme_from_articulation_ui = MethodType(lambda self: _phoneme("M"), win)
    win._set_articulation_ui_from_phoneme = MethodType(lambda self, phoneme, regenerate=False: None, win)
    win._selected_articulation_source_mode = MethodType(lambda self: wave_toy.ARTICULATION_SOURCE_CURRENT, win)
    win._refresh_articulation_motion_timeline = MethodType(lambda self: None, win)
    win._refresh_selected_component_controls = MethodType(lambda self: None, win)
    win._schedule_live_preview = MethodType(lambda self, target="selected_timeline_fragment": None, win)
    win._scrub_articulation_playhead = MethodType(lambda self, elapsed_ms: None, win)
    win.articulation_playhead_ms = 0.0

    win._add_current_phoneme_to_chain()
    win._select_articulation_chain_item(2)
    win._apply_current_wave_to_selected_chain_item()
    win._set_chain_item_duration_ms(2, 640)
    win._duplicate_articulation_chain_item(2)

    assert win.articulation_selected_chain_index == 3
    assert win.articulation_chain_items[2].phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_CURRENT
    assert win.articulation_chain_items[2].duration_ms == 640
    assert win.articulation_chain_items[3].duration_ms == 640
