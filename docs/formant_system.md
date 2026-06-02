# Formant System

WaveToy keeps the original articulation-only `formants_from_articulation(...)` helper as the compatibility fallback. Task 069 adds resonance-aware interpretation for render-time copies.

## Resonance-aware helper

`formants_from_articulation_with_resonance(...)` computes base F1/F2/F3 from articulation, then applies small resonance biases:

- `vocal_tract_length` adjusts overall scale: longer tracts lower formants, shorter tracts raise them.
- `larynx_height` contributes brightness/darkness.
- `chest_resonance` supports lower, darker bias.
- `head_resonance` supports brighter upper resonance.
- `nasal_coupling` is exposed as metadata and contributes to nasal shaping.
- `formant_scale` and per-band shifts provide future voice-font/singing hooks within clamps.

## Clamps

The helper clamps biased formants to sane animation/render ranges:

| Band | Range |
| --- | --- |
| F1 | 180–1200 Hz |
| F2 | 500–3500 Hz |
| F3 | 1200–5000 Hz |

## Continuous Mouth Motion

Continuous rendering uses resonance-biased formants only when formants are not bypassed. Intensity remains controlled by the existing Formant Intensity setting, and the math applies a local safety reduction for larger resonance scaling rather than switching render modes.
