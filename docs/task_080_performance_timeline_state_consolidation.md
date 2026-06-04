# Task 080 — Performance Timeline Runtime State Consolidation

Task 080 makes `PerformanceTimelineEngine` the authoritative owner for mutable Performance Timeline runtime state while keeping project JSON unchanged.

## Engine-owned runtime state

The engine now owns:

- `playhead_ms`
- `selected_track_id`
- `selected_point_index`
- `dirty_generation`
- `last_change_reason`

`WaveToyWindow` keeps legacy attributes (`performance_playhead_ms`, `selected_automation_track_id`, and `selected_timeline_point_index`) as compatibility mirrors only. The `_sync_performance_state_from_engine()` helper copies engine state into those mirrors so older UI paths can continue to function while new code reads from the engine.

## Selection API

Selection moves through engine helpers:

- `selected_track()`
- `selected_point()`
- `set_selected_track(track_id)`
- `set_selected_point(track_id, point_index)`
- `clear_selection()`
- `selected_track_value(time_ms=None)`

Selection changes update diagnostics callbacks and status displays but do not invalidate audio envelopes because track data has not changed.

## Playhead API

The playhead moves through engine helpers:

- `set_playhead_ms(time_ms, reason="ui")`
- `playhead_seconds()`
- `scrub_to_ms(time_ms)`
- `reset_playhead()`

Performance Timeline scrubbing, Articulation Motion playback, waveform overlays, and Speech Diagnostics all read the same engine playhead.

## Dirty state and cache invalidation

Runtime invalidation is centralized in the engine:

- `mark_tracks_dirty(reason)`
- `mark_timing_dirty(reason)`
- `mark_bridge_dirty(reason)`
- `mark_runtime_dirty(reason)`
- `invalidate_runtime_cache(reason)`

Track edits, point edits, mute changes, timing changes, and bridge edits bump `dirty_generation` and update `last_change_reason`. Envelope cache clearing remains an engine responsibility; window code should not call `clear_automation_envelope_cache()` directly.

## Lightweight callbacks

The engine exposes optional local callbacks:

- `on_playhead_changed`
- `on_selection_changed`
- `on_tracks_changed`
- `on_diagnostics_changed`

Callbacks are intentionally simple callables, not a new event bus. The engine guards against recursive callback re-entry, and existing explicit UI refresh calls remain in place for safety.

## Diagnostics consolidation

`PerformanceTimelineEngine.diagnostics()` now includes playhead, selection, selected sampled value, dirty generation, last change reason, bridge activity flags, musical-grid activity, compiled track counts, cache hit/miss counters, last generation time, and timeline hash. Performance status text and Speech Diagnostics can use this shared payload instead of recalculating runtime state in `WaveToyWindow`.

## Persistent schema compatibility

Task 080 does not change `PerformanceAsset`, `TimelineParameterTrack`, `TimelineParameterPoint`, `PitchAutomationPoint`, `SyllableStressMarker`, or project JSON layout. Existing Task 076 through Task 079 project files continue to load without a migration.

## Future undo/redo path

The consolidated engine dirty helpers are a future seam for undo/redo transactions. A later transaction layer can wrap track/point/timing mutations, call the same dirty helpers, and attach operation metadata without changing the persistent schema introduced by Tasks 075 through 079.
