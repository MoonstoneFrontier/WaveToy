import sys
from types import MethodType

import numpy as np

try:
    import wave_toy
except ImportError:
    sys.modules.pop("wave_toy", None)
    from tests.test_performance_timeline_undo import _install_qt_stubs

    _install_qt_stubs()
    import wave_toy

from tests.test_articulation_chain_card_workflow import _phoneme
from tests.test_voice_render_source_integrity import _integrity_window, _source_tuple, _voice_id


def _progress_window():
    win = _integrity_window()
    win.articulation_chain_items = [
        wave_toy.ArticulationChainItem(_phoneme("A"), duration_ms=100, crossfade_ms=0),
        wave_toy.ArticulationChainItem(_phoneme("B"), duration_ms=200, crossfade_ms=0),
        wave_toy.ArticulationChainItem(_phoneme("C"), duration_ms=300, crossfade_ms=0),
    ]
    win.articulation_word_render_settings = {
        "allow_word_gaps": False,
        "voice_source_progress_mode": wave_toy.VOICE_SOURCE_PROGRESS_CONTINUOUS,
    }
    for index in range(len(win.articulation_chain_items)):
        win.apply_voice_wave_variation_to_chain_item(index, _voice_id("Charles_up"))
    return win


def _progress_ranges(items):
    return [
        (
            item.phoneme.source_progress_start,
            item.phoneme.source_progress_end,
            item.phoneme.source_start_seconds,
            item.phoneme.source_duration_seconds,
        )
        for item in items
    ]


def test_voice_progress_ranges_cover_whole_word():
    win = _progress_window()

    render_items = win._render_chain_items_snapshot()
    ranges = _progress_ranges(render_items)

    assert ranges[0][0] == 0.0
    assert ranges[1][0] > ranges[0][0]
    assert ranges[2][1] == 1.0
    assert ranges == sorted(ranges, key=lambda value: value[0])
    assert ranges[0][1] <= ranges[1][0]
    assert ranges[1][1] <= ranges[2][0]
    assert np.isclose(ranges[0][1], 1.0 / 6.0)
    assert np.isclose(ranges[1][0], 1.0 / 6.0)
    assert np.isclose(ranges[1][1], 0.5)


def test_voice_progress_does_not_reset_each_phoneme():
    win = _progress_window()
    seen = []

    def render(self):
        seen.extend(_progress_ranges(self.articulation_chain_items))
        return np.ones((16, 2), dtype=np.float32)

    win._render_articulation_word = MethodType(render, win)

    win._render_word_audio_for_current_chain()

    assert len(seen) == 3
    assert len({entry[0] for entry in seen}) == 3
    assert not all(entry[2] == 0.0 for entry in seen)


def test_restart_per_phoneme_mode_preserves_old_behavior():
    win = _progress_window()
    win.articulation_word_render_settings["voice_source_progress_mode"] = wave_toy.VOICE_SOURCE_PROGRESS_RESTART

    render_items = win._render_chain_items_snapshot()

    assert all(item.phoneme.source_start_seconds == 0.0 for item in render_items)
    assert all(item.phoneme.source_progress_start == 0.0 for item in render_items)
    assert all(item.phoneme.source_progress_end == 1.0 for item in render_items)


def test_continuous_progress_does_not_mutate_editable_chain():
    win = _progress_window()
    before = [_source_tuple(item) for item in win.articulation_chain_items]

    def render(self):
        self.articulation_chain_items[1].phoneme.source_start_seconds = 123.0
        return np.ones((16, 2), dtype=np.float32)

    win._render_articulation_word = MethodType(render, win)

    win._render_word_audio_for_current_chain()

    assert [_source_tuple(item) for item in win.articulation_chain_items] == before


def test_render_source_snapshot_records_progress_ranges():
    win = _progress_window()
    win._current_word_audio_is_fresh = MethodType(lambda self: False, win)
    win._render_articulation_word = MethodType(lambda self: np.ones((16, 2), dtype=np.float32), win)
    win._speech_display_sequence_for_chain = MethodType(lambda self: "A + B + C", win)
    win._speech_ipa_sequence_for_chain = MethodType(lambda self: "/a/ /b/ /c/", win)
    win.articulation_syllable_markers = []
    win.articulation_phrase_markers = []
    win.timeline_next_speech_item_id = 1
    win.timeline_speech_cache_dir = wave_toy.Path("/tmp/wavetoy-test-speech-cache")
    win.timeline_speech_bin = []
    win.timeline_selected_speech_item_id = None
    win._timeline_refresh_speech_bin_cards = MethodType(lambda self: None, win)
    win._timeline_debug = MethodType(lambda self, message: None, win)

    item = win._create_rendered_speech_bin_item("word", name="progress")

    sources = item.articulation_metadata["render_source_snapshot"]
    assert sources[0]["source_progress_start"] == 0.0
    assert sources[-1]["source_progress_end"] == 1.0
    assert sources[1]["source_start_seconds"] > sources[0]["source_start_seconds"]
