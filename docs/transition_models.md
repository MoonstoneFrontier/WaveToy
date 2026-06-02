# Phoneme-Pair Transition Models

WaveToy uses a render-only `PhonemePairTransitionModel` registry to make **Continuous Mouth Motion** transitions less generic while keeping saved articulation chains compatible.

## Registry fields

Each model describes how one phoneme family should move into another:

- `model_id`
- `from_family` / `to_family`
- optional `from_phoneme_optional` / `to_phoneme_optional` pair override markers
- `default_transition_ms`
- `curve`
- `formant_motion_weight`
- `voicing_blend_weight`
- `airflow_blend_weight`
- `closure_preservation`
- `burst_preservation`
- `nasal_decay`
- `frication_hold`
- `notes`

The registry is non-destructive: it is resolved during motion sampling and continuous rendering, and it does not mutate saved phoneme presets or saved chain items.

## Family-level models

Initial family-level models include:

- `vowel_to_vowel` — 70 ms, Smoothstep, smooth formant travel and continuous voicing.
- `vowel_to_stop` — 18 ms, Ease In, prepares closure while preserving the following stop.
- `stop_to_vowel` — 35 ms, Ease Out, preserves release burst then opens into the vowel.
- `fricative_to_stop` — 18 ms, Ease In, holds frication before stop closure.
- `stop_to_fricative` — 22 ms, Ease Out, releases into controlled frication.
- `nasal_to_stop` — 28 ms, Ease In Out, decays nasal color into a stop onset.
- `liquid_to_vowel` — 55 ms, Smoothstep, carries liquid coloring into the vowel.
- `glide_to_vowel` — 60 ms, Smoothstep, glides smoothly into the target vowel.
- `vowel_to_fricative` — 35 ms, Ease In, raises airflow without abrupt vowel cutoff.
- `stop_to_liquid` and `stop_to_glide` support targeted English overrides such as T→R and D→Y.

## Specific pair overrides

The registry includes targeted overrides for difficult English transitions:

- S→T strengthens `fricative_to_stop` frication hold and closure preservation.
- T→R uses `stop_to_liquid` with preserved burst and slower formant motion.
- D→Y, T→Y, and K→Y use `stop_to_glide` variants.
- N→D and M→B use stronger `nasal_to_stop` nasal decay, closure preservation, and voicing blend.

## User overrides

Manual transition settings remain authoritative:

1. If `transition_to_next_ms` is set on a chain item, that duration overrides the model default.
2. If a user selects a non-default transition curve, that curve overrides the model curve.
3. Existing chains that only contain the saved default curve continue to load unchanged; in that neutral case, the model curve can explain and shape the default transition.

## Diagnostics

Continuous rendering and motion sampling expose these diagnostics when a transition model is active:

- `transition_model`
- `transition_model_id`
- `transition_strength`
- `transition_model_duration_reason`
- `transition_model_curve_reason`

## Manual listening checklist

Use Continuous Mouth Motion and render these chains:

- S T AA P
- T R IY
- D Y UW
- T Y UW
- N D AH
- M B AH
- K Y UW
- AH IY
- M AY
- B OY

Listen for preserved S frication before T closure, audible stop bursts into vowels/glides/liquids, nasal color that decays without smearing stop release, smooth liquid/glide-to-vowel motion, stable pitch, no new distortion, and diphthongs remaining single timeline items.
