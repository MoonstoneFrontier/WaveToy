# WaveToy UI Layout Plan

## Current focus: Articulation Timeline

The Articulation Timeline workspace keeps the Task 094 top-level pages:

- **Timeline**
- **Render**
- **Inspector**
- **Profiles**

The **Timeline** page has its own focused internal subtabs:

- **Chain** for Chain Builder actions, chain cards/source actions, compact Speech Assets, and the collapsible CV / VC Library.
- **Timing / Performance** for Musical Timing + Singing Preview, Visual Speech Timeline controls, the `ArticulationTimelineCanvas` scroll area, selected-phoneme controls, scrub/playhead status, boundary curve controls, and envelope/formant canvases. A visible Chain-page shortcut says “Tempo / Singing Preview moved to Timeline → Timing.” so the old performance controls remain discoverable without restoring the crowded Performance tab.
- **Motion** for Motion Summary, fit-to-view Motion Timeline, fit-to-view Viseme Track, Word Motion Preview, motion transport controls, viseme/animation JSON export, the front/anatomical motion canvas, and the collapsible side-cutaway SVG canvas.

Timing and Motion include compact read-only summaries so users can verify phoneme count, approximate duration, and current render mode without duplicating the full chain card list. The Motion Summary also reports unique visemes separately from total viseme holds for animation pacing checks. Motion Timeline and Viseme Track active-segment detection uses half-open intervals (`start_ms <= playhead_ms < end_ms`) with an explicit final-endpoint highlight to avoid boundary ambiguity. These Motion lanes are fit-to-view in Task 096; functional horizontal zoom is deferred to Task 098 animation curve visualization. This reduces scrolling by separating chain management, visual timing edits, and anatomical motion preview instead of stacking every workflow on one dense page.

Non-goals for this layout split: no synthesis feature additions, no render default changes, no project schema changes, no asset-format migration, and no duplicate Articulation Inspector panels.

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

## Task 092 Articulation Inspector placement

The Articulation Inspector belongs inside Articulation Timeline → Inspector. It should remain compact and workflow-oriented: waveform, selection statistics, pitch, energy, spectrogram, and save/load areas use internal collapsible sections instead of another giant Build-page stack. This preserves the Task 090 cleanup that keeps Build focused on chain construction and timeline editing.

## Articulation Motion curve inspection

The Motion workflow keeps the compact Task 095/096 layout order: Motion Summary, Motion Timeline, Viseme Track, Motion Curves, then Word Motion Preview/export controls. Motion Curves is fit-to-view and read-only, with compact visibility checkboxes for mouth, lips, tongue height/frontness, nasal opening, closure, voicing, and airflow. The toggles only repaint the curve canvas; they do not render audio, edit chain items, add persistence, or change export schemas. Task 098 should add functional horizontal zoom/curve detail without changing the generic export payloads.

## Task 097a Performance discoverability

The internal Timing tab is labeled **Timing / Performance**. The Chain workflow keeps a visible note and shortcut to the moved tempo/singing controls, while the timing page adds a compact **Performance Timing** header above Musical Timing, BPM, snap, count-in, beat-grid, and Singing Preview controls. Smooth Mouth Transitions, Word Render Mode, Bypass formants, validation, stop tests, and continuous tuning remain in Render → Render Mode Settings; this keeps controls accessible without rebuilding the old crowded Performance tab.
