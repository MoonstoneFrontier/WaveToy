# Continuous Mouth Motion Validation

## Current posture

Continuous Mouth Motion is still experimental and under quality validation. **Clip Crossfade remains the stable default** and should stay available as the reference mode until Continuous is consistently cleaner by ear.

## Required listen tests

Render and compare these chains in all three modes:

- Continuous Mouth Motion with formants ON
- Continuous Mouth Motion with formants bypassed
- Clip Crossfade reference

### Single vowels

- `AH`
- `IY`
- `OO`
- `AA`
- `AE`

### Words / sequences

- `M OO N`
- `B AH D`
- `D AE D`
- `S T AA P`
- `SH IY`
- `TH IH S`

## Bypass-formants diagnostic workflow

1. Render a chain in Continuous with formants ON.
2. Toggle **Bypass formants** and render again.
3. If bypassed pitch is stable but formants ON warbles or sounds phasey, tune formant intensity/shaping.
4. If both modes warble, tune excitation pitch smoothing, source harshness, and voiced transitions.

Bypass formants is equivalent to `continuous_formant_intensity = 0.0`.

## Diagnostic interpretation

- `pitch_error_percent`: high values indicate unstable excitation, poor pitch estimation, or excessive noise in voiced windows.
- `formant_gain_ratio`: should stay near unity. Large ratios suggest pumping or aggressive coloration.
- `formant_input_rms` / `formant_output_rms`: compare dry and shaped frames; output should not jump sharply frame-to-frame.
- `clipped_samples`: non-zero clipping after limiting is a failure unless it is trivially small and inaudible.
- `distortion_status`: `clipping` or `distorted` requires follow-up even if audio is present.
- `burst_peak` / `burst_rms`: confirms stop release audibility. Very low values make stops weak; excessive values make consonants spitty.
- `stop_debug_events`: inspect stop name, closure duration, release start, burst duration, peak/RMS, and voiced overlap.
- `transition_progress`: helps correlate pitch/formant changes to transitions.
- `voiced_gain`: confirms vowels, nasals, liquids, glides, and voiced stops retain source identity.

## Manual review note template

```text
[WaveToy Listen Test]
chain=<symbols> mode=<continuous_on|continuous_bypass|clip_crossfade>
observation=<pitch stable/warble/distortion/burst too weak/etc>
next_action=<formant tuning/excitation tuning/stop tuning/no action>
```

## Future work

- Continue ear-led tuning before making Continuous default.
- Add CV/VC preview after renderer stability improves.
- Export Continuous state for future animation only after timing and diagnostics are reliable.
