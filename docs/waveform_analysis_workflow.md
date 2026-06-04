# Waveform Analysis Workflow

The Articulation waveform diagnostics view shows the latest word render and lightweight overlays for render debugging.

## Performance overlay sync

The waveform overlay uses the currently selected Performance Timeline track. It displays that track's points and follows the Performance Timeline playhead.

The overlay refreshes when:

- the selected timeline track changes,
- a point is added, removed, edited, or dragged,
- the Performance Timeline playhead changes,
- a word render refreshes.

The waveform editor is not rewritten by this workflow; the overlay remains a read-only diagnostic view.

## Automation diagnostics

After a word render, Speech Diagnostics reports active automation targets plus min/max values for `accentuation_db` and `pitch_bias_cents`. The selected track's sampled value at the playhead is shown for scrubbing and review.

## Render notes

`accentuation_db` changes should be audible as non-destructive gain automation on the render copy. `pitch_bias_cents` is deliberately conservative and avoids obvious noisy regions where possible; if a phrase contains only unvoiced/noisy material, the pitch-bias mask may leave it unchanged.

## Task 079 engine-sourced overlay data

The waveform diagnostics overlay now follows the Performance Timeline engine's selected runtime data and playhead state. This keeps the waveform overlay read-only while avoiding duplicate playhead and sampled-value logic in the window.

Diagnostics shown alongside the waveform should be treated as engine-owned runtime diagnostics rather than independently recalculated waveform-editor state.

## Task 080 engine-owned overlay state

The waveform overlay should read Performance Timeline selection and playhead from `PerformanceTimelineEngine`. `WaveToyWindow` compatibility mirrors may still be present for older UI plumbing, but the overlay state follows the engine so the canvas, Performance Timeline status, and Speech Diagnostics agree during point selection and scrubbing.

Runtime callbacks (`on_playhead_changed`, `on_selection_changed`, `on_tracks_changed`, and `on_diagnostics_changed`) provide a lightweight refresh seam without adding a new dependency or event bus.
