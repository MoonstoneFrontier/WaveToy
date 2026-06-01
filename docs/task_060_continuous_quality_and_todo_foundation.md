# Task 060 — Continuous Quality and TODO Foundations

## Status

Continuous Mouth Motion remains under quality validation. This task keeps **Clip Crossfade** as the stable default render mode while making Continuous easier to tune and diagnose.

## Renderer changes

- Added `continuous_formant_intensity` with a default of `0.45` and a UI control from `0.00` to `1.00`.
- Treating **Bypass formants** as intensity `0.0` so excitation pitch can be isolated from tract coloration.
- Reduced formant shaping to small, clipped spectral coloration with frame RMS ratio limiting to avoid pumping and pitch-moving spectral boosts.
- Added `continuous_pitch_smoothing_ms` with a default of `20 ms` and a UI range of `0–120 ms`.
- Kept oscillator phase continuous while smoothing voiced pitch targets between phonemes.
- Kept stop bursts injected after transition-only smoothing.

## Diagnostics added

Continuous debug output now includes:

- `formant_intensity`
- `formant_input_rms`
- `formant_output_rms`
- `formant_gain_ratio`
- `continuous_pitch_smoothing_ms`
- `intended_pitch_hz`
- `measured_pitch_estimate_hz`
- `pitch_error_percent`
- `active_phoneme`
- `transition_progress`
- `voiced_gain`
- per-stop `stop_debug_events` with closure, release, burst peak/RMS, and voicing-overlap fields

## Validation workflow

The validation button renders vowels and short words/sequences without destroying the user's current chain, render mode, bypass-formants state, or cached render audio. Results are shown in aligned monospace-style text columns:

`chain`, `duration`, `peak`, `pitch err`, `clipped`, `burst`, `voiced`, `noise`, `status`, and `notes`.

## Listen-test note

The automated environment can render and report diagnostics, but it cannot confirm subjective audio quality by ear. Treat PASS diagnostics as a screening result only. Manual ear checks should compare:

1. Continuous with formants enabled.
2. Continuous with Bypass formants enabled.
3. Clip Crossfade reference.

Do not mark Continuous fully solved until those manual checks sound clean.

## Adjacent foundations

- CV/VC library gained compact search/filter controls and a low-risk “Load Combination to Chain” action.
- Voice-font work is limited to recording-prompt documentation.
- Viseme work is limited to future-compatible mapping documentation.
- Export/provenance work is limited to package-manifest documentation.

## Future work

- More ear-led tuning for stop consonants, especially D versus TS-like releases.
- Audio preview for CV/VC combinations.
- JSON export for animation/viseme timing once Continuous state is stable.
- Voice-font recording UI only after prompt/provenance requirements are settled.
