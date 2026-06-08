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


def _window(tmp_path):
    win = wave_toy.WaveToyWindow.__new__(wave_toy.WaveToyWindow)
    win.timeline_next_speech_item_id = 1
    win.timeline_speech_bin = []
    win.timeline_selected_speech_item_id = None
    win.timeline_speech_bin_widget = None
    win.speech_asset_list_widgets = []
    win.timeline_speech_count_label = None
    win.timeline_speech_cache_dir = tmp_path / "Cache" / "Speech"
    win.storage = SimpleNamespace(
        rendered_syllables_dir=tmp_path / "Rendered" / "Syllables",
        rendered_words_dir=tmp_path / "Rendered" / "Words",
        rendered_phrases_dir=tmp_path / "Rendered" / "Phrases",
        write_json=lambda path, data: path.write_text(__import__("json").dumps(data, indent=2), encoding="utf-8"),
    )
    win._timeline_debug = MethodType(lambda self, message: setattr(self, "last_timeline_debug", message), win)
    return win


def _audio(duration=0.05):
    samples = max(1, int(round(duration * wave_toy.SAMPLE_RATE)))
    return np.full((samples, 2), 0.2, dtype=np.float32)


def test_rendered_syllable_asset_is_saved_under_rendered_syllables(tmp_path):
    win = _window(tmp_path)

    item = win._add_speech_bin_item("com", "syllable", _audio(), "/kom/", "com", {}, "test")

    assert item is not None
    assert item.item_type == "syllable"
    assert item.audio_cache_path is not None
    assert "Rendered/Syllables" in item.audio_cache_path.replace("\\", "/")
    assert any((tmp_path / "Rendered" / "Syllables").glob("*.wav"))
    assert any((tmp_path / "Rendered" / "Syllables").glob("*.rendered-speech.json"))


def test_rendered_word_and_phrase_assets_use_type_specific_dirs(tmp_path):
    win = _window(tmp_path)

    word = win._add_speech_bin_item("communication", "word", _audio(), "", "com + mu", {}, "timeline_word_selection_render")
    phrase = win._add_speech_bin_item("hello world", "phrase", _audio(), "", "hello + world", {}, "timeline_phrase_selection_render")

    assert word is not None and phrase is not None
    assert "Rendered/Words" in word.audio_cache_path.replace("\\", "/")
    assert "Rendered/Phrases" in phrase.audio_cache_path.replace("\\", "/")
    assert len(win.timeline_speech_bin) == 2
    assert win.timeline_selected_speech_item_id == phrase.id
