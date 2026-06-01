# Task 055 — Timeline Audio Foundation

## Implementation notes

- `TimelineClip` now separates immutable source duration from non-destructive edit duration by keeping full-source sample length plus trim, playback-rate, gain, and fade metadata.
- Timeline block width continues to be derived from the rendered edit duration (`source_visible_duration / playback_rate`) so trim and stretch updates repaint at the same size they will render.
- Pitch-preserving stretch remains the default render path and uses the existing NumPy phase-vocoder path instead of naive resampling; legacy speed resampling is only retained as an explicit compatibility escape hatch.
- Render caching is scoped to source identity, trim, stretch, pitch-preserve state, quality, and articulation metadata so stretched clips are reused until edit-relevant inputs change.
- Timeline waveform drawing now goes through a renderer abstraction (`TimelineWaveformRenderer`) with raster and future-SVG adapter classes. The raster renderer uses a per-clip cached preview peak list.
- Clip painting now exposes visible trim handles, fade handles/regions, and stretch diamonds so clips communicate DAW-style edge affordances even before every handle has a dedicated edit mode.
- Clip audio render applies non-destructive gain and fade-in/fade-out envelopes after trim/stretch, preserving the source audio array.

## Code review notes

- The change intentionally stays in `wave_toy.py` because this phase is incremental and the project still treats that file as the primary application entry point.
- Existing timeline drag behavior already follows button-held drag semantics: press selects, motion does not edit until the left button is held past the drag threshold, and release commits or clears state. This task keeps that interaction path intact.
- The current time stretch is a lightweight NumPy phase vocoder. It preserves broad pitch/phoneme identity better than resampling but is not yet a production elastique/Rubber Band equivalent.
- Fade handles are currently visual foundations; editable fade dragging can be added as a focused follow-up without disturbing trim/stretch/move behavior.

## Architecture notes

- First extraction candidates:
  1. `TimelineWaveformRenderer`, `RasterTimelineWaveformRenderer`, and `SvgTimelineWaveformRenderer` into a timeline rendering module.
  2. `TimelineCanvas` clip block painting into a timeline renderer/controller split.
  3. Speech bin and speech cache helpers into a speech asset manager.
  4. Articulation chain/timing widgets into an articulation timeline module.
- The new waveform renderer abstraction creates a seam for generating SVG waveform paths from the same cached peak data used by the raster painter.
- Clip metadata now models audio editor concepts (`source_duration`, trims, gain, fades, playback rate) without embedding raw source audio in exported arrangement sidecars.

## Migration plan

1. Keep reading older arrangement sidecars by defaulting missing `gain`, `fade_in`, and `fade_out` metadata to neutral values.
2. Add dedicated fade-handle edit operations with cache invalidation limited to preview/render envelopes.
3. Add an articulation-clip model that maps each phoneme to clip start, duration, overlap, and crossfade data while preserving the existing chain save format.
4. Move waveform rendering into `wavetoy/timeline/waveform_renderer.py` once the single-file app has one more stable milestone.
5. Add optional higher-quality pitch-preserving backends behind dependency checks rather than replacing the NumPy fallback.
