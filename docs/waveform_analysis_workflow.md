# Waveform Analysis Workflow

WaveToy's waveform diagnostics view remains focused on render inspection while gaining a lightweight performance overlay hook.

## Performance overlay API

The diagnostics canvas can receive:

- `performance_points`: JSON-safe marker dictionaries for the selected performance track;
- `active_track`: the selected lane name;
- `playhead_ms`: the current performance playhead.

This allows selected automation points to appear over the waveform without rewriting the waveform editor.

## Current scope

The overlay is intentionally simple: it shows selected-track markers and the playhead. It does not yet provide waveform-side automation editing, Bezier handles, or DAW-style region tools. Those belong in a future Task 077-style waveform integration pass.
