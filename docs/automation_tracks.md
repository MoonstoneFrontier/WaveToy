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
