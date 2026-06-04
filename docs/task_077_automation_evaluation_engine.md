# Task 077 — Unified Automation Evaluation Engine

Task 077 turns the Task 076 Performance Timeline lanes into the shared execution path for automation sampling.

## Shared evaluator

WaveToy now provides one reusable sampler for canonical `TimelineParameterTrack` data:

- `evaluate_timeline_track(track, time_ms)` samples one track at a millisecond timestamp.
- `evaluate_timeline_tracks(tracks, time_ms)` samples all active tracks and sums values by `target_parameter`.
- `automation_value_for_parameter(parameter, time_ms, tracks)` returns the summed automation value for one parameter.
- `automation_envelope_for_parameter(parameter, duration_ms, sample_rate, tracks)` creates a render-rate envelope for one parameter.

The evaluator sorts points before sampling, clamps values through `_timeline_value_range()`, ignores muted tracks, and treats `visible` as a UI-only flag. Empty tracks return no sampled value. One-point tracks hold their point value after the point time; before the first point the parameter contributes no value.

## Curves

Supported point curves are:

- `hold`: keep the left point value until the next point.
- `linear`: interpolate directly from the left point to the right point.
- `smooth`: use smoothstep easing between the left and right points.

Unsupported curve names are normalized back to `linear` when points are created or edited.

## Render flow

`accentuation_db` and `pitch_bias_cents` both sample through `automation_envelope_for_parameter()` during word render. The render path works on a copy of the rendered word audio and does not mutate chain items or saved phoneme presets.

`accentuation_db` remains a non-destructive gain envelope clamped to `-24..24 dB`.

`pitch_bias_cents` is intentionally conservative: the sampled envelope is reduced to a median active bias, limited to `±300 cents`, and blended only into regions that look voiced by a lightweight RMS/zero-crossing mask. This avoids shifting stop bursts and harsh fricative noise in most cases, but it is still a post-render approximation rather than frame-aware oscillator resynthesis.

## Diagnostics

Speech diagnostics now include:

- `active_automation_targets`
- `selected_performance_track`
- `selected_track_value_at_playhead`
- `accentuation_db_min` / `accentuation_db_max`
- `pitch_bias_cents_min` / `pitch_bias_cents_max`

The Performance Timeline status line also shows the selected track's sampled value at the current playhead.

## Stress and pitch bridges

Syllable stress and pitch-curve compatibility remain intact. Helper functions create derived timeline lanes from existing `SyllableStressMarker` and `PitchAutomationPoint` data, and write edits on those bridge lanes back to the original models. These helpers do not add automatic syllable detection and do not replace NoteEvent-derived pitch behavior.
