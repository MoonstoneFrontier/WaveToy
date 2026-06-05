import copy
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


def test_empty_chain_returns_empty_curve_points_and_safe_summary():
    points = wave_toy.build_motion_curve_points([])

    assert points == []
    summary = wave_toy.summarize_motion_curve_points(points)
    assert summary.frame_count == 0
    assert summary.duration_ms == 0.0


def test_simple_one_phoneme_chain_produces_hold_samples():
    points = wave_toy.build_motion_curve_points(_chain(["AH"], durations=[100]), sample_step_ms=25)

    assert len(points) >= 2
    assert {point.segment_kind for point in points} == {"hold"}
    assert all(point.phoneme.startswith("AH") for point in points)


def test_two_phoneme_chain_with_transition_produces_transition_samples():
    points = wave_toy.build_motion_curve_points(_chain(["AH", "M"], durations=[100, 100], transitions=[50]), sample_step_ms=10)

    transition_points = [point for point in points if point.segment_kind == "transition"]
    assert transition_points
    assert transition_points[0].transition_progress <= transition_points[-1].transition_progress
    assert any("→" in point.phoneme for point in transition_points)


def test_curve_point_count_is_bounded():
    chain = _chain(["AH"] * 40, durations=[5000] * 40, transitions=[250] * 39)

    points = wave_toy.build_motion_curve_points(chain, sample_step_ms=1)

    assert len(points) <= wave_toy.MOTION_CURVE_MAX_POINTS
    assert len(points) == wave_toy.MOTION_CURVE_MAX_POINTS


def test_sampled_values_stay_within_expected_normalized_ranges():
    points = wave_toy.build_motion_curve_points(_chain(["AH", "S", "M"], transitions=[40, 40]), sample_step_ms=10)

    for point in points:
        for field_name in wave_toy.MOTION_CURVE_FIELDS:
            assert 0.0 <= getattr(point, field_name) <= 1.0
        assert 0.0 <= point.transition_progress <= 1.0


def test_transition_summary_handles_zero_transitions():
    points = wave_toy.build_motion_curve_points(_chain(["AH"], durations=[120]))
    segments = wave_toy.motion_timeline_segments_from_articulation_segments(wave_toy.build_articulation_motion_segments_for_chain(_chain(["AH"], durations=[120]))[0])

    summary = wave_toy.analyze_motion_transitions(segments, points)

    assert summary.transition_count == 0
    assert "0 transitions" in wave_toy.motion_transition_analysis_text(summary)


def test_transition_summary_reports_longest_shortest_average_transition():
    chain = _chain(["AH", "M", "OO"], durations=[100, 100, 100], transitions=[20, 80])
    points = wave_toy.build_motion_curve_points(chain, sample_step_ms=10)
    segments = wave_toy.motion_timeline_segments_from_articulation_segments(wave_toy.build_articulation_motion_segments_for_chain(chain)[0])

    summary = wave_toy.analyze_motion_transitions(segments, points)

    assert summary.transition_count == 2
    assert summary.longest_transition_ms == 80
    assert summary.shortest_transition_ms == 20
    assert summary.average_transition_ms == 50


def test_curve_canvas_can_be_constructed_with_qt_stubs_or_qapp():
    canvas = wave_toy.ArticulationMotionCurveCanvas()

    assert canvas.visible_curves["mouth_open"] is True
    assert canvas.visible_curves["lip_rounding"] is True
    assert canvas.visible_curves["tongue_height"] is True
    assert canvas.visible_curves["closure"] is True
    assert canvas.visible_curves["airflow"] is False


def test_toggling_curve_visibility_does_not_mutate_chain_items():
    chain = _chain(["AH", "M"], transitions=[40])
    before = [copy.deepcopy(item.to_json_dict()) for item in chain]
    canvas = wave_toy.ArticulationMotionCurveCanvas()
    points = wave_toy.build_motion_curve_points(chain)
    segments = wave_toy.motion_timeline_segments_from_articulation_segments(wave_toy.build_articulation_motion_segments_for_chain(chain)[0])

    canvas.set_curve_points(points, segments, 240, 0)
    canvas.set_curve_visible("airflow", True)
    canvas.set_curve_visible("mouth_open", False)

    after = [item.to_json_dict() for item in chain]
    assert after == before


def test_viseme_json_export_schema_remains_unchanged():
    source = wave_toy.Path(wave_toy.__file__).read_text(encoding="utf-8")
    start = source.index('"schema": "wavetoy.viseme_timeline.v1"')
    export_source = source[start : source.index('Path(filename).write_text', start)]

    assert '"viseme_timeline"' in export_source
    assert "motion_curve" not in export_source
    assert "curve_points" not in export_source


def test_animation_json_export_schema_remains_unchanged():
    source = wave_toy.Path(wave_toy.__file__).read_text(encoding="utf-8")
    start = source.index('"schema": "wavetoy.animation_export.v1"')
    export_source = source[start : source.index('Path(filename).write_text', start)]

    assert '"speech_organ_state_frames"' in export_source
    assert '"viseme_timeline"' in export_source
    assert "motion_curve" not in export_source
    assert "curve_points" not in export_source


def test_no_project_serialization_fields_are_added():
    item_payload = _chain(["AH"], durations=[160])[0].to_json_dict()
    source = wave_toy.Path(wave_toy.__file__).read_text(encoding="utf-8")

    assert "motion_curve" not in item_payload
    assert "curve_points" not in item_payload
    assert '"motion_curve"' not in source
    assert '"curve_points"' not in source
