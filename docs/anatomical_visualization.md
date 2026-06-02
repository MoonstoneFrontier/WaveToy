# Anatomical Visualization

Task 068 keeps Simple visualization available and optional while improving Anatomical SVG mode.

## SVG render cache

`VocalTractCanvas` now keeps a lightweight `QSvgRenderer` cache for Anatomical mode. The cache key includes display mode, SVG view kind, airflow overlay visibility, quantized `SpeechOrganState` values, and the current/next label used in the SVG.

Simple mode remains unaffected and continues to paint directly with Qt.

## Side cutaway refinements

The side-cutaway SVG now includes a clearer larynx/voice-box region, vocal-fold shapes, a glottal opening indicator, and a vibration ring driven by `voiced_gain`. Oral airflow, nasal airflow, and voice particles remain separate overlays.

## Readability goals

The anatomical views continue to emphasize readable lips, teeth, tongue, palate, velum, nasal cavity, oral airflow, nasal airflow, and larynx status for scrubbing and Word Motion playback.
