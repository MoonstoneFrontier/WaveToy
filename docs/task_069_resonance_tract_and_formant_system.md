# Task 069 — Resonance Tract Model and Formant System Foundations

Task 069 introduces a distinct resonance layer downstream of Voice Box source settings and upstream of final articulation/formant interpretation.

## Implemented foundations

- Added `ResonanceTractState` with serialization, clamping, neutral defaults, and derived defaults from `VoiceBoxState` plus `SpeechOrganState`.
- Added resonance-aware formant calculation while preserving `formants_from_articulation(...)` as the compatibility fallback.
- Added compact Resonance Tract Controls in the Speech Diagnostics dock below Voice Box controls.
- Extended character presets so presets can update both voice-box and resonance defaults while leaving direct controls editable.
- Added a subtle resonance overlay to the anatomical side cutaway.
- Routed resonance-aware F1/F2/F3 into Continuous Mouth Motion formant shaping while respecting Bypass Formants and formant intensity.
- Extended viseme and animation JSON with resonance state frames, formant frames, resonance profile, and resonance curves.

## Compatibility rules

- Saved phoneme and articulation-chain data is not mutated by resonance controls.
- Clip Crossfade remains the default render mode.
- Continuous Mouth Motion is not made default.
- Blender export remains a future add-on; generic JSON remains human-readable.
- No ML voice cloning or new large dependencies were added.

## Safe formant ranges

- F1: `180`–`1200` Hz
- F2: `500`–`3500` Hz
- F3: `1200`–`5000` Hz

The resonance bias is deliberately conservative to avoid unstable jumps or pitch warble.
