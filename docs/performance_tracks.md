# Performance Tracks

`PerformanceAsset` version 2 stores canonical `timeline_tracks`. These tracks are the authoritative internal model for Performance Timeline data and future automation execution.

Each `TimelineParameterTrack` stores:

- `track_id`
- `name`
- `track_kind`
- `target_parameter`
- `points`
- `muted`
- `visible`
- `color`
- `lane_order`

Each `TimelineParameterPoint` stores:

- `time_ms`
- `value`
- `curve`
- `label`
- `metadata`

## Track kinds

- `automation`: render or parameter automation such as `accentuation_db` and `pitch_bias_cents`.
- `stress`: bridge/view lane for `SyllableStressMarker` data.
- `pitch`: bridge/view lane for `PitchAutomationPoint` data.
- `musical_grid` and `marker`: reserved for future timing and marker lanes.

## Safe ranges

Values are clamped through `_timeline_value_range()` before display or render sampling. Current explicit ranges include:

- `accentuation_db`: `-24.0` to `24.0`
- `pitch_bias_cents`: `-1200.0` to `1200.0`
- `timing_bias`: `-1.0` to `1.0`
- normalized articulation, voice-box, and resonance targets: `0.0` to `1.0`
- stress bridge lanes: `0.0` to `1.0`
- pitch bridge lanes: `40.0` to `2000.0 Hz`

## Evaluation

`evaluate_timeline_track(track, time_ms)` is the base sampler. It sorts points safely, ignores muted tracks, clamps sampled values, and supports `hold`, `linear`, and `smooth` curves. Invisible tracks still evaluate; visibility only controls editor display.

`automation_envelope_for_parameter()` is the render path for automation targets. Multiple active automation tracks for the same target are summed and clamped.

## Editor behavior

The Performance Timeline canvas supports selecting, dragging, double-click creation, delete-key removal, a millisecond ruler, a playhead, and optional musical-grid snap. The inspector tables remain available for precise fallback edits.

The playhead updates the status line, diagnostics, and waveform overlay sampled-value context. Scrubbing the Performance Timeline moves the playhead without starting overlapping audio playback. During Articulation Word Motion playback, the Performance Timeline playhead follows the motion timeline.
