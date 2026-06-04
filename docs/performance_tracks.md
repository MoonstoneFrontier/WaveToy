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

## Task 078 runtime compilation

Performance tracks now have an in-memory compiled runtime form, `CompiledTimelineTrack`. It is derived from `TimelineParameterTrack`, is not persisted, and exists only to make repeated sampling efficient.

Compilation behavior:

- sorts points by time,
- normalizes unsupported curves to `linear`,
- clamps values through `_timeline_value_range()`,
- builds adjacent points into runtime segments,
- excludes `visible` from the source hash because visibility is UI-only,
- keeps muted tracks compiled but inactive during evaluation.

`evaluate_compiled_track()` samples these segments while preserving Task 077 behavior for `hold`, `linear`, `smooth`, before-first-point silence, and after-last-point hold. The compact Runtime inspector in the Performance Timeline tab shows the selected track's point count, segment count, sampled playhead value, min/max point values, mute/visible state, and source hash short form.

Runtime diagnostics shown in the Performance Timeline status and Speech Diagnostics include compiled track counts, active compiled track counts, envelope cache hits/misses, last envelope generation time, timeline hash, and backend name.

## Task 079 unified engine

`PerformanceTimelineEngine` is now the central runtime service for `PerformanceAsset.timeline_tracks`. It owns bridge-lane sync, compiled track access, selected-track sampling, playhead state, timeline hashing, cache invalidation, musical grid data, and runtime diagnostics. `TimelineParameterTrack` remains the persistent model; the engine is an in-memory runtime layer.

The Performance Timeline canvas reads visible lanes and playhead state through the engine. Bridge lanes for pitch and stress are derived from their source models and should be edited only through safe point updates that can write back to those source models.

## Task 080 runtime state ownership

`PerformanceTimelineEngine` is now the owner of Performance Timeline runtime state: playhead position, selected track id, selected point index, dirty generation, and last change reason. `WaveToyWindow` may still expose compatibility mirrors for older table/canvas paths, but those mirrors are synchronized from the engine rather than treated as separate authority.

The engine also owns lightweight runtime callbacks for playhead, selection, track, and diagnostics changes. These callbacks keep UI refresh local and simple while leaving explicit refresh calls in place where they are safer.

Track and point edits should invalidate runtime caches through engine dirty helpers. Project persistence remains unchanged: only canonical timeline tracks and points are saved, not runtime playhead, selection, cache, or diagnostics state.

## Task 082 undo/redo QA notes

Performance Timeline undo/redo stress testing treats bridge lanes as regenerated projections and normal tracks as persisted timeline data. Repeated drag, point delete, and snapshot restore flows should leave selection mirrored from `PerformanceTimelineEngine` with any selected point index clamped to the active track's point count.

The transaction stack is bounded at runtime. Once the undo stack exceeds its configured limit, the oldest transaction is discarded; project files remain unchanged because undo/redo transactions are never serialized.
