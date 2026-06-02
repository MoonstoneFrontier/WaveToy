# Speech Organ State

`SpeechOrganState` is the render-only anatomical state that all new speech visualization and animation layers consume. It is derived from the existing `ArticulationPhoneme` sliders and does **not** change saved articulation chains.

## Fields

All fields are normalized `0.0` to `1.0` except `voice_pitch`, which remains Hz:

- `jaw_open`, `lip_open`, `lip_rounding`, `lip_spread`
- `tongue_tip_height`, `tongue_blade_height`, `tongue_body_height`, `tongue_back_height`
- `tongue_frontness`, `tongue_retraction`
- `velum_open`, `velum_closed`, `nasal_airflow`
- `glottal_open`, `glottal_closure`, `voiced_gain`, `airflow`
- `closure_strength`, `burst_strength`, `voice_pitch`

## Mapping from phoneme sliders to anatomy

- `mouth_open` maps to `jaw_open` and contributes to `lip_open`.
- `lip_rounding` maps directly to `lip_rounding`; `lip_spread` is the inverse rounding with a front-tongue bias.
- `tongue_height` maps to the tongue tip, blade, body, and back heights.
- `tongue_frontness` maps directly to `tongue_frontness`; `tongue_retraction` is its inverse.
- `nasal_open` maps to `velum_open`; `velum_closed` is its inverse.
- `air_pressure` maps to `airflow` and combines with `nasal_open` for `nasal_airflow`.
- `closure` maps to `closure_strength`.
- `burst_strength` maps directly to `burst_strength`.
- `voiced` and `voice_strength` map to `voiced_gain`, `glottal_closure`, and `glottal_open`.
- `voice_pitch` maps directly to `voice_pitch`.

## Compatibility guarantees

- Existing phoneme presets and articulation-chain JSON remain the persisted source data.
- `SpeechOrganState` is generated at render/export time.
- Viseme generation now has a state-first path with a phoneme compatibility wrapper.
