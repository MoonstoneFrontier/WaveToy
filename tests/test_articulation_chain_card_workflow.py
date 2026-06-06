import sys
from types import MethodType

try:
    import wave_toy
except ImportError:
    sys.modules.pop("wave_toy", None)
    from tests.test_performance_timeline_undo import _install_qt_stubs

    _install_qt_stubs()
    import wave_toy



def _patch_messagebox_yes_no(monkeypatch):
    monkeypatch.setattr(wave_toy.QMessageBox, "Yes", 1, raising=False)
    monkeypatch.setattr(wave_toy.QMessageBox, "No", 2, raising=False)


def _phoneme(name="AH"):
    return wave_toy.ArticulationPhoneme.from_json_dict(
        wave_toy.VOWEL_PRESETS["AH"] | {"name": name, "voice_pitch": 220.0, "voice_strength": 0.65}
    )


def _window_with_chain():
    win = wave_toy.WaveToyWindow.__new__(wave_toy.WaveToyWindow)
    win.articulation_chain_items = [
        wave_toy.ArticulationChainItem(_phoneme("AH")),
        wave_toy.ArticulationChainItem(_phoneme("OO")),
    ]
    win.articulation_selected_chain_index = None
    win.wave_row_order = ["sine", "Charles_up"]
    win.timeline_selected_palette_item_id = None
    win._timeline_palette_item_by_id = MethodType(lambda self, item_id: None, win)
    win._selected_mix_wave_id = MethodType(lambda self: "sine", win)
    win._timeline_recipe_snapshot = MethodType(lambda self: {"recipe": "classic"}, win)
    win._source_metadata_for_mode = MethodType(
        lambda self, mode: {
            "source_mode": mode,
            "source_recipe_snapshot": {"recipe": "classic"},
            "source_start_seconds": 0.0,
            "source_duration_seconds": 0.0,
            "source_pitch_follow": True,
            "source_loop_to_fit": True,
            "source_gain": 1.0,
        },
        win,
    )
    win._mark_articulation_word_dirty = MethodType(lambda self: None, win)
    win._refresh_articulation_chain_cards = MethodType(lambda self: None, win)
    win._set_articulation_ui_from_phoneme = MethodType(lambda self, phoneme: None, win)
    return win


def test_selected_chain_index_updates_from_chain_card_selection_helper():
    win = _window_with_chain()

    win._select_articulation_chain_item(1)

    assert win.articulation_selected_chain_index == 1


def test_voice_wave_variation_options_include_default_and_current_classic_wave():
    win = _window_with_chain()

    options = win.available_chain_voice_wave_variations()
    labels = {option["label"] for option in options}
    ids = {option["id"] for option in options}

    assert "Default Voice" in labels
    assert "Current Classic Wave" in labels
    assert wave_toy.ARTICULATION_SOURCE_DEFAULT in ids
    assert wave_toy.ARTICULATION_SOURCE_CURRENT in ids


def test_applying_variation_to_one_chain_item_does_not_mutate_other_items():
    win = _window_with_chain()

    win.apply_voice_wave_variation_to_chain_item(0, f"{wave_toy.ARTICULATION_SOURCE_MIX_WAVE}:Charles_up")

    assert win.articulation_chain_items[0].phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_MIX_WAVE
    assert win.articulation_chain_items[0].phoneme.source_wave_id == "Charles_up"
    assert win.articulation_chain_items[1].phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_DEFAULT
    assert win.articulation_selected_chain_index == 0


def test_reset_selected_and_whole_chain_source_workflows_remain_available(monkeypatch):
    win = _window_with_chain()
    win.apply_voice_wave_variation_to_chain_item(0, f"{wave_toy.ARTICULATION_SOURCE_MIX_WAVE}:Charles_up")
    win.apply_voice_wave_variation_to_chain_item(1, wave_toy.ARTICULATION_SOURCE_CURRENT)

    win.articulation_selected_chain_index = 0
    win._reset_selected_chain_item_source()
    assert win.articulation_chain_items[0].phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_DEFAULT
    assert win.articulation_chain_items[1].phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_CURRENT

    _patch_messagebox_yes_no(monkeypatch)
    monkeypatch.setattr(wave_toy.QMessageBox, "question", lambda *args: wave_toy.QMessageBox.Yes, raising=False)

    win._reset_whole_chain_source()
    assert all(item.phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_DEFAULT for item in win.articulation_chain_items)


def test_reset_whole_chain_source_cancel_keeps_existing_sources(monkeypatch):
    win = _window_with_chain()
    win.apply_voice_wave_variation_to_chain_item(0, f"{wave_toy.ARTICULATION_SOURCE_MIX_WAVE}:Charles_up")
    win.apply_voice_wave_variation_to_chain_item(1, wave_toy.ARTICULATION_SOURCE_CURRENT)
    _patch_messagebox_yes_no(monkeypatch)
    monkeypatch.setattr(wave_toy.QMessageBox, "question", lambda *args: wave_toy.QMessageBox.No, raising=False)

    win._reset_whole_chain_source()

    assert win.articulation_chain_items[0].phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_MIX_WAVE
    assert win.articulation_chain_items[0].phoneme.source_wave_id == "Charles_up"
    assert win.articulation_chain_items[1].phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_CURRENT


def test_selection_clamps_when_selected_card_is_deleted():
    win = _window_with_chain()
    win.articulation_selected_chain_index = 1

    win._remove_articulation_chain_item(1)

    assert win.articulation_selected_chain_index == 0


def test_chain_card_selected_state_and_selector_are_in_source():
    source = wave_toy.Path(wave_toy.__file__).read_text(encoding="utf-8")

    assert 'card.setProperty("selected", index == self.articulation_selected_chain_index)' in source
    assert 'card.mousePressEvent = lambda event, i=index: self._select_articulation_chain_item(i)' in source
    assert 'variation_combo.setObjectName("chainCardVoiceWaveVariationSelector")' in source
    assert 'duration_spin.setObjectName("chainCardDurationSpin")' in source
    assert 'variation_label = QLabel("Source")' in source


def test_existing_apply_current_wave_helpers_still_exist_without_schema_migration():
    source = wave_toy.Path(wave_toy.__file__).read_text(encoding="utf-8")

    assert "def _apply_current_wave_to_selected_chain_item" in source
    assert "def _apply_current_wave_to_whole_chain" in source
    assert "schema migration" not in source.lower()
    assert '"schema": "wavetoy.articulation_chain.v1"' not in source


def test_new_chain_item_defaults_to_current_classic_wave_without_mutating_existing_items():
    win = _window_with_chain()
    win.articulation_word_render_settings = {"auto_apply_current_wave_to_new_chain_items": True}
    win.current_phoneme = _phoneme("M")
    win._phoneme_from_articulation_ui = MethodType(lambda self: _phoneme("M"), win)

    win._add_current_phoneme_to_chain()

    assert win.articulation_chain_items[-1].phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_CURRENT
    assert win.articulation_chain_items[0].phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_DEFAULT
    assert win.articulation_chain_items[1].phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_DEFAULT


def test_apply_current_wave_to_selected_changes_only_selected_item():
    win = _window_with_chain()
    win._selected_articulation_source_mode = MethodType(lambda self: wave_toy.ARTICULATION_SOURCE_CURRENT, win)
    win.articulation_selected_chain_index = 1

    win._apply_current_wave_to_selected_chain_item()

    assert win.articulation_chain_items[0].phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_DEFAULT
    assert win.articulation_chain_items[1].phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_CURRENT


def test_apply_current_wave_to_chain_changes_all_items():
    win = _window_with_chain()
    win._selected_articulation_source_mode = MethodType(lambda self: wave_toy.ARTICULATION_SOURCE_CURRENT, win)
    win.articulation_selected_chain_index = 0

    win._apply_current_wave_to_whole_chain()

    assert all(item.phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_CURRENT for item in win.articulation_chain_items)


def test_apply_current_wave_to_selected_requires_selection(monkeypatch):
    win = _window_with_chain()
    win._selected_articulation_source_mode = MethodType(lambda self: wave_toy.ARTICULATION_SOURCE_CURRENT, win)
    win.articulation_selected_chain_index = None
    messages = []
    monkeypatch.setattr(wave_toy.QMessageBox, "information", lambda *args: messages.append(args), raising=False)

    win._apply_current_wave_to_selected_chain_item()

    assert messages
    assert all(item.phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_DEFAULT for item in win.articulation_chain_items)
