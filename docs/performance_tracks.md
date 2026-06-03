# Performance Tracks

Performance tracks are the canonical container for non-destructive time-based expression in WaveToy.

## Canonical schema

`PerformanceAsset` version 2 stores `timeline_tracks`, not a separate top-level automation list. Each `TimelineParameterTrack` has:

- `track_id`
- `name`
- `track_kind`
- `target_parameter`
- `points`
- `muted`
- `visible`
- `color`
- `lane_order`

Each `TimelineParameterPoint` has:

- `time_ms`
- `value`
- `curve`
- `label`
- `metadata`

## Track kinds

- `automation`: render or parameter automation such as `accentuation_db` and `pitch_bias_cents`.
- `pitch`: bridge/view lane for pitch curve data.
- `stress`: bridge/view lane for syllable stress markers.
- `musical_grid`: reserved for future beat/measure timelines.
- `marker`: reserved for future expression markers.

## Safe value ranges

- `accentuation_db`: `-24.0` to `24.0`
- `pitch_bias_cents`: `-1200.0` to `1200.0`
- `timing_bias`: `-1.0` to `1.0`
- articulation lanes: normalized `0.0` to `1.0`
- voice-box lanes: normalized `0.0` to `1.0`
- resonance lanes: normalized `0.0` to `1.0`

## Visual editing

The Performance Timeline canvas supports selecting, dragging, double-click creation, delete-key removal, a millisecond ruler, a playhead, and optional musical-grid snap. The inspector tables remain available for precise fallback edits.
