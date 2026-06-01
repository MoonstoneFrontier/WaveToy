# Speech Workstation Roadmap

## Current foundation

WaveToy's Articulation Timeline is moving from a chain-card editor toward a speech workstation. The current foundation keeps the phoneme track visible while introducing a shared track-container concept for future lanes.

Visible now:

- Phoneme track with draggable phoneme blocks.
- Transition regions between adjacent phonemes.
- Playhead scrubbing.
- Zoom buttons, fit-to-word, zoom-to-selection, and Ctrl/Shift + wheel zoom.
- Compact selected-phoneme controls for basic timing and accentuation edits.

Reserved future lanes:

- Accentuation automation.
- Airflow automation.
- Voicing automation.
- Pitch lane.
- Formant lanes.
- Viseme lane.

## Multitrack direction

The next architecture step is to extract shared timeline scale/state so all lanes use the same milliseconds-to-pixels mapping, playhead position, selection state, and zoom navigation. The phoneme track should remain the authoritative structural lane until automation editing is explicitly implemented.

Do not implement yet:

- Automation editing.
- Pitch-lane editing.
- Formant-lane editing.
- SVG/web/canvas replacement.

## Direct manipulation roadmap

Near-term improvements:

- More precise insertion markers between every block boundary.
- Optional snap-to-grid and snap-to-phoneme-boundary behavior.
- Keyboard nudging for duration and transition durations.
- Inline numeric handles for selected block duration and transition regions.

## Continuous Mouth Motion integration

Continuous Mouth Motion should remain compatible with timeline editing:

- Duration edits alter the hold segment length.
- Transition edits alter interpolation segment length and curve timing.
- Reordering rebuilds the chain before rendering.
- Accentuation should continue to shape effective gain and remain visible in diagnostics.
- Dirty-state invalidation must clear render signatures whenever timeline edits change phoneme order, duration, transition, accentuation, or phoneme parameter state.

## SVG migration notes

SVG migration should be incremental and documentation-led before implementation:

1. Identify rendering primitives in `ArticulationTimelineCanvas`, `ArticulationTrackCanvas`, and waveform renderers.
2. Model primitives as semantic timeline elements: block, transition, playhead, ruler tick, selection outline, accent marker, waveform path.
3. Keep PySide interaction semantics stable while experimenting with exportable SVG metadata.
4. Avoid replacing the native editor until editing, playback, diagnostics, and render-cache behavior are covered by tests or repeatable manual checks.
