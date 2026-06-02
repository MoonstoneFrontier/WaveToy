# Anatomical Visualization

Task 067 introduces SVG-based anatomical visualization foundations while preserving the existing simple vocal-tract drawing.

## Display modes

- **Simple** keeps the existing cartoon/symbolic visualizer.
- **Anatomical** uses generated SVG driven by `SpeechOrganState`.

## Anatomical mouth view

The frontal anatomical mouth SVG includes:

- upper lip and lower lip
- upper teeth and lower teeth
- tongue
- palate
- oral cavity

It is resolution-independent SVG and updates from the same interpolated state used by timeline scrubbing and word-motion playback.

## Vocal tract side-cutaway

The optional side-cutaway panel is collapsed by default. It shows:

- lips, teeth, tongue, and palate
- velum and nasal cavity
- pharynx and larynx
- oral, nasal, and voicing airflow particles

## Airflow model

SVG particle overlays use consistent colors:

- oral airflow: blue
- nasal airflow: green
- stop burst: orange
- frication: purple
- voicing: red

The overlay is lightweight and can be disabled from the Articulation Lab display controls.

## Voice-source model

Voice-source visualization is separate from articulation. The read-only diagnostics panel reports voice-source-style values including vocal fold tension, thickness, glottal closure, breathiness, rasp, jitter, and shimmer without changing audio synthesis.
