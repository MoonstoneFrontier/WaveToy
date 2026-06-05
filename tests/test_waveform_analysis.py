import json
import sys

import numpy as np

try:
    import wave_toy
except ImportError:
    sys.modules.pop("wave_toy", None)
    from tests.test_performance_timeline_undo import _install_qt_stubs

    _install_qt_stubs()
    import wave_toy


def _sine(freq=440.0, seconds=0.25, sr=44100):
    t = np.arange(int(sr * seconds), dtype=np.float32) / sr
    return np.sin(2 * np.pi * freq * t).astype(np.float32)


def test_empty_audio_analysis_is_safe():
    empty = np.zeros((0, 2), dtype=np.float32)
    assert wave_toy.waveform_peak_series(empty, 128) == []
    assert wave_toy.waveform_rms_series(empty, 128) == []
    assert wave_toy.zero_crossing_count(empty) == 0
    assert wave_toy.estimate_pitch_autocorrelation(empty, 44100) is None
    stats = wave_toy.selection_audio_stats(empty, 44100, 1.0, -1.0)
    assert stats["duration_seconds"] == 0.0
    assert stats["peak"] == 0.0


def test_mono_and_stereo_audio_produce_valid_stats():
    mono = _sine()
    stereo = np.column_stack([mono, mono * 0.5]).astype(np.float32)
    mono_stats = wave_toy.selection_audio_stats(mono, 44100, 0.0, 0.1)
    stereo_stats = wave_toy.selection_audio_stats(stereo, 44100, 0.0, 0.1)
    assert mono_stats["channel_count"] == 1
    assert stereo_stats["channel_count"] == 2
    assert mono_stats["peak"] > 0.9
    assert 0.3 < stereo_stats["rms"] < 0.6


def test_sine_wave_pitch_estimate_is_approximately_correct():
    tone = _sine(440.0, seconds=0.5)
    pitch = wave_toy.estimate_pitch_autocorrelation(tone, 44100)
    assert pitch is not None
    assert abs(pitch - 440.0) < 8.0


def test_autocorrelation_workload_is_capped_for_long_audio(monkeypatch):
    captured = {}
    original_correlate = wave_toy.np.correlate

    def spy_correlate(a, v, mode="valid"):
        captured["length"] = len(a)
        return original_correlate(a, v, mode=mode)

    monkeypatch.setattr(wave_toy.np, "correlate", spy_correlate)
    tone = _sine(220.0, seconds=3.0)
    assert wave_toy.estimate_pitch_autocorrelation(tone, 44100) is not None
    assert captured["length"] <= int(44100 * wave_toy.WaveformAnalysisEngine.MAX_AUTOCORRELATION_SECONDS) + 1


def test_zero_crossing_count_works():
    audio = np.array([-1.0, -0.5, 0.25, 1.0, -0.1, 0.2], dtype=np.float32)
    assert wave_toy.zero_crossing_count(audio) == 3


def test_selection_stats_clamp_invalid_ranges():
    tone = _sine(seconds=0.1)
    stats = wave_toy.selection_audio_stats(tone, 44100, 10.0, -4.0)
    assert stats["start_seconds"] == 0.0
    assert 0.09 < stats["end_seconds"] <= 0.1
    assert stats["sample_count"] == len(tone)


def test_spectrogram_summary_is_bounded_quantized_and_json_safe():
    tone = _sine(seconds=1.0)
    summary = wave_toy.simple_spectrogram(tone, 44100, 25.0, 5.0)
    assert summary["preview_frame_count"] <= wave_toy.WaveformAnalysisEngine.MAX_SPECTROGRAM_FRAMES
    assert summary["frequency_band_count"] <= wave_toy.WaveformAnalysisEngine.MAX_SPECTROGRAM_BANDS
    assert summary["preview_encoding"] == "uint8_normalized"
    payload = json.dumps(summary)
    assert "preview" in payload
    assert len(summary["preview"]) <= wave_toy.WaveformAnalysisEngine.MAX_SPECTROGRAM_FRAMES
    assert all(isinstance(value, int) and 0 <= value <= 255 for row in summary["preview"] for value in row)


def test_waveform_analysis_record_serializes_to_json_with_standard_name():
    tone = _sine(seconds=0.2)
    record = wave_toy.WaveformAnalysisRecord.from_audio(tone, 44100, name="A4", source_kind="test")
    payload = record.to_json_dict()
    assert payload["name"] == "Waveform Analysis - A4"
    assert payload["source_kind"] == "test"
    assert payload["duration_seconds"] > 0.0
    json.dumps(payload)


def test_stable_audio_hash_changes_with_audio_content():
    tone = _sine(seconds=0.1)
    same = tone.copy()
    different = tone.copy()
    different[0] = 0.5
    assert wave_toy.waveform_audio_hash(tone, 44100) == wave_toy.waveform_audio_hash(same, 44100)
    assert wave_toy.waveform_audio_hash(tone, 44100) != wave_toy.waveform_audio_hash(different, 44100)


def test_waveform_canvas_smoke_handles_audio_selection_and_zoom():
    canvas = wave_toy.WaveformAnalysisCanvas()
    stereo = np.column_stack([_sine(seconds=0.05), _sine(seconds=0.05)]).astype(np.float32)
    canvas.set_audio(stereo, 44100)
    assert canvas.duration_seconds() > 0.04
    assert canvas.selection() == (0.0, canvas.duration_seconds())
    canvas.set_zoom(3.0)
    assert canvas.zoom == 3.0
    canvas.fit_to_audio()
    assert canvas.zoom == 1.0


def test_save_load_analysis_payload_does_not_include_raw_audio_arrays(tmp_path):
    tone = _sine(seconds=0.1)
    record = wave_toy.WaveformAnalysisRecord.from_audio(tone, 44100, name="No Raw Audio")
    envelope = wave_toy.AssetLibraryRecord(asset_type="waveform_analysis", name=record.name, payload=record.to_json_dict())
    path = tmp_path / "analysis.json"
    path.write_text(json.dumps(envelope.to_json_dict()), encoding="utf-8")
    loaded = wave_toy.AssetLibraryRecord.from_json_dict(json.loads(path.read_text(encoding="utf-8")))
    serialized = json.dumps(loaded.to_json_dict())
    assert "audio_data" not in serialized
    assert "raw_audio" not in serialized
    assert "preview" in serialized


def test_waveform_analysis_save_load_smoke_uses_waveform_analyses_category(tmp_path):
    storage = wave_toy.WaveToyStorage(root=tmp_path / "WaveToyData")
    record = wave_toy.WaveformAnalysisRecord.from_audio(_sine(seconds=0.1), 44100, name="Storage Smoke")
    envelope = wave_toy.AssetLibraryRecord(asset_type="waveform_analysis", name=record.name, payload=record.to_json_dict())
    saved_path = storage.save_asset(envelope)
    assert saved_path.parent.name == "WaveformAnalyses"
    loaded = wave_toy.AssetLibraryRecord.from_json_dict(storage.read_json(saved_path))
    assert loaded.asset_type == "waveform_analysis"
    assert loaded.name.startswith("Waveform Analysis - ")
    assert "audio_data" not in json.dumps(loaded.to_json_dict())
