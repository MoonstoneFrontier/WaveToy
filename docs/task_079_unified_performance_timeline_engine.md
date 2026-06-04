# Task 079 — Unified Performance Timeline Engine

Task 079 turns the compiled Performance Timeline runtime from Task 078 into a shared `PerformanceTimelineEngine` service. The engine is intentionally lightweight and remains in `wave_toy.py` while WaveToy is still primarily a single-file desktop app.

## Engine responsibilities

`PerformanceTimelineEngine` owns the runtime view of time-based performance data:

- canonical `timeline_tracks`
- bridge-lane synchronization for pitch and stress data
- compiled track access and timeline hashing
- sampled track values
- automation envelopes
- pitch and stress envelopes
- musical beat/measure grid data
- playhead state
- runtime diagnostics

Persistent project JSON still stores the same public models (`PerformanceAsset`, `TimelineParameterTrack`, `PitchAutomationPoint`, `SyllableStressMarker`, and `MusicalTimingSettings`). The engine is an in-memory service, not a new serialized format.

## Bridge lanes

Pitch and stress remain authored by their existing data models. The engine converts them into derived timeline lanes so the Performance Timeline can display and evaluate them with automation tracks:

- `PitchAutomationPoint` → `track_kind="pitch"`, `target_parameter="pitch_hz"`
- `SyllableStressMarker` → `track_kind="stress"`, `target_parameter="stress_level"`

Safe bridge edits still write back through the existing helper functions when a point maps to an existing source item. The task does not add automatic syllable detection, vibrato editing, or portamento editing.

## Musical grid bridge

Musical Timing remains off by default and millisecond speech timing remains authoritative. The engine now exposes:

- `beat_grid(duration_ms)`
- `measure_grid(duration_ms)`
- `current_beat(time_ms)`
- `current_measure(time_ms)`
- `snap_time_ms(time_ms)`

These helpers respect `MusicalTimingSettings`. When Musical Timing is disabled, beat/measure queries return millisecond-friendly defaults and no speech transitions are quantized.

## Render path cleanup

Word-render automation now asks the engine for `accentuation_db` and `pitch_bias_cents` envelopes. The behavior remains conservative: gain automation is applied to a render copy, and pitch bias keeps the Task 078 voiced-region approximation rather than mutating phoneme presets or chain items.

## Diagnostics ownership

Speech Diagnostics and the Performance Timeline status read from `PerformanceTimelineEngine.diagnostics()`. The diagnostics include the runtime backend, compiled counts, cache hits/misses, last envelope generation time, timeline hash, bridge activity, musical-grid activity, and playhead state.

## Compatibility wrapper policy

Public helper functions such as `compiled_timeline_tracks()`, `automation_envelope_for_parameter()`, `evaluate_timeline_track()`, and `quantize_ms_to_grid()` remain available. Window code delegates runtime timeline work to the engine where practical, while compatibility helpers keep older callers and saved project data stable.
