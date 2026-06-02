# VoiceBoxState

Task 068 adds `VoiceBoxState` as a non-destructive, normalized larynx layer upstream of `SpeechOrganState`.

## Field ranges

All fields are normalized `0.0` to `1.0`. Voice pitch in Hz is computed downstream and is not stored as a normalized field.

| Field | Purpose |
| --- | --- |
| `vocal_fold_length` | Longer folds bias pitch lower; shorter folds bias pitch higher. |
| `vocal_fold_thickness` | Thicker folds bias pitch/resonance lower. |
| `vocal_fold_tension` | Higher tension biases pitch higher. |
| `vocal_fold_mass` | More mass biases pitch lower. |
| `vocal_fold_symmetry` | Reserved for future clean/irregular fold behavior. |
| `glottal_closure` | Maps into `SpeechOrganState.glottal_closure`. |
| `glottal_leak` | Opens the glottis and slightly raises airflow in render copies. |
| `breathiness` | Adds glottal openness/airflow and safe noise-color bias. |
| `rasp` | Diagnostics and safe noise-color bias only. |
| `jitter` | Diagnostics only for now. |
| `shimmer` | Diagnostics only for now. |
| `vocal_damage` | Diagnostics only; no ML voice cloning or medical modeling. |
| `age_looseness` | Lowers pitch bias slightly and supports character presets. |
| `larynx_height` | Future formant-bias metadata. |
| `vocal_tract_length` | Future formant-bias metadata. |
| `resonance_depth` | Future formant-bias metadata. |

## VoiceBoxState vs VoiceSourceProfile

`VoiceSourceProfile` remains the legacy/source-profile description used by existing WaveToy controls. `VoiceBoxState` is the render-copy larynx snapshot derived from that profile and then optionally adjusted by compact controls or character presets.

Direct phoneme articulation remains separate and authoritative: mouth, tongue, lips, velum, closure, and burst controls are not overwritten in saved chains.

## Mapping to SpeechOrganState

The current low-risk mapping is intentionally small:

- `glottal_closure` blends into `SpeechOrganState.glottal_closure`.
- `glottal_leak` and `breathiness` raise `glottal_open` and airflow in render copies.
- fold tension/length/thickness/mass produce a small pitch bias.
- `larynx_height`, `vocal_tract_length`, and `resonance_depth` are exported as future formant metadata.
- rasp/jitter/shimmer/vocal damage appear in diagnostics but avoid broad DSP changes.

## Serialization

`VoiceBoxState.to_json_dict()` emits a human-readable normalized dict. `VoiceBoxState.from_json_dict()` clamps incoming values and fills missing fields with neutral defaults.
