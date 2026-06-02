# ResonanceTractState

Task 069 adds `ResonanceTractState` as a render-only layer between `VoiceBoxState` and final mouth/nose articulation. It colors perceived identity and formant behavior without writing back into editable phoneme presets or saved articulation-chain items.

## Model fields

Normalized `0.0`–`1.0` fields:

- `oral_cavity_length`
- `oral_cavity_width`
- `oral_cavity_height`
- `pharyngeal_volume`
- `pharyngeal_tension`
- `nasal_coupling`
- `chest_resonance`
- `head_resonance`
- `larynx_height`
- `vocal_tract_length`
- `resonance_depth`
- `brightness`
- `darkness`

Special formant fields:

- `formant_scale`: clamped to `0.5`–`1.5`.
- `formant_shift_f1`, `formant_shift_f2`, `formant_shift_f3`: clamped to `-1.0`–`1.0`.

## Derivation

Defaults are derived from `VoiceBoxState` and a render-copy `SpeechOrganState`:

1. `VoiceBoxState` supplies larynx height, vocal tract length, resonance depth, fold tension, age looseness, and source-body hints.
2. `SpeechOrganState` supplies current jaw/lip/tongue/velum posture.
3. The resulting `ResonanceTractState` is clamped and serialized separately from phoneme data.

## Render order

```text
Voice Box / source controls
        ↓
VoiceBoxState
        ↓
ResonanceTractState
        ↓
SpeechOrganState + ArticulationPhoneme
        ↓
formant interpretation, diagnostics, visualization, animation export
```

This keeps resonance useful for identity, character profiles, future singing, and voice-font workflows while preserving direct phoneme controls.
