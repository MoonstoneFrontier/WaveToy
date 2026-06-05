# WaveToy UI Layout Plan

## Current focus: Articulation Timeline

The Articulation Timeline tab is organized as a workflow hub with internal subtabs:

- **Build** for phoneme chain construction and compact saved/list pickers.
- **Visual Timeline** for the timeline graphic, transport/playhead controls, and selected-item inspector.
- **Render / Export** for word render mode, `Play Word`, `Create Word`, `Export Word`, and render status.
- **Performance** for automation-adjacent previews, voice profile, and musical timing controls.
- **Advanced** for diagnostics, debug controls, validation details, and verbose status panels.

## Picker/sidebar width policy

List and saved-asset pickers should not consume the full page width unless the picker is the primary content. Articulation Timeline picker sidebars use:

- minimum: `220` px;
- preferred: `300` px;
- maximum: `380` px.

Active editors, graphics, and inspectors should receive more stretch than picker sidebars.

## Scrolling guidance

- Use internal workflow pages before adding more stacked cards to a single scroll area.
- Keep primary actions at the top of their workflow page.
- Move debug/experimental/status-heavy content to Advanced pages or collapsed sections.
- Prefer horizontal split panels for picker + editor layouts.
- Avoid pixel-perfect geometry dependencies in tests; prefer smoke tests and helper-policy checks.

## Music Theory / Harmony

The note-wheel Harmony Workbench now uses a **Music Theory** workflow area with internal subtabs:

- **Notes** for the wheel, note picker, spelling controls, coloration, and selected-note mood.
- **Intervals** for interval preview, interval mood, and teaching summaries.
- **Scales** for key root, scale construction, highlighting, descriptors, and mode/degree expansion space.
- **Chords** for chord root, chord construction, highlighting, quality, and inversion-ready summaries.
- **Harmony Analysis** for roman numerals, harmonic functions, contextual scale/chord relationships, and descriptor reporting.
- **Export** for Harmony JSON import/export and future progression export actions.

Music Theory picker/list/library panels use the same compact sidebar policy: minimum `220` px, preferred `300` px, maximum `380` px. Keep primary editing actions near the top of each subtab and move educational detail below core controls. Future progression, cadence, songwriting, composition, harmonic movement, and ear-training features should prefer adding to these workflow pages instead of returning to a single giant vertical page.
