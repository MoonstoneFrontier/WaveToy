# Task 081 — Performance Timeline Undo/Redo Transactions

Task 081 adds in-memory undo/redo for Performance Timeline editing while preserving the existing project JSON schema. Transactions are runtime-only, JSON-safe, and intentionally limited to timeline/timing state; raw audio arrays and render buffers are never captured.

## Scope

Undoable operations include:

- Add/delete Performance Timeline tracks.
- Rename tracks.
- Mute/unmute tracks.
- Toggle track visibility.
- Add/delete timeline points.
- Move points from table edits or canvas drags.
- Edit point values and curve names.
- Low-risk musical timing controls, including enablement, BPM, time signature, snap subdivision, count-in, and grid visibility.

Runtime-only selection/playhead operations stay outside the undo stack unless bundled with a structural edit, such as selecting a point and then dragging it.

## Transaction models

`PerformanceEditSnapshot` stores only JSON-safe state:

- Canonical `TimelineParameterTrack` dictionaries.
- `MusicalTimingSettings` as a dictionary.
- Practical selection restoration fields (`selected_track_id`, `selected_point_index`).

`PerformanceEditTransaction` stores:

- `transaction_id`
- `label`
- `created_at`
- `before_state`
- `after_state`
- `affected_track_ids`
- `reason`

These models are in-memory runtime models. They are not included in `PerformanceAsset`, project snapshots, or library exports.

## Stack behavior

The main window owns two runtime stacks:

- `performance_undo_stack`
- `performance_redo_stack`

The undo stack is bounded by `performance_undo_stack_limit` to keep memory use predictable. A new transaction clears the redo stack. Project loading clears both stacks so undo/redo cannot affect state from a previous project session.

Snapshot comparison ignores selection fields when deciding whether to record a transaction. This prevents selection-only UI activity from creating undo entries while still allowing structural edits to restore a useful selected track/point when practical.

## Timing transaction coalescing

Rapid musical timing edits, especially BPM spinbox updates, are coalesced into a single `Musical Timing Change` transaction when they occur within the configured coalescing window. The transaction keeps the first `before_state` and replaces the `after_state` with the latest timing state, so one undo returns to the original timing setting instead of stepping through every intermediate spinbox value.

## Bridge lane restoration

Stress and pitch bridge lanes are derived from source lists (`SyllableStressMarker` and `PitchAutomationPoint`). Undo/redo restoration therefore handles bridge lanes specially:

1. Snapshot tracks are normalized and deduplicated by `track_id`.
2. Bridge tracks are separated from normal timeline tracks.
3. Bridge point edits are written back directly to their source lists.
4. Normal timeline tracks are restored without generating bridge lanes.
5. Bridge lanes are regenerated once from the updated source lists.

This avoids duplicate bridge-track generation while preserving bridge edits that were captured in undo snapshots.

## Engine integration

Undo/redo applies snapshots through the existing `PerformanceTimelineEngine` seams:

- Restores musical timing settings.
- Restores base timeline tracks.
- Regenerates bridge lanes from source data.
- Restores selected track/point where possible.
- Invalidates the runtime cache.
- Marks the project dirty.
- Refreshes timeline/diagnostic UI surfaces.

A runtime restoration guard prevents undo/redo application from recursively creating new transactions through UI or engine callback paths.

## UI

The Edit menu includes:

- **Undo Performance Edit** (`Ctrl+Z`)
- **Redo Performance Edit** (`Ctrl+Shift+Z`)

Menu labels include the next undo/redo transaction label when available. The Performance Timeline status text also reports the last undo/redo action or the currently available undo label.

## Regression coverage

`tests/test_performance_timeline_undo.py` covers the transaction stack and snapshot restoration paths for:

- Add track.
- Delete track.
- Add point.
- Delete point.
- Drag/move point.
- Mute track.
- Coalesced timing changes.
- Bridge restore deduplication and source-marker update.
- Undo/redo after project reload remaining runtime-only.

The tests provide lightweight Qt stubs if local Qt system libraries (for example `libGL`) are unavailable, so the non-GUI transaction logic can still run in headless environments.
