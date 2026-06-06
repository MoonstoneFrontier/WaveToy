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


def _window_with_three_chain_items():
    win = _window_with_chain()
    win.articulation_chain_items = [
        wave_toy.ArticulationChainItem(_phoneme("AH")),
        wave_toy.ArticulationChainItem(_phoneme("OO")),
        wave_toy.ArticulationChainItem(_phoneme("M")),
    ]
    win._selected_articulation_source_mode = MethodType(lambda self: wave_toy.ARTICULATION_SOURCE_CURRENT, win)
    return win


def _source() -> str:
    return wave_toy.Path(wave_toy.__file__).read_text(encoding="utf-8")


def test_workbench_exists_in_articulation_timeline_workflow():
    source = _source()

    assert 'def _build_selected_phoneme_workbench' in source
    assert 'self._toy_group("Selected Phoneme Workbench")' in source
    assert 'build_sidebar.addWidget(self._build_selected_phoneme_workbench())' in source
    assert 'speechBuilderSelectedPhonemeColumn' in source
    assert 'timing_layout.addWidget(self._build_selected_phoneme_workbench())' not in source


def test_workbench_includes_required_sections_and_primary_create_word():
    source = _source()

    assert 'Selected Phoneme Status' in source
    assert 'Voice' in source
    assert 'Timing' in source
    assert 'Actions' in source
    assert 'make_primary_action_button("Create Word", self._create_articulation_word' in source
    assert 'make_export_import_button("Export Word", self._export_articulation_word' in source
    assert 'make_secondary_action_button("Send Word to Timeline", self._send_articulation_word_to_timeline' in source


def test_workbench_source_scope_labels_are_clear():
    source = _source()

    assert 'Voice' in source
    assert 'selectedPhonemeVoiceWaveVariationSelector' in source
    assert 'Apply to Selected' in source
    assert 'Reset Selected to Default Voice' in source
    assert 'Use Current Voice Lab Sound' not in source


def test_selecting_timing_track_or_chain_card_uses_same_selected_index():
    source = _source()

    assert 'self.articulation_timeline_canvas.blockSelected.connect(self._select_articulation_chain_item)' in source
    assert 'card.mousePressEvent = lambda event, i=index: self._select_articulation_chain_item(i)' in source
    assert 'def _select_articulation_chain_item(self, index: int) -> None:' in source


def test_apply_current_wave_to_remaining_changes_selected_and_following_only():
    win = _window_with_three_chain_items()
    win.articulation_selected_chain_index = 1

    win._apply_current_wave_to_remaining_chain()

    assert win.articulation_chain_items[0].phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_DEFAULT
    assert win.articulation_chain_items[1].phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_CURRENT
    assert win.articulation_chain_items[2].phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_CURRENT


def test_apply_source_to_whole_chain_changes_all_items():
    win = _window_with_three_chain_items()
    win.articulation_selected_chain_index = 1

    win._apply_current_wave_to_whole_chain()

    assert all(item.phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_CURRENT for item in win.articulation_chain_items)


def test_reset_selected_source_changes_only_selected_item():
    win = _window_with_three_chain_items()
    win.articulation_selected_chain_index = 1
    win._apply_current_wave_to_whole_chain()

    win._reset_selected_chain_item_source()

    assert win.articulation_chain_items[0].phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_CURRENT
    assert win.articulation_chain_items[1].phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_DEFAULT
    assert win.articulation_chain_items[2].phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_CURRENT


def test_create_word_callback_remains_existing_render_method_and_render_tab_button_still_exists():
    source = _source()

    assert 'def _create_articulation_word' in source
    assert source.count('make_primary_action_button("Create Word", self._create_articulation_word') >= 2


def test_no_project_or_export_schema_changes_for_workbench():
    source = _source()

    assert '"schema": "wavetoy.articulation_chain.v1"' not in source
    assert 'selected_phoneme_workbench' not in source.lower().split('to_json_dict', 1)[0]
