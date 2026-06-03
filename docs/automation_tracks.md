# Automation Tracks

Automation tracks from Task 075 remain load-compatible but are now represented internally by unified timeline lanes.

## Compatibility

Legacy `AutomationTrack` / `AutomationPoint` JSON can still load from:

- `performance.automation_tracks`
- legacy top-level `automation_tracks` when no canonical timeline is present
- `automation_curve` library assets

On load, legacy automation becomes `TimelineParameterTrack(track_kind="automation")` with `TimelineParameterPoint` entries.

## New save behavior

New project snapshots use the canonical `performance.timeline_tracks` schema. WaveToy does not write duplicate top-level `automation_tracks` in normal project snapshots, reducing synchronization risk.

## Active render targets

`accentuation_db` remains non-destructive gain automation. `pitch_bias_cents` is now a second working target, implemented as a lightweight post-render pitch-bias hook and included in the word-render signature through canonical timeline tracks.

## Roadmap

Future automation work should extend the timeline-lane model rather than adding separate time-based containers. Candidate follow-ups include Bezier curves, richer voiced-region pitch integration, marker lanes, and DAW-style lane folding.
