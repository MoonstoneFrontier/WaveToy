# Task 068 — Voice Box Model and Speech Organ Controls

Task 068 expands WaveToy from mouth/nose articulation toward a fuller speech-production model while keeping saved chain data stable.

## Implemented foundations

- Added `VoiceBoxState`, a normalized non-destructive larynx layer derived from `VoiceSourceProfile`.
- Added compact Speech Diagnostics dock controls for visible and advanced voice-box fields.
- Added Reset Voice Box behavior.
- Added character-profile preset mappings for Neutral, Child, Adult Narrator, Elder, Bright Feminine, Deep Masculine, Breathy, Raspy, and Robot.
- Replaced raw SVG diagnostics text with readable metrics.
- Added Anatomical SVG renderer caching for `VocalTractCanvas`.
- Improved side-cutaway larynx/voice-box visualization.
- Extended generic animation JSON with speech-organ frames, voice-box frames, profiles, render mode, phoneme sequence, and timing frames.

## Non-destructive rules

Voice-box controls map into render copies and diagnostics. They do not mutate editable phoneme data or saved articulation-chain format. Clip Crossfade remains the stable default, and Continuous Mouth Motion remains opt-in.

## UI controls

Basic visible controls:

- `vocal_fold_tension`
- `glottal_closure`
- `breathiness`
- `rasp`
- `age_looseness`

Advanced collapsed controls:

- `vocal_fold_length`
- `vocal_fold_thickness`
- `vocal_fold_mass`
- `vocal_fold_symmetry`
- `glottal_leak`
- `jitter`
- `shimmer`
- `vocal_damage`
- `larynx_height`
- `vocal_tract_length`
- `resonance_depth`

## Future work

Future tasks can deepen formant/resonance DSP, singing, and animation exports. This task intentionally avoids ML voice cloning, Blender-specific code, large dependencies, and broad audio lifecycle changes.
