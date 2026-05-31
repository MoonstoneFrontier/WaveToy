# Task 028 — Wave Explorer Workspace Recovery and Articulation Audio Corrections

## Toolbar redesign rationale

The Wave Explorer now uses a compact horizontal workspace toolbar directly above the waveform area instead of large stacked launcher buttons around the dashboard. The toolbar keeps the six workspaces available as touch-friendly buttons while returning the side and lower dashboard regions to the waveform viewer.

Toolbar buttons:

- Shape Mix
- Stereo Space
- Tuning Map
- Pitch Toys
- Sound Magic
- Sound Experiment

Selecting a toolbar item still opens the same floating toy panel as before. The active workspace is kept in the existing dashboard workspace state and the selected toolbar button is visibly checked/highlighted.

## Voice model correction

`Voice On` is now treated as a boolean excitation gate. `Voice Strength` remains a continuous `0.0` to `1.0` amplitude control.

Synthesis rule:

- `Voice On = false` → `voiced_gain = 0.0`
- `Voice On = true` → `voiced_gain = voice_strength`

This separates the vocal-cord on/off decision from the continuous loudness of the voiced component. Vowels, nasals, stops, and fricatives all read the same voiced-gain helper so the model stays consistent.

## Fricative model redesign

Fricatives are now built from separate modular sources:

```text
fricative_output = centered_tone + filtered_noise + optional_voiced_component
```

The renderer keeps these components independent so future speech-quality work can adjust them separately:

- `noise_source`: colored/filtered turbulent noise
- `tonal_source`: a frequency-centered tone based on the phoneme pitch
- `voiced_source`: optional vocal-cord buzz gated by `Voice On`
- `articulation_filter`: existing formant and noise-shaping filters
- `final_mix`: family-specific gain balance and output envelope

## Air Pressure behavior

Air Pressure now directly changes the debug mix and the rendered fricative level:

- Low Air Pressure produces a smaller turbulent/noise gain and softer fricatives.
- High Air Pressure produces stronger turbulence and a louder fricative output envelope.

The fricative noise gain uses both turbulent and airflow terms so pressure changes remain obvious while preview looping or regenerating.

## Tonal component behavior

Each fricative receives a centered tonal component derived from `voice_pitch`. The tonal amount depends on the phoneme family/name and the current voice settings.

Examples:

- `S`: mostly noise with a weak tone.
- `Z`: noise plus a stronger voiced/tonal center.
- `SH`: filtered noise with a moderate tonal center.
- `F`: strong air/noise with a weak tonal center.
- `V`: clear tonal center with a noise overlay.

## Debug display

The Articulation Lab status area now shows the current synthesis mix:

- `voiced_gain`
- `noise_gain`
- `tonal_gain`
- `air_pressure`
- `voice_strength`
- `source_mode`

This makes it easier to verify that `Voice On`, `Voice Strength`, and `Air Pressure` are changing synthesis values before listening to the result.

## Future speech synthesis roadmap

The updated model keeps source generation modular. Future coarticulation and speech-quality improvements can independently alter:

1. voiced excitation,
2. centered tonal excitation,
3. turbulent/noise excitation,
4. articulation filtering, and
5. final family-specific mixing.

Useful next steps would include note-aware phoneme pitch routing from the tuning map, time-varying coarticulation curves between chain items, and richer voiced-fricative formant/noise transitions.
