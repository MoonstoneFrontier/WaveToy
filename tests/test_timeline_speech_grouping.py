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


def _clip(clip_id, name=None, start=0.0, duration=0.1, value=0.25, item_type="syllable"):
    samples = max(1, int(round(duration * wave_toy.SAMPLE_RATE)))
    audio = np.full((samples, 2), value, dtype=np.float32)
    return wave_toy.TimelineClip(
        clip_id=clip_id,
        name=name or f"Clip {clip_id}",
        audio=audio,
        start_time_seconds=start,
        lane=0,
        sample_rate=wave_toy.SAMPLE_RATE,
        source_type=f"articulation_{item_type}_render",
        speech_metadata={"item_type": item_type, "display_sequence": name or f"Clip {clip_id}"},
    )


def _window(tmp_path, clips):
    win = wave_toy.WaveToyWindow.__new__(wave_toy.WaveToyWindow)
    win.timeline_clips = list(clips)
    win.timeline_groups = []
    win.timeline_selected_clip_id = None
    win.timeline_selected_clip_ids = []
    win.timeline_selected_group_id = None
    win.timeline_next_clip_id = max([clip.clip_id for clip in clips] or [0]) + 1
    win.timeline_next_speech_item_id = 1
    win.timeline_speech_bin = []
    win.timeline_speech_bin_widget = None
    win.speech_asset_list_widgets = []
    win.timeline_speech_count_label = None
    win.timeline_canvas = None
    win.timeline_inspector_label = SimpleNamespace(setText=lambda text: setattr(win, "inspector_text", text))
    win.timeline_playhead_seconds = 0.0
    win.timeline_duration_seconds = 0.0
    win.timeline_mix_dirty = False
    win.timeline_preserve_pitch = True
    win.timeline_stretch_quality = "Balanced"
    win.timeline_speech_cache_dir = tmp_path / "Cache" / "Speech"
    win.storage = SimpleNamespace(
        rendered_syllables_dir=tmp_path / "Rendered" / "Syllables",
        rendered_words_dir=tmp_path / "Rendered" / "Words",
        rendered_phrases_dir=tmp_path / "Rendered" / "Phrases",
        write_json=lambda path, data: path.write_text(__import__("json").dumps(data, indent=2), encoding="utf-8"),
    )
    win._timeline_debug = MethodType(lambda self, message: setattr(self, "last_timeline_debug", message), win)
    win._timeline_stretch_debug = MethodType(lambda self, message: setattr(self, "last_stretch_debug", message), win)
    win._mark_project_dirty = MethodType(lambda self, reason: setattr(self, "dirty_reason", reason), win)
    return win


def test_group_selected_clips_as_word_creates_group(tmp_path):
    clips = [_clip(1, "com"), _clip(2, "mu", start=0.12), _clip(3, "ni", start=0.24)]
    win = _window(tmp_path, clips)
    win.timeline_selected_clip_ids = [1, 2, 3]

    group = win._timeline_group_selected("word", name="commun")

    assert group is not None
    assert len(win.timeline_groups) == 1
    assert group.group_type == "word"
    assert group.clip_ids == [1, 2, 3]
    assert [clip.clip_id for clip in win.timeline_clips] == [1, 2, 3]


def test_group_selected_clips_as_phrase_creates_group(tmp_path):
    clips = [_clip(1, "hello", item_type="word"), _clip(2, "world", start=0.2, item_type="word")]
    win = _window(tmp_path, clips)
    win.timeline_selected_clip_ids = [1, 2]

    group = win._timeline_group_selected("phrase", name="hello world")

    assert group is not None
    assert group.group_type == "phrase"
    assert group.clip_ids == [1, 2]


def test_render_selected_clips_to_word_asset(tmp_path):
    clips = [_clip(1, "com", start=0.0, duration=0.1, value=0.5), _clip(2, "mu", start=0.2, duration=0.1, value=0.25)]
    win = _window(tmp_path, clips)
    win.timeline_selected_clip_ids = [1, 2]

    item = win._timeline_render_selected_to_asset("word", name="commu")

    assert item is not None
    assert item.item_type == "word"
    assert item.audio_data.shape[0] >= int(round(0.3 * wave_toy.SAMPLE_RATE))
    gap = item.audio_data[int(round(0.11 * wave_toy.SAMPLE_RATE)): int(round(0.19 * wave_toy.SAMPLE_RATE))]
    assert np.max(np.abs(gap)) == 0.0
    assert item.audio_cache_path is not None
    assert "Rendered/Words" in item.audio_cache_path.replace("\\", "/")
    assert (tmp_path / "Rendered" / "Words").glob("*.wav")
    assert any((tmp_path / "Rendered" / "Words").glob("*.wav"))


def test_render_selected_group_to_phrase_asset(tmp_path):
    clips = [_clip(1, "hello", item_type="word"), _clip(2, "world", start=0.15, item_type="word")]
    win = _window(tmp_path, clips)
    win.timeline_selected_clip_ids = [1, 2]
    group = win._timeline_group_selected("phrase", name="hello world")
    win.timeline_selected_group_id = group.group_id

    item = win._timeline_render_selected_to_asset("phrase", name="hello world")

    assert item is not None
    assert item.item_type == "phrase"
    assert item.audio_cache_path is not None
    assert "Rendered/Phrases" in item.audio_cache_path.replace("\\", "/")
    assert any((tmp_path / "Rendered" / "Phrases").glob("*.wav"))


def test_ungroup_keeps_clips(tmp_path):
    clips = [_clip(1, "com"), _clip(2, "mu", start=0.1)]
    win = _window(tmp_path, clips)
    win.timeline_selected_clip_ids = [1, 2]
    group = win._timeline_group_selected("word", name="commu")
    win.timeline_selected_group_id = group.group_id

    assert win._timeline_ungroup_selected() is True

    assert win.timeline_groups == []
    assert [clip.clip_id for clip in win.timeline_clips] == [1, 2]


def test_group_persistence_roundtrip(tmp_path):
    clips = [_clip(1, "com"), _clip(2, "mu", start=0.12)]
    win = _window(tmp_path, clips)
    win.timeline_selected_clip_ids = [1, 2]
    group = win._timeline_group_selected("word", name="commu")

    metadata = group.metadata()
    restored = wave_toy.TimelineGroup.from_metadata(metadata)
    assert restored is not None
    assert restored.group_id == group.group_id
    assert restored.group_type == "word"
    assert restored.clip_ids == [1, 2]

    rehydrated = win._rehydrate_timeline_groups([metadata])
    assert len(rehydrated) == 1
    assert rehydrated[0].clip_ids == [1, 2]
