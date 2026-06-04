# Automation Tracks Compatibility

Older WaveToy projects may contain automation data in legacy automation-track form. Current projects use canonical `performance.timeline_tracks` instead.

## Canonical model

`timeline_tracks` are the authoritative internal model. New render code samples `TimelineParameterTrack` through the shared evaluation engine instead of using parameter-specific ad-hoc automation logic.

`automation_tracks` remains only for compatibility:

- loading older project snapshots,
- bridging old automation-curve assets,
- exporting legacy-compatible automation payloads where needed,
- temporary adapters while older UI/library paths are migrated.

WaveToy should avoid writing separate live automation state when the same information can be represented as `performance.timeline_tracks`.

## Load migration

On load, legacy automation becomes `TimelineParameterTrack(track_kind="automation")` with `TimelineParameterPoint` entries. If canonical timeline tracks are present, they win.

## Render targets

`accentuation_db` is sampled as a gain envelope and applied to a render copy only.

`pitch_bias_cents` is sampled through the same envelope helper. Pitch bias currently uses a conservative post-render approximation: it limits active bias to `±300 cents` and blends into voiced-looking regions based on RMS and zero-crossing analysis. This is intentionally safer for stops and fricatives, but not a replacement for future frame-aware voiced-source resynthesis.

## Task 078 compiled envelopes and cache

Automation envelopes now route through `compiled_envelope_for_parameter()`. The compatibility helper `automation_envelope_for_parameter()` remains available and delegates to the compiled/cached path.

The envelope cache stores only numeric `float32` parameter envelopes, never rendered audio. Cache keys are built from parameter, duration in milliseconds, sample rate, and the timeline tracks hash. The hash changes when tracks or points change, including point moves and mute toggles; `visible` remains UI-only and is excluded from the runtime source hash.

The cache is bounded by entry count and memory budget. Old entries are evicted least-recently-used style when the budget is exceeded. Runtime diagnostics report cache hit/miss behavior and the last envelope generation time.

`accentuation_db` and `pitch_bias_cents` both use the compiled envelope path. Gain automation and conservative pitch-bias behavior are intended to stay audibly compatible with Task 077 while avoiding repeated point scans for longer or denser phrases.

## Task 079 engine-owned automation envelopes

Automation rendering now routes through `PerformanceTimelineEngine.automation_envelope_for_parameter()`. The compatibility helpers remain in place, but Window render code asks the engine for `accentuation_db` and `pitch_bias_cents` envelopes so diagnostics, hashing, cache behavior, and compiled-track access all come from one runtime service.

This keeps generated audio as a render copy only. Automation never mutates phoneme presets, articulation chain items, or stored raw audio arrays.

## Task 080 cache ownership

Automation envelope cache invalidation is centralized in `PerformanceTimelineEngine.invalidate_runtime_cache()` and the related dirty helpers. Track edits, point edits, mute toggles, bridge changes, and musical-timing changes should mark the engine dirty instead of clearing the envelope cache directly from `WaveToyWindow`.

This does not change automation-track persistence. Legacy automation compatibility remains a load/library bridge into canonical `performance.timeline_tracks`.

## Task 082 render regression notes

Undo/redo restore invalidates the `PerformanceTimelineEngine` runtime cache and clears the current articulation word render signature. Manual QA should render after undo/redo and confirm both `accentuation_db` gain automation and `pitch_bias_cents` automation still route through the compiled envelope path.

Because a new timeline edit clears redo history, cache and diagnostics validation should use the currently restored timeline state rather than expecting redo transactions to survive subsequent edits.
