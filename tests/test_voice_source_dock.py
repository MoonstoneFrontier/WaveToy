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


def test_voice_source_dock_and_current_voice_panel_are_in_speech_builder():
    source = _source()

    assert 'self._toy_group("Voice Source Dock")' in source
    assert 'dock.setObjectName("voiceSourceDock")' in source
    assert 'chain_tab_layout.addWidget(voice_source_dock)' in source
    assert 'self._toy_group("Current Voice")' in source
    assert 'panel.setObjectName("currentVoiceStatusPanel")' in source
    assert 'build_sidebar.addWidget(self._build_current_voice_status_panel())' in source


def test_voice_source_dock_displays_voice_picker_without_raw_metadata_labels():
    source = _source()

    start = source.index('def _build_voice_source_dock')
    end = source.index('def _build_current_voice_status_panel', start)
    dock_source = source[start:end]

    for expected in (
        'Active Voice:',
        'Voice selector',
        'voiceSourceDockVoiceSelector',
        '▶ Preview Voice',
        'Apply Voice to Selected',
        'Apply Voice to Remaining',
        'Apply Voice to Whole Chain',
        'Refresh Voices',
        'Selecting a voice does not change the chain until Apply is clicked.',
        'Ready',
    ):
        assert expected in dock_source

    for hidden in ('Source Mode:', 'Badge:', 'Preview Color:', 'Category:'):
        assert hidden not in dock_source


def test_selecting_current_voice_is_non_destructive_until_apply_scope():
    win = _window_with_chain()
    win.current_voice_variation_id = wave_toy.ARTICULATION_SOURCE_CURRENT
    win._refresh_voice_source_controls = MethodType(lambda self: None, win)
    combo = type("Combo", (), {"currentData": lambda self: f"{wave_toy.ARTICULATION_SOURCE_MIX_WAVE}:Charles_up"})()

    win._select_current_voice_from_selector(combo)

    assert win.current_voice_variation_id == f"{wave_toy.ARTICULATION_SOURCE_MIX_WAVE}:Charles_up"
    assert all(item.phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_DEFAULT for item in win.articulation_chain_items)


def test_apply_current_voice_scopes_selected_remaining_and_whole_chain():
    win = _window_with_chain()
    win.articulation_chain_items.append(wave_toy.ArticulationChainItem(_phoneme("M")))
    win.current_voice_variation_id = f"{wave_toy.ARTICULATION_SOURCE_MIX_WAVE}:Charles_up"
    win.articulation_selected_chain_index = 1

    win._apply_current_voice_to_selected_chain_item()
    assert win.articulation_chain_items[0].phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_DEFAULT
    assert win.articulation_chain_items[1].phoneme.source_wave_id == "Charles_up"
    assert win.articulation_chain_items[2].phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_DEFAULT

    win.current_voice_variation_id = wave_toy.ARTICULATION_SOURCE_CURRENT
    win._apply_current_voice_to_remaining_chain()
    assert win.articulation_chain_items[0].phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_DEFAULT
    assert win.articulation_chain_items[1].phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_CURRENT
    assert win.articulation_chain_items[2].phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_CURRENT

    win.current_voice_variation_id = f"{wave_toy.ARTICULATION_SOURCE_MIX_WAVE}:sine"
    win._apply_current_voice_to_whole_chain()
    assert all(item.phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_MIX_WAVE for item in win.articulation_chain_items)


def test_saved_voice_presets_appear_in_voice_source_options():
    win = _window_with_chain()
    win.user_presets_path = wave_toy.Path("/tmp/unused_voice_presets.json")
    win._read_user_recipes = MethodType(lambda self: [
        {"name": "Charles_flat", "asset_type": "voice_preset", "voice_preset": True, "ui": {}, "settings": {}},
        {"name": "NotAVoice", "asset_type": "sound", "ui": {}, "settings": {}},
    ], win)

    options = win.available_chain_voice_wave_variations()

    assert "Charles_flat" in {option["label"] for option in options}
    assert f"{wave_toy.ARTICULATION_SOURCE_VOICE_PRESET_ID_PREFIX}Charles_flat" in {option["id"] for option in options}
    assert "NotAVoice" not in {option["label"] for option in options}


def test_saved_voice_preset_metadata_keeps_recipe_snapshot():
    win = _window_with_chain()
    win.user_presets_path = wave_toy.Path("/tmp/unused_voice_presets.json")
    win._read_user_recipes = MethodType(lambda self: [
        {"name": "Charles_flat", "asset_type": "voice_preset", "voice_preset": True, "ui": {"note": "C4"}, "settings": {"duration": 1.0}},
    ], win)

    metadata = win._source_metadata_for_variation_id(f"{wave_toy.ARTICULATION_SOURCE_VOICE_PRESET_ID_PREFIX}Charles_flat")

    assert metadata["source_mode"] == wave_toy.ARTICULATION_SOURCE_CURRENT
    assert metadata["source_recipe_snapshot"]["name"] == "Charles_flat"
