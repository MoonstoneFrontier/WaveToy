import sys
from types import MethodType, SimpleNamespace

import numpy as np
import pytest

try:
    import wave_toy
except ImportError:
    sys.modules.pop("wave_toy", None)
    from tests.test_performance_timeline_undo import _install_qt_stubs

    _install_qt_stubs()
    import wave_toy

from tests.test_articulation_chain_card_workflow import _window_with_chain


class _ProgressDialog:
    instances = []

    def __init__(self, *args, **kwargs):
        self.values = []
        self.labels = []
        self.closed = False
        self.cancelled = False
        _ProgressDialog.instances.append(self)

    def setWindowTitle(self, title):
        self.title = title

    def setWindowModality(self, modality):
        self.modality = modality

    def setMinimumDuration(self, value):
        self.minimum_duration = value

    def setAutoClose(self, value):
        self.auto_close = value

    def setAutoReset(self, value):
        self.auto_reset = value

    def setValue(self, value):
        self.values.append(value)

    def setLabelText(self, text):
        self.labels.append(text)

    def show(self):
        self.shown = True

    def close(self):
        self.closed = True

    def cancel(self):
        self.cancelled = True


class _App:
    def __init__(self):
        self.processed = 0

    def processEvents(self):
        self.processed += 1


def _progress_window(monkeypatch):
    _ProgressDialog.instances.clear()
    app = _App()
    monkeypatch.setattr(wave_toy, "QProgressDialog", _ProgressDialog)
    monkeypatch.setattr(wave_toy.QApplication, "instance", staticmethod(lambda: app), raising=False)
    monkeypatch.setattr(wave_toy.QMessageBox, "information", lambda *args, **kwargs: None, raising=False)
    win = _window_with_chain()
    win.word_render_progress_dialog = None
    win.word_render_progress_stage = ""
    win.articulation_word_render_audio = np.zeros((0, 2), dtype=np.float32)
    win.articulation_word_render_signature = None
    win.articulation_last_word_render_created_at = None
    win.articulation_last_word_render_path = None
    win.articulation_last_render_source_snapshot = []
    win._snapshot_voice_source_ui_state = MethodType(lambda self: {"voice": "before"}, win)
    win._restore_voice_source_ui_state = MethodType(lambda self, state: None, win)
    win._render_chain_items_snapshot = MethodType(lambda self: [item for item in self.articulation_chain_items], win)
    win._voice_source_field_snapshot = MethodType(lambda self, phoneme: {"name": phoneme.name}, win)
    win._current_word_render_signature = MethodType(lambda self: "signature", win)
    win._update_articulation_word_status = MethodType(lambda self: None, win)
    win._update_articulation_waveform_diagnostics_canvas = MethodType(lambda self: None, win)
    win._articulation_inspector_source_key = MethodType(lambda self: "none", win)
    win._refresh_articulation_inspector = MethodType(lambda self: None, win)
    win._show_non_modal_status = MethodType(lambda self, message, timeout_ms=2500: setattr(self, "last_status", message), win)
    return win, app


def test_create_word_starts_progress(monkeypatch):
    win, app = _progress_window(monkeypatch)
    win._render_articulation_word = MethodType(lambda self: np.ones((8, 2), dtype=np.float32), win)

    audio = win._render_word_audio_for_current_chain()

    assert audio.size
    assert _ProgressDialog.instances
    assert _ProgressDialog.instances[-1].shown is True
    assert app.processed > 0


def test_progress_reaches_done_on_success(monkeypatch):
    win, _app = _progress_window(monkeypatch)
    win._render_articulation_word = MethodType(lambda self: np.ones((8, 2), dtype=np.float32), win)

    win._render_word_audio_for_current_chain()

    dialog = _ProgressDialog.instances[-1]
    assert "Done" in dialog.labels
    assert dialog.values[-1] == 100
    assert dialog.closed is True
    assert win.word_render_progress_dialog is None


def test_progress_closes_or_reports_failure_on_render_exception(monkeypatch):
    win, _app = _progress_window(monkeypatch)

    def fail(self):
        raise RuntimeError("boom")

    win._render_articulation_word = MethodType(fail, win)

    with pytest.raises(RuntimeError):
        win._render_word_audio_for_current_chain()

    dialog = _ProgressDialog.instances[-1]
    assert dialog.cancelled is True
    assert win.word_render_progress_dialog is None
    assert "boom" in win.last_status


def test_preview_word_can_render_with_progress_without_creating_speech_asset(monkeypatch):
    win, _app = _progress_window(monkeypatch)
    win.timeline_speech_bin = []
    win._can_start_playback = MethodType(lambda self, show_status=True: True, win)
    win._stop_phoneme_preview = MethodType(lambda self, checked=False: None, win)
    win._stop_articulation_motion = MethodType(lambda self, checked=False: None, win)
    win._current_word_audio_is_fresh = MethodType(lambda self: False, win)
    win._log_play_word_render_path = MethodType(lambda self, *args: None, win)
    win._start_articulation_motion = MethodType(lambda self, *, loop=False, speed=1.0, audio=None: setattr(self, "played_audio", audio), win)
    win._render_articulation_word = MethodType(lambda self: np.ones((10, 2), dtype=np.float32), win)

    win._play_articulation_word()

    assert len(win.timeline_speech_bin) == 0
    assert getattr(win, "played_audio").shape == (10, 2)
    assert _ProgressDialog.instances[-1].closed is True


def test_create_word_can_render_with_progress_and_still_creates_speech_asset(monkeypatch):
    win, _app = _progress_window(monkeypatch)
    win.timeline_next_speech_item_id = 1
    win.timeline_speech_bin = []
    win.timeline_selected_speech_item_id = None
    win.timeline_speech_cache_dir = wave_toy.Path("/tmp/wavetoy-test-speech-cache")
    win._speech_cache_audio = MethodType(lambda self, audio, prefix, item_id: None, win)
    win._timeline_refresh_speech_bin_cards = MethodType(lambda self: None, win)
    win._timeline_debug = MethodType(lambda self, message: None, win)
    win._speech_display_sequence_for_chain = MethodType(lambda self: "AH + OO", win)
    win._speech_ipa_sequence_for_chain = MethodType(lambda self: "/ɑ/ /u/", win)
    win._speech_chain_metadata_snapshot = MethodType(lambda self: {"items": [item.to_json_dict() for item in self.articulation_chain_items]}, win)
    win._articulation_word_render_mode = MethodType(lambda self: wave_toy.ARTICULATION_WORD_RENDER_CONTINUOUS, win)
    win._current_word_audio_is_fresh = MethodType(lambda self: bool(self.articulation_word_render_audio.size), win)
    win._suggested_chain_asset_name = MethodType(lambda self, include_render_mode=False: "test_word", win)
    win._save_library_asset = MethodType(lambda self, *args, **kwargs: None, win)
    win._chain_custom_transition_summary = MethodType(lambda self: "default transitions", win)
    win.articulation_word_status_label = SimpleNamespace(setText=lambda text: setattr(win, "status_text", text))
    win._render_articulation_word = MethodType(lambda self: np.ones((14, 2), dtype=np.float32), win)
    monkeypatch.setattr(wave_toy.QInputDialog, "getText", lambda *args, **kwargs: ("created", True), raising=False)

    audio = win._create_articulation_word()

    assert audio.size
    assert len(win.timeline_speech_bin) == 1
    assert win.timeline_speech_bin[0].name == "created"
    assert _ProgressDialog.instances[-1].closed is True
    assert "Done" in _ProgressDialog.instances[-1].labels
