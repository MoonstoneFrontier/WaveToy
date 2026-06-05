# Task 094 — Articulation Workspace Refactor

## Top-level Articulation Timeline workspace

Task 094 separated the Articulation Timeline workspace into four top-level workflow pages:

1. **Timeline** — chain, timing, and motion-oriented speech editing.
2. **Render** — word playback, asset creation, export, render mode settings, and render diagnostics.
3. **Inspector** — waveform, formant, vowel-space, and resonance inspection.
4. **Profiles** — character voice profile management plus Voice Box / Resonance access.

Task 095 preserves those labels and keeps Render, Inspector, and Profiles intact.

## Task 095 Timeline refinement

The top-level **Timeline** page now hosts internal subtabs:

- **Chain** — chain building, chain cards/source actions, compact Speech Assets, and CV / VC Library.
- **Timing** — visual speech timeline, selected phoneme controls, musical timing, envelopes, formants, scrub/playhead, and boundary curves.
- **Motion** — word motion preview, anatomical/front motion canvas, side-cutaway SVG canvas, and viseme/animation JSON export.

This is a layout-only density reduction. It does not alter render behavior, schema, direct phoneme controls, Voice Source boundaries, or animation export data formats.
