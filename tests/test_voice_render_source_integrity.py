import sys
from types import MethodType

import numpy as np
import pytest

try:
    import wave_toy
except ImportError:
    sys.modules.pop("wave_toy", None)
    from tests.test_performance_timeline_undo import _install_qt_stubs

    _install_qt_stubs()
    import wave_toy

from tests.test_articulation_chain_card_workflow import _phoneme, _window_with_chain


class _SignalSafeCombo:
    def __init__(self, data=None, on_unblocked_set=None):
        self.items = []
        self.index = -1
        self.blocked = False
        self.on_unblocked_set = on_unblocked_set
        self._initial_data = data

    def blockSignals(self, value):
        old = self.blocked
        self.blocked = bool(value)
        return old

    def clear(self):
        self.items.clear()
        self.index = -1

    def addItem(self, label, data):
        self.items.append((label, data))
        if self._initial_data is not None and data == self._initial_data:
            self.index = len(self.items) - 1

    def setCurrentIndex(self, index):
        self.index = int(index)
        if not self.blocked and self.on_unblocked_set is not None:
            self.on_unblocked_set(self.currentData())

    def currentData(self):
        if 0 <= self.index < len(self.items):
            return self.items[self.index][1]
        return self._initial_data


def _voice_id(name):
    return f"{wave_toy.ARTICULATION_SOURCE_VOICE_PRESET_ID_PREFIX}{name}"


def _source_tuple(item):
    phoneme = item.phoneme
    return (
        phoneme.source_mode,
        phoneme.source_wave_id,
        dict(phoneme.source_recipe_snapshot or {}),
        phoneme.source_audio_path,
        phoneme.source_start_seconds,
        phoneme.source_duration_seconds,
        phoneme.source_pitch_follow,
        phoneme.source_loop_to_fit,
        phoneme.source_gain,
    )


def _integrity_window():
    win = _window_with_chain()
    win.current_phoneme = _phoneme("CURRENT")
    win.current_voice_variation_id = _voice_id("Charles_flat")
    win._refreshing_voice_source_controls = False
    win.selected_phoneme_source_combos = []
    win.voice_source_dock_selector = None
    win.voice_source_dock_status_label = None
    win.voice_source_dock_type_label = None
    win.current_voice_panel_name_label = None
    win.current_voice_panel_type_label = None
    win._read_user_recipes = MethodType(lambda self: [
        {"name": "Charles_flat", "asset_type": "voice_preset", "voice_preset": True, "ui": {"pitch": "flat"}},
        {"name": "Charles_up", "asset_type": "voice_preset", "voice_preset": True, "ui": {"pitch": "up"}},
    ], win)
    win._update_articulation_word_status = MethodType(lambda self: None, win)
    win._update_articulation_waveform_diagnostics_canvas = MethodType(lambda self: None, win)
    win._articulation_inspector_source_key = MethodType(lambda self: "none", win)
    win._refresh_articulation_inspector = MethodType(lambda self: None, win)
    win._current_word_render_signature = MethodType(lambda self: "signature", win)
    win.articulation_word_render_audio = np.zeros((0, 2), dtype=np.float32)
    win.articulation_word_render_signature = None
    win.articulation_last_word_render_created_at = None
    win.articulation_last_word_render_path = None
    return win


def test_create_word_does_not_change_active_voice(monkeypatch):
    win = _integrity_window()
    flat_id = _voice_id("Charles_flat")
    up_id = _voice_id("Charles_up")
    win.current_voice_variation_id = flat_id
    win.apply_voice_wave_variation_to_chain_item(0, flat_id)
    win.voice_source_dock_selector = _SignalSafeCombo(flat_id)
    before = _source_tuple(win.articulation_chain_items[0])

    def render(self):
        self.current_voice_variation_id = up_id
        self.articulation_chain_items[0].phoneme.source_recipe_snapshot = {"name": "Charles_up"}
        return np.ones((16, 2), dtype=np.float32)

    win._render_articulation_word = MethodType(render, win)

    audio = win._render_word_audio_for_current_chain()

    assert audio.size
    assert win.current_voice_variation_id == flat_id
    assert win.voice_source_dock_selector.currentData() == flat_id
    assert _source_tuple(win.articulation_chain_items[0]) == before


def test_render_word_uses_chain_item_source_not_active_voice():
    win = _integrity_window()
    flat_id = _voice_id("Charles_flat")
    up_id = _voice_id("Charles_up")
    win.apply_voice_wave_variation_to_chain_item(0, flat_id)
    win.apply_voice_wave_variation_to_chain_item(1, up_id)
    win.current_voice_variation_id = wave_toy.ARTICULATION_SOURCE_CURRENT
    seen = []

    def render(self):
        seen.extend(dict(item.phoneme.source_recipe_snapshot or {}) for item in self.articulation_chain_items)
        return np.ones((8, 2), dtype=np.float32)

    win._render_articulation_word = MethodType(render, win)
    before = [_source_tuple(item) for item in win.articulation_chain_items]

    win._render_word_audio_for_current_chain()

    assert seen[0]["name"] == "Charles_flat"
    assert seen[1]["name"] == "Charles_up"
    assert [_source_tuple(item) for item in win.articulation_chain_items] == before
    assert win.current_voice_variation_id == wave_toy.ARTICULATION_SOURCE_CURRENT

    win._current_word_audio_is_fresh = MethodType(lambda self: True, win)
    win._speech_display_sequence_for_chain = MethodType(lambda self: "AH + OO", win)
    win._speech_ipa_sequence_for_chain = MethodType(lambda self: "/ɑ/ /u/", win)
    win._speech_chain_metadata_snapshot = MethodType(lambda self: {"items": [item.to_json_dict() for item in self.articulation_chain_items]}, win)
    win.timeline_next_speech_item_id = 1
    win.timeline_speech_cache_dir = wave_toy.Path("/tmp/wavetoy-test-speech-cache")
    win.timeline_speech_bin = []
    win.timeline_selected_speech_item_id = None
    win._timeline_refresh_speech_bin_cards = MethodType(lambda self: None, win)
    win._timeline_debug = MethodType(lambda self, message: None, win)

    item = win._create_rendered_speech_bin_item("word", name="test")

    sources = item.articulation_metadata["render_source_snapshot"]
    assert sources[0]["source_recipe_snapshot"]["name"] == "Charles_flat"
    assert sources[1]["source_recipe_snapshot"]["name"] == "Charles_up"


def test_refresh_voice_source_controls_is_non_destructive():
    win = _integrity_window()
    flat_id = _voice_id("Charles_flat")
    up_id = _voice_id("Charles_up")
    win.apply_voice_wave_variation_to_chain_item(0, flat_id)
    win.current_voice_variation_id = up_id
    before = _source_tuple(win.articulation_chain_items[0])
    win.voice_source_dock_selector = _SignalSafeCombo(up_id)
    win.selected_phoneme_source_combos = [_SignalSafeCombo(up_id)]

    win._refresh_voice_source_controls()

    assert _source_tuple(win.articulation_chain_items[0]) == before
    assert win.current_voice_variation_id == up_id


def test_programmatic_combo_refresh_does_not_apply_voice():
    win = _integrity_window()
    win.articulation_selected_chain_index = 0
    win.current_voice_variation_id = _voice_id("Charles_up")
    win.selected_phoneme_source_combos = [
        _SignalSafeCombo(on_unblocked_set=lambda data: win.apply_voice_wave_variation_to_chain_item(0, str(data)))
    ]
    before = _source_tuple(win.articulation_chain_items[0])

    win._refresh_selected_phoneme_source_combos(win.articulation_chain_items[0])

    assert _source_tuple(win.articulation_chain_items[0]) == before


def test_create_word_restores_source_state_after_exception():
    win = _integrity_window()
    flat_id = _voice_id("Charles_flat")
    up_id = _voice_id("Charles_up")
    win.current_voice_variation_id = flat_id
    win.apply_voice_wave_variation_to_chain_item(0, flat_id)
    before = [_source_tuple(item) for item in win.articulation_chain_items]

    def render(self):
        self.current_voice_variation_id = up_id
        self.articulation_chain_items[0].phoneme.source_recipe_snapshot = {"name": "Charles_up"}
        raise RuntimeError("boom")

    win._render_articulation_word = MethodType(render, win)

    with pytest.raises(RuntimeError):
        win._create_articulation_word()

    assert win.current_voice_variation_id == flat_id
    assert [_source_tuple(item) for item in win.articulation_chain_items] == before
