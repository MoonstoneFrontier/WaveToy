# Automation Tracks

Automation tracks are persistent parameter lanes used by Performance assets and project snapshots.

## AutomationPoint

Each point stores:

- `time_ms`
- `value`
- `curve`

Supported curve labels are `linear`, `hold`, and `smooth`.

## AutomationTrack

Each track stores:

- `track_id`
- `name`
- `target_parameter`
- `lane_type`
- `points`
- `muted`
- `visible`
- `color`

## Target parameter groups

### Articulation

- `mouth_open`
- `tongue_height`
- `tongue_frontness`
- `lip_rounding`
- `nasal_open`

### Voice box

- `breathiness`
- `rasp`
- `glottal_closure`
- `vocal_fold_tension`

### Resonance

- `resonance_depth`
- `brightness`
- `darkness`
- `nasal_coupling`

### Expression

- `accentuation_db`
- `timing_bias`
- `pitch_bias_cents`

## Waveform editor hook

Task 075 does not add a waveform marker canvas. Automation point marker overlays should be added later when the waveform editor can expose a low-risk overlay API without changing playback or audio lifecycle behavior.
