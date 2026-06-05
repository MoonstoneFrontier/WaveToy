import json
import sys

try:
    import wave_toy
except ImportError:
    sys.modules.pop("wave_toy", None)
    from tests.test_performance_timeline_undo import _install_qt_stubs

    _install_qt_stubs()
    import wave_toy


def _frames(count=4):
    base = []
    for index in range(count):
        base.append(
            {
                "time_ms": index * 10.0,
                "phoneme": "AH" if index % 2 == 0 else "IY",
                "formants": {
                    "f1": 500.0 + index * 10.0,
                    "f2": 1200.0 + index * 20.0,
                    "f3": 2500.0 + index * 30.0,
                    "resonance_formant_scale": 0.98 + index * 0.01,
                    "nasal_coupling": 0.1 + index * 0.02,
                },
                "resonance_tract_state": {
                    "vocal_tract_length": 0.5 + index * 0.01,
                    "larynx_height": 0.45,
                    "resonance_depth": 0.55,
                    "chest_resonance": 0.4,
                    "head_resonance": 0.6,
                    "nasal_coupling": 0.1 + index * 0.02,
                    "brightness": 0.58,
                    "darkness": 0.42,
                    "formant_scale": 1.0,
                    "formant_shift_f1": 0.0,
                    "formant_shift_f2": 0.0,
                    "formant_shift_f3": 0.0,
                },
            }
        )
    return base


def test_empty_formant_frames_summarize_safely():
    summary = wave_toy.formant_summary_from_frames([])
    assert summary["available"] is False
    assert summary["frame_count"] == 0
    assert summary["f1_min_hz"] is None
    assert summary["status"] == "unavailable"


def test_bounded_formant_preview_caps_output():
    preview = wave_toy.bounded_formant_frames_preview(_frames(20), max_frames=5)
    assert len(preview) == 5
    assert set(preview[0]) == {"time_ms", "phoneme", "f1", "f2", "f3", "resonance_scale", "nasal_coupling"}


def test_vowel_space_points_are_json_safe():
    points = wave_toy.vowel_space_points_from_formants(_frames(3))
    assert len(points) == 3
    assert points[0]["f1_hz"] == 500.0
    json.dumps(points)


def test_formant_summary_computes_min_mean_max_for_f1_f2_f3():
    summary = wave_toy.formant_summary_from_frames(_frames(3))
    assert summary["f1_min_hz"] == 500.0
    assert summary["f1_mean_hz"] == 510.0
    assert summary["f1_max_hz"] == 520.0
    assert summary["f2_mean_hz"] == 1220.0
    assert summary["f3_mean_hz"] == 2530.0


def test_resonance_summary_handles_missing_fields_safely():
    summary = wave_toy.resonance_summary_from_frames([{"time_ms": 0.0, "formants": {"f1": 500.0}}])
    assert summary["available"] is True
    assert summary["vocal_tract_length"] is None
    assert summary["formant_scale"] is None
    json.dumps(summary)


def test_formant_analysis_record_serializes_to_json():
    record = wave_toy.formant_analysis_from_articulation_chain([], _frames(2), 44100, name="Word")
    payload = record.to_json_dict()
    assert payload["name"] == "Formant Analysis - Word"
    assert payload["frame_count"] == 2
    assert payload["phoneme_sequence"] == ["AH", "IY"]
    json.dumps(payload)


def test_formant_analysis_payload_does_not_include_raw_audio_arrays():
    record = wave_toy.formant_analysis_from_articulation_chain([], _frames(2), 44100, name="No Raw")
    serialized = json.dumps(record.to_json_dict())
    assert "audio_data" not in serialized
    assert "raw_audio" not in serialized
    assert "formant_frames_preview" in serialized


def test_imported_audio_source_returns_unavailable_formant_frame_status():
    record = wave_toy.formant_analysis_from_articulation_chain([], _frames(2), 44100, name="Import", source_kind="selected_imported_wav")
    assert record.frame_count == 0
    assert record.formant_frames_preview == []
    assert "No generated formant frames available for imported audio." in record.notes
