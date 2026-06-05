import sys

try:
    import wave_toy
except ImportError:
    sys.modules.pop("wave_toy", None)
    from tests.test_performance_timeline_undo import _install_qt_stubs

    _install_qt_stubs()
    import wave_toy


def _chain(symbols, durations=None, transitions=None):
    durations = durations or [200 for _ in symbols]
    items = []
    for index, symbol in enumerate(symbols):
        phoneme = wave_toy._phoneme_from_preset_symbol(symbol)
        item = wave_toy.ArticulationChainItem(phoneme=phoneme, duration_ms=durations[index])
        if transitions and index < len(transitions):
            item.transition_to_next_ms = transitions[index]
        items.append(item)
    return items


def _harness(symbols=("AH", "M", "OO"), durations=None, transitions=None):
    window = object.__new__(wave_toy.WaveToyWindow)
    window.articulation_chain_items = _chain(list(symbols), durations, transitions)
    window.articulation_playhead_ms = 0.0
    window.articulation_timeline_zoom = 1.0
    return window


def test_motion_timeline_builds_from_articulation_chain():
    window = _harness(("AH", "M"), durations=[240, 180], transitions=[60])
    render_phonemes = [item.phoneme_for_render() for item in window.articulation_chain_items]

    segments, total_ms, _stops, _bursts = window._build_articulation_envelope_timeline(render_phonemes=render_phonemes)
    motion_segments = wave_toy.motion_timeline_segments_from_articulation_segments(segments)

    assert [segment.kind for segment in motion_segments] == ["hold", "transition", "hold"]
    assert [segment.label for segment in motion_segments] == ["AH", "AH→M", "M"]
    assert total_ms == 480


def test_viseme_track_updates_after_chain_edits():
    first = _harness(("AH", "M"), durations=[200, 200], transitions=[50])
    first_segments = wave_toy.motion_timeline_segments_from_articulation_segments(
        first._build_articulation_envelope_timeline(render_phonemes=[item.phoneme_for_render() for item in first.articulation_chain_items])[0]
    )

    edited = _harness(("AH", "M", "OO"), durations=[200, 200, 200], transitions=[50, 50])
    edited_segments = wave_toy.motion_timeline_segments_from_articulation_segments(
        edited._build_articulation_envelope_timeline(render_phonemes=[item.phoneme_for_render() for item in edited.articulation_chain_items])[0]
    )

    assert len(wave_toy.viseme_timeline_segments_from_motion_segments(first_segments)) == 2
    assert len(wave_toy.viseme_timeline_segments_from_motion_segments(edited_segments)) == 3


def test_timeline_duration_matches_motion_duration():
    window = _harness(("AH", "M", "OO"), durations=[100, 150, 200], transitions=[25, 35])
    render_phonemes = [item.phoneme_for_render() for item in window.articulation_chain_items]

    segments, total_ms, _stops, _bursts = window._build_articulation_envelope_timeline(render_phonemes=render_phonemes)
    motion_segments = wave_toy.motion_timeline_segments_from_articulation_segments(segments)

    assert total_ms == 510
    assert motion_segments[-1].end_ms == total_ms


def test_playhead_highlight_updates_correctly():
    motion_segments = [
        wave_toy.MotionTimelineSegment("AH", "hold", 0, 200),
        wave_toy.MotionTimelineSegment("AH→M", "transition", 200, 250),
        wave_toy.MotionTimelineSegment("M", "hold", 250, 450),
    ]

    assert motion_segments[0].contains_ms(100)
    assert motion_segments[1].contains_ms(225)
    assert motion_segments[2].contains_ms(400)
    assert not motion_segments[0].contains_ms(200)
    assert motion_segments[1].contains_ms(200)


def test_final_segment_endpoint_is_active_without_boundary_overlap():
    canvas = object.__new__(wave_toy.ArticulationMotionTimelineCanvas)
    canvas.total_ms = 450.0
    canvas.playhead_ms = 450.0
    motion_segments = [
        wave_toy.MotionTimelineSegment("AH", "hold", 0, 200),
        wave_toy.MotionTimelineSegment("AH→M", "transition", 200, 250),
        wave_toy.MotionTimelineSegment("M", "hold", 250, 450),
    ]

    assert not motion_segments[-1].contains_ms(450)
    assert canvas._active_index(motion_segments) == 2


def test_motion_timeline_contains_transition_segments():
    window = _harness(("AH", "M"), transitions=[45])
    render_phonemes = [item.phoneme_for_render() for item in window.articulation_chain_items]

    segments = window._build_articulation_envelope_timeline(render_phonemes=render_phonemes)[0]
    motion_segments = wave_toy.motion_timeline_segments_from_articulation_segments(segments)

    assert any(segment.kind == "transition" and segment.duration_ms == 45 for segment in motion_segments)


def test_viseme_lane_contains_expected_count():
    motion_segments = [
        wave_toy.MotionTimelineSegment("Closed", "hold", 0, 100, index=0),
        wave_toy.MotionTimelineSegment("Closed→Open", "transition", 100, 130, index=0),
        wave_toy.MotionTimelineSegment("Open", "hold", 130, 280, index=1),
        wave_toy.MotionTimelineSegment("Open→Rounded", "transition", 280, 320, index=1),
        wave_toy.MotionTimelineSegment("Rounded", "hold", 320, 500, index=2),
    ]

    visemes = wave_toy.viseme_timeline_segments_from_motion_segments(motion_segments)

    assert [segment.viseme for segment in visemes] == ["Closed", "Open", "Rounded"]
    assert len(visemes) == 3


def test_no_serialization_fields_added_for_motion_timeline():
    item = _chain(["AH"], durations=[220])[0]
    payload = item.to_json_dict()

    assert "motion_timeline" not in payload
    assert "viseme_track" not in payload
    assert "motion_summary" not in payload


def test_export_behavior_unchanged():
    source = wave_toy.Path(wave_toy.__file__).read_text(encoding="utf-8")

    assert '"schema": "wavetoy.viseme_timeline.v1"' in source
    assert '"schema": "wavetoy.animation_export.v1"' in source
    assert source.count('Path(filename).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")') == 2


def test_motion_summary_reports_unique_visemes_and_holds():
    visemes = [
        wave_toy.VisemeTimelineSegment("open_vowel", "AH", 0, 100),
        wave_toy.VisemeTimelineSegment("nasal", "M", 100, 200),
        wave_toy.VisemeTimelineSegment("open_vowel", "AA", 200, 300),
    ]

    summary = wave_toy.motion_summary_text(3, 300, 2, 100, visemes)

    assert "2 unique visemes / 3 viseme holds" in summary


def test_motion_summary_empty_chain_is_safe():
    assert "0 unique visemes / 0 viseme holds" in wave_toy.motion_summary_text(0, 0, 0, 0, [])


def test_motion_timeline_canvas_labels_fit_view_not_functional_zoom():
    source = wave_toy.Path(wave_toy.__file__).read_text(encoding="utf-8")
    start = source.index("class ArticulationMotionTimelineCanvas")
    end = source.index("class VocalTractCanvas", start)
    canvas_source = source[start:end]

    assert "fit view" in canvas_source
    assert "functional horizontal zoom is deferred to Task 098" in canvas_source
    assert "zoom {self.zoom" not in canvas_source
