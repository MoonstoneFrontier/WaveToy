# Anatomical Visualization

Task 068 keeps Simple visualization available and optional while improving Anatomical SVG mode.

## SVG render cache

`VocalTractCanvas` now keeps a lightweight `QSvgRenderer` cache for Anatomical mode. The cache key includes display mode, SVG view kind, airflow overlay visibility, quantized `SpeechOrganState` values, and the current/next label used in the SVG.

Simple mode remains unaffected and continues to paint directly with Qt.

## Side cutaway refinements

The side-cutaway SVG now includes a clearer larynx/voice-box region, vocal-fold shapes, a glottal opening indicator, and a vibration ring driven by `voiced_gain`. Oral airflow, nasal airflow, and voice particles remain separate overlays.

## Readability goals

The anatomical views continue to emphasize readable lips, teeth, tongue, palate, velum, nasal cavity, oral airflow, nasal airflow, and larynx status for scrubbing and Word Motion playback.

## Task 069 resonance overlay

The anatomical side cutaway now accepts an optional `ResonanceTractState`. The overlay adds subtle, low-opacity indicators for:

- oral resonance chamber
- pharyngeal resonance chamber
- nasal coupling path
- chest/head resonance indicators
- labeled F1/F2/F3 traces

The existing airflow overlay remains available, and the resonance overlay is intentionally understated to avoid visual noise during scrubbing or word motion.
