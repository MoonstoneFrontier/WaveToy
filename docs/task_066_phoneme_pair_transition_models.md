# Task 066 — Phoneme-Pair Transition Models

Task 066 adds phoneme-pair-aware transition behavior for Continuous Mouth Motion.

## What changed

- Added a non-destructive `PhonemePairTransitionModel` data model and registry in `wave_toy.py`.
- Continuous render timelines now resolve a transition model for each boundary and use the model default duration when no manual `transition_to_next_ms` exists.
- Motion sampling and continuous audio interpolation now apply model weights for formant motion, voicing blend, airflow blend, frication hold, nasal decay, closure preservation, and burst preservation.
- Visual speech timeline tooltips can show the model id for transition regions.
- Continuous diagnostics include `transition_model`, `transition_model_id`, and `transition_strength`.

## Compatibility

Saved chains remain compatible because transition models are not serialized into chain items. Models are resolved from render copies at preview/render time. Existing phoneme presets are not changed.

## Override rules

Manual settings still win:

- A saved or user-edited `transition_to_next_ms` overrides the model default duration.
- A non-default saved or user-edited `transition_curve` overrides the model curve.
- If no explicit duration exists, the model default duration is used and the diagnostics report why that duration was selected.

## Validation chains

Render these in Continuous Mouth Motion:

- `S T AA P`
- `T R IY`
- `D Y UW`
- `T Y UW`
- `N D AH`
- `M B AH`
- `K Y UW`
- `AH IY`
- `M AY`
- `B OY`

## Manual checks

- Clip Crossfade remains the default render mode.
- Continuous diagnostics show a transition model id during modeled transitions.
- Transition sliders still override modeled default durations.
- Saved chains load unchanged.
- No generated WAV or cache files are staged.
