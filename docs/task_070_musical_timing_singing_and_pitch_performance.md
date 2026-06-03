# Task 070 — Musical Timing, Singing, and Pitch Performance Foundations

Task 070 adds WaveToy's first optional music-aware timing and singing-performance layer while preserving the millisecond-first speech workflow.

## Scope added

- `MusicalTimingSettings` now carries tempo, time signature, snapping, count-in, beat-grid visibility, beat-unit metadata, and bar visibility.
- Visual Speech Timeline can draw beat and bar grid lines when Musical Timing and Show Beat Grid are enabled.
- Duration drags can quantize to the selected musical subdivision when snapping is enabled; transition timing remains millisecond/manual for articulation safety.
- `NoteEvent`, `PitchAutomationPoint`, and `SyllableStressMarker` provide serialization-ready foundations for singing notes, pitch performance, and phrasing emphasis.
- Singing Preview remains default-off and applies note-derived pitch targets primarily to vowels, with partial support for voiced sonorants.
- Animation JSON export now includes musical timing settings, note events, pitch curve, syllable stress markers, beat grid, and a simple tempo map.

## Regression guard

- Millisecond timing remains default when Musical Timing is disabled.
- Clip Crossfade remains the stable default word render mode.
- Continuous Mouth Motion remains opt-in.
- Speech Diagnostics continues to include `tongue_frontness` and now shows readable musical/singing diagnostics.

## Current limitations

- Note events are foundational data. The UI creates only a simple guide note when Singing Preview is enabled and no note events exist.
- MIDI import/export is documented as a roadmap only; no MIDI dependency is added.
- Singing Preview is not a Vocaloid clone and does not replace the existing speech renderer.

## Task 070a safety note

Task 070a narrowed the active behavior: Musical snap applies only to phoneme durations, transitions remain millisecond articulation timing, and pitch automation is a lightweight vowel-anchored preview. Continuous Mouth Motion quality remains the priority.
