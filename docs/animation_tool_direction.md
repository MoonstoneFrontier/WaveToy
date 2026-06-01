# Animation Tool Direction

WaveToy's long-term direction is a visual audio, speech, and animation-prep workstation that remains approachable while preserving the current single-file desktop workflow.

## Speech synthesis workstation direction

- Keep Articulation Lab as the hands-on place for phoneme design.
- Continue using the Articulation Timeline for editable chains, speech assets, word rendering, and timing experiments.
- Add voice-font capture only as a consent-first, reviewable workflow; do not imply production voice duplication until recording, analysis, and licensing safeguards exist.

## SVG-based visual audio direction

- Treat waveform SVG export as both visual documentation and a possible interchange format for animation tools.
- Preserve existing waveform and timeline visualization features.
- Future work can expose clip envelopes, fades, crossfades, speech blocks, and provenance metadata as SVG annotations.

## Blender rig export direction

- Export articulation curves and phoneme/viseme blocks in JSON first.
- Add CSV as a simple inspection format.
- Build a Blender add-on later for rig-specific mapping profiles.

## Voice font direction

- Store `VoiceFontProfile` and `VoiceCapturePrompt` metadata.
- Analyze recordings into reviewable feature packets before deriving presets.
- Keep user consent, license, and provenance visible throughout capture and export.

## Web and iPad portability relationship

- Keep workflow concepts portable: prompt queues, manifests, CV/VC libraries, SVG exports, and JSON animation data should not depend on desktop-only APIs.
- Document dependency assumptions rather than adding large dependencies silently.
- Preserve the PySide6 desktop app while designing schemas that a future web/iPad version can reuse.

## Timeline follow-up todos from Task 055

- Editable fade handles.
- Gain handle or inspector field.
- Clip crossfade visualization.
- Waveform SVG export.
- Articulation phonemes as timeline clips.
- Overlap-aware speech rendering.
