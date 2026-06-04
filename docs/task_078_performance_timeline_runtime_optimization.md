# Task 078 — Performance Timeline Runtime Optimization

Task 078 builds on the Task 077 unified automation evaluator by adding a compiled runtime path for `TimelineParameterTrack` data. The goal is to keep long phrases, singing phrases, and dense automation lanes responsive without changing the audible behavior of existing `accentuation_db` or `pitch_bias_cents` tracks.

## Compiled track model

`CompiledTimelineTrack` is an in-memory runtime representation only. It is not stored in project JSON and does not replace the persistent `TimelineParameterTrack` model.

Compiled fields:

- `track_id`
- `target_parameter`
- `track_kind`
- `muted`
- `points`
- `segments`
- `value_range`
- `source_hash`

Compilation sorts points, normalizes unsupported curve names to `linear`, clamps point values through `_timeline_value_range()`, and builds adjacent point pairs into runtime segments. `visible` is intentionally excluded from the runtime source hash because visibility is UI-only. Muted tracks still compile, but their compiled evaluator returns no contribution.

## Segment evaluation

`evaluate_compiled_track(compiled_track, time_ms)` preserves the Task 077 point evaluator semantics:

- No contribution before the first point.
- One-point tracks hold their single value from the point onward.
- `hold` keeps the left point value until the next point.
- `linear` interpolates directly between adjacent points.
- `smooth` uses the same smoothstep curve as Task 077.
- After the last point, the last value is held.

The legacy `evaluate_timeline_track()` helper remains available for compatibility and for parity checks.

## Envelope cache

`compiled_envelope_for_parameter(parameter, duration_ms, sample_rate, tracks)` generates numeric `float32` parameter envelopes from compiled tracks and caches only those envelopes. It does not cache raw rendered audio.

The cache key includes:

- parameter
- duration in milliseconds
- sample rate
- timeline tracks hash

The timeline tracks hash includes track identity, target, kind, mute state, and normalized points. It excludes `visible`. Moving points, changing values, changing curves, adding/removing tracks, and muting/unmuting tracks changes the hash and naturally misses the old cache entry. The application also clears the bounded cache when performance timeline edits mark the render dirty.

The cache is bounded by entry count and memory budget so repeated render previews can reuse small numeric envelopes without accumulating unbounded data.

## Runtime diagnostics

Compact diagnostics are available in the Performance Timeline status line and Speech Diagnostics:

- `compiled_track_count`
- `active_compiled_track_count`
- `envelope_cache_hits`
- `envelope_cache_misses`
- `envelope_generation_ms`
- `timeline_tracks_hash` short form in the UI
- `automation_runtime_backend`

The UI reports summary counters only and avoids dumping raw envelope arrays.

## Runtime inspector

The Performance Timeline tab now includes a compact runtime inspector line for the selected track. It reports selected track name, target parameter, point count, segment count, current sampled value at the playhead, min/max compiled point values, muted/visible state, and a short source hash.

## Self-check process

`_timeline_evaluation_self_check()` creates in-memory tracks for empty, one-point, hold, linear, smooth, muted, and out-of-range scenarios. It compares `evaluate_timeline_track()` with `evaluate_compiled_track()` across sample times using a small tolerance.

This self-check is intentionally lightweight and framework-free. It is available for manual/debug use and is not required for normal project loading.

## Render migration

The word render automation path now routes `accentuation_db` and `pitch_bias_cents` through `compiled_envelope_for_parameter()`. The Task 077 public helper `automation_envelope_for_parameter()` remains available and delegates to the compiled/cached path.
