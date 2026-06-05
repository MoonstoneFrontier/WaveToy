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

## Future TODO: Music Theory / Harmony

Harmony Workbench, pitch selection, interval education, and harmonic analysis are now dense enough to deserve their own layout follow-up. A future task may split those controls into a **Music Theory / Harmony** area with separate pages for note picking, scale/chord analysis, interval education, and export.
