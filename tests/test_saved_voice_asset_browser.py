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


def _window_with_saved_voice_options():
    win = _window_with_chain()
    win.user_presets_path = wave_toy.Path("/tmp/unused_voice_presets.json")
    win._read_user_recipes = MethodType(lambda self: [
        {
            "name": "Charles_up",
            "asset_type": "voice_preset",
            "voice_preset": True,
            "description": "Bright Charles voice",
            "ui": {},
            "settings": {},
        },
        {
            "name": "Charles_down",
            "asset_type": "voice_preset",
            "voice_preset": True,
            "ui": {},
            "settings": {},
        },
    ], win)
    return win


def test_saved_voices_panel_exists_in_speech_builder_with_required_controls():
    source = _source()
    start = source.index("def _build_saved_voices_panel")
    end = source.index("def _build_voice_source_dock", start)
    panel_source = source[start:end]

    assert 'self._toy_group("Saved Voices")' in panel_source
    assert 'QLabel("Active Voice")' in panel_source
    assert 'activeVoiceSelector' in panel_source
    assert 'savedVoiceAssetList' in panel_source
    assert 'No saved voices yet. Create one in Voice Lab with Save Voice Preset.' in panel_source
    for expected in (
        '▶ Preview Voice',
        'Apply to Selected',
        'Apply to Remaining',
        'Apply to Whole Chain',
        'Refresh Voices',
        'Open Voices Folder',
    ):
        assert expected in panel_source


def test_saved_voices_panel_hides_raw_source_metadata_labels_from_primary_ui():
    source = _source()
    start = source.index("def _build_saved_voices_panel")
    end = source.index("def _build_current_voice_status_panel", start)
    panel_source = source[start:end]

    for hidden in ("Source Mode:", "Badge:", "Preview Color:", "Category:"):
        assert hidden not in panel_source


def test_saved_voices_appear_before_current_and_default_voice_options():
    win = _window_with_saved_voice_options()

    labels = [option["label"] for option in win.available_chain_voice_wave_variations()]

    assert labels.index("Charles_up") < labels.index("Current Voice Lab Sound")
    assert labels.index("Charles_down") < labels.index("Current Voice Lab Sound")
    assert labels.index("Current Voice Lab Sound") < labels.index("Default Voice")


def test_selecting_saved_voice_asset_updates_active_voice_without_mutating_chain():
    win = _window_with_saved_voice_options()
    win.saved_voice_asset_ids = [f"{wave_toy.ARTICULATION_SOURCE_VOICE_PRESET_ID_PREFIX}Charles_up"]
    win._refresh_voice_source_controls = MethodType(lambda self: None, win)

    win._select_saved_voice_asset(0)

    assert win.current_voice_variation_id == f"{wave_toy.ARTICULATION_SOURCE_VOICE_PRESET_ID_PREFIX}Charles_up"
    assert all(item.phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_DEFAULT for item in win.articulation_chain_items)


def test_refresh_saved_voices_preserves_active_voice_and_chain_sources():
    win = _window_with_saved_voice_options()
    active_id = f"{wave_toy.ARTICULATION_SOURCE_VOICE_PRESET_ID_PREFIX}Charles_down"
    win.current_voice_variation_id = active_id
    win.saved_voice_asset_list = None
    win.saved_voice_asset_empty_label = None
    win.saved_voice_asset_details_label = None

    before = [item.phoneme.to_json_dict() for item in win.articulation_chain_items]
    win._refresh_saved_voice_asset_cards()

    assert win.current_voice_variation_id == active_id
    assert [item.phoneme.to_json_dict() for item in win.articulation_chain_items] == before


def test_saved_voice_apply_scopes_selected_remaining_and_whole_chain():
    win = _window_with_saved_voice_options()
    win.articulation_chain_items = [
        wave_toy.ArticulationChainItem(_phoneme("AH")),
        wave_toy.ArticulationChainItem(_phoneme("OO")),
        wave_toy.ArticulationChainItem(_phoneme("M")),
    ]
    win.articulation_selected_chain_index = 1
    up_id = f"{wave_toy.ARTICULATION_SOURCE_VOICE_PRESET_ID_PREFIX}Charles_up"
    down_id = f"{wave_toy.ARTICULATION_SOURCE_VOICE_PRESET_ID_PREFIX}Charles_down"

    win.current_voice_variation_id = up_id
    win._apply_current_voice_to_selected_chain_item()
    assert win.articulation_chain_items[0].phoneme.source_recipe_snapshot == {}
    assert win.articulation_chain_items[1].phoneme.source_recipe_snapshot["name"] == "Charles_up"
    assert win.articulation_chain_items[2].phoneme.source_recipe_snapshot == {}

    win.current_voice_variation_id = down_id
    win._apply_current_voice_to_remaining_chain()
    assert win.articulation_chain_items[0].phoneme.source_recipe_snapshot == {}
    assert win.articulation_chain_items[1].phoneme.source_recipe_snapshot["name"] == "Charles_down"
    assert win.articulation_chain_items[2].phoneme.source_recipe_snapshot["name"] == "Charles_down"

    win.current_voice_variation_id = up_id
    win._apply_current_voice_to_whole_chain()
    assert all(item.phoneme.source_recipe_snapshot["name"] == "Charles_up" for item in win.articulation_chain_items)
