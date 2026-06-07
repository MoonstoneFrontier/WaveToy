import sys
from types import MethodType, SimpleNamespace

import numpy as np

try:
    import wave_toy
except ImportError:
    sys.modules.pop("wave_toy", None)
    from tests.test_performance_timeline_undo import _install_qt_stubs

    _install_qt_stubs()
    import wave_toy

from tests.test_articulation_chain_card_workflow import _window_with_chain


def _preview_window():
    win = _window_with_chain()
    win.articulation_word_render_audio = np.zeros((0, 2), dtype=np.float32)
    win.articulation_word_render_signature = None
    win.timeline_speech_bin = []
    win._can_start_playback = MethodType(lambda self, show_status=True: True, win)
    win._stop_phoneme_preview = MethodType(lambda self, checked=False: None, win)
    win._stop_articulation_motion = MethodType(lambda self, checked=False: None, win)
    win._show_non_modal_status = MethodType(lambda self, message, timeout_ms=2500: None, win)
    win._articulation_word_render_mode = MethodType(lambda self: wave_toy.ARTICULATION_WORD_RENDER_CONTINUOUS, win)
    win._log_play_word_render_path = MethodType(lambda self, render_mode, audio, cached_reused, fresh_render_created: None, win)
    win._current_word_audio_is_fresh = MethodType(lambda self: False, win)
    return win


def test_preview_word_uses_render_word_audio_path(monkeypatch):
    win = _preview_window()
    known_audio = np.ones((12, 2), dtype=np.float32)
    calls = {"render": 0, "play": [], "assets_before": len(getattr(win, "timeline_speech_bin", []))}

    def render(self):
        calls["render"] += 1
        self.articulation_word_render_audio = known_audio
        self.articulation_word_render_signature = "fresh"
        self._current_word_audio_is_fresh = MethodType(lambda inner: True, self)
        return known_audio

    def start_motion(self, *, loop=False, speed=1.0, audio=None):
        self._play_audio_array(audio)

    win._render_word_audio_for_current_chain = MethodType(render, win)
    win._start_articulation_motion = MethodType(start_motion, win)
    win._play_audio_array = MethodType(lambda self, audio: calls["play"].append(audio), win)

    win._play_articulation_word()

    assert calls["render"] == 1
    assert calls["play"] == [known_audio]
    assert len(getattr(win, "timeline_speech_bin", [])) == calls["assets_before"]


def test_preview_word_does_not_rerender_when_audio_is_fresh():
    win = _preview_window()
    cached_audio = np.full((10, 2), 0.5, dtype=np.float32)
    played = []
    win.articulation_word_render_audio = cached_audio
    win.articulation_word_render_signature = "matching"
    win._current_word_audio_is_fresh = MethodType(lambda self: True, win)
    win._render_word_audio_for_current_chain = MethodType(lambda self: (_ for _ in ()).throw(AssertionError("rerendered")), win)
    win._start_articulation_motion = MethodType(lambda self, *, loop=False, speed=1.0, audio=None: self._play_audio_array(audio), win)
    win._play_audio_array = MethodType(lambda self, audio: played.append(audio), win)

    win._play_articulation_word()

    assert played == [cached_audio]


def test_preview_word_does_not_play_stale_audio_after_render_failure(monkeypatch):
    win = _preview_window()
    stale_audio = np.full((8, 2), 0.25, dtype=np.float32)
    played = []
    win.articulation_word_render_audio = stale_audio
    win.articulation_word_render_signature = "old"
    win._current_word_audio_is_fresh = MethodType(lambda self: False, win)
    win._render_word_audio_for_current_chain = MethodType(lambda self: np.zeros((0, 2), dtype=np.float32), win)
    win._start_articulation_motion = MethodType(lambda self, *, loop=False, speed=1.0, audio=None: self._play_audio_array(audio), win)
    win._play_audio_array = MethodType(lambda self, audio: played.append(audio), win)
    monkeypatch.setattr(wave_toy.QMessageBox, "information", lambda *args, **kwargs: None, raising=False)

    win._play_articulation_word()

    assert played == []


def test_regression_suite_audition_uses_preview_word_path():
    win = wave_toy.WaveToyWindow.__new__(wave_toy.WaveToyWindow)
    calls = []
    win._load_speech_regression_entry_to_chain = MethodType(lambda self, checked=False: calls.append("load"), win)
    win._play_articulation_word = MethodType(lambda self, checked=False: calls.append("preview_word"), win)

    win._preview_speech_regression_entry()

    assert calls == ["load", "preview_word"]


def test_create_word_still_saves_asset(monkeypatch):
    win = _window_with_chain()
    rendered = np.ones((14, 2), dtype=np.float32)
    win.articulation_word_render_audio = np.zeros((0, 2), dtype=np.float32)
    win.articulation_word_render_signature = None
    win.articulation_last_render_source_snapshot = []
    win.timeline_next_speech_item_id = 1
    win.timeline_speech_bin = []
    win.timeline_selected_speech_item_id = None
    win._speech_cache_audio = MethodType(lambda self, audio, prefix, item_id: None, win)
    win._timeline_refresh_speech_bin_cards = MethodType(lambda self: None, win)
    win._timeline_debug = MethodType(lambda self, message: None, win)
    win._speech_display_sequence_for_chain = MethodType(lambda self: "AH + OO", win)
    win._speech_ipa_sequence_for_chain = MethodType(lambda self: "/ɑ/ /u/", win)
    win._speech_chain_metadata_snapshot = MethodType(lambda self: {"items": [item.to_json_dict() for item in self.articulation_chain_items]}, win)
    win._articulation_word_render_mode = MethodType(lambda self: wave_toy.ARTICULATION_WORD_RENDER_CONTINUOUS, win)
    win._current_word_render_signature = MethodType(lambda self: "signature", win)
    win._current_word_audio_is_fresh = MethodType(lambda self: bool(self.articulation_word_render_audio.size), win)
    win._suggested_chain_asset_name = MethodType(lambda self, include_render_mode=False: "test_word", win)
    win._save_library_asset = MethodType(lambda self, *args, **kwargs: None, win)
    win.articulation_word_status_label = SimpleNamespace(setText=lambda text: None)

    def render(self):
        self.articulation_word_render_audio = rendered
        self.articulation_word_render_signature = "signature"
        return rendered

    win._render_word_audio_for_current_chain = MethodType(render, win)
    monkeypatch.setattr(wave_toy.QInputDialog, "getText", lambda *args, **kwargs: ("created", True), raising=False)

    audio = win._create_articulation_word()

    assert audio is rendered
    assert len(win.timeline_speech_bin) == 1
    assert isinstance(win.timeline_speech_bin[0], wave_toy.SpeechBinItem)
    assert win.timeline_speech_bin[0].name == "created"
