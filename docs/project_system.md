# Project System

WaveToy project snapshots are JSON documents designed for editable synthesis state, not raw audio storage.

## Performance persistence

Canonical performance data lives under `performance.timeline_tracks`. New saves should not duplicate the same data in a top-level `automation_tracks` key.

Legacy Task 075 projects remain supported:

1. load `performance.timeline_tracks` when present;
2. otherwise migrate `performance.automation_tracks`;
3. otherwise read legacy top-level `automation_tracks` as a load-only fallback.

This keeps older projects openable while making `performance` the single authoritative save location.

## Audio storage rule

Generated waveform/audio arrays are not stored in project JSON. Projects may store paths, settings, source metadata, and timeline point data, but rendered arrays remain cache/runtime data.

## Asset library compatibility

Performance assets are saved using the canonical performance schema. Legacy automation-curve assets can still be loaded and are appended as unified timeline parameter tracks.

## Task 080 runtime state is not persisted

Performance Timeline playhead position, selected track, selected point, dirty generation, cache diagnostics, and callback state are runtime-only engine state. They are intentionally excluded from project JSON so Task 076 through Task 079 project files continue to load without migration and new saves do not introduce a schema change.

The future undo/redo path should build transactions around runtime mutations and engine dirty helpers, not by extending the project schema with transient UI state.
