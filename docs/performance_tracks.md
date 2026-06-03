# Performance Tracks

Performance tracks are reusable performance snapshots for speech rendering. A performance contains automation tracks that describe expressive changes over time without changing saved phoneme presets or articulation chain items.

## Performance asset schema

A performance asset stores:

- `performance_id`
- `name`
- `automation_tracks`
- `created_at`
- `modified_at`
- `version`

When imported from the Speech Asset Library, the performance receives a fresh UUID so the imported copy is distinct from the library source.

## Current render behavior

The current render hook applies only `accentuation_db` tracks. The generated audio receives a render-time gain envelope after the selected word render mode returns audio. This keeps the editable chain and presets unchanged.

## Future hooks

Other persisted targets are reserved for future render passes:

- articulation: mouth and nasal parameters
- voice box: breathiness, rasp, glottal closure, vocal fold tension
- resonance: resonance depth, brightness, darkness, nasal coupling
- expression: timing and pitch bias
