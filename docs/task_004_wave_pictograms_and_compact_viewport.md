# Task 004: Wave Pictograms and Compact Right-Side Viewport

## Summary

Task 004 adds compact waveform pictograms beside the existing slider controls while keeping `wave_toy.py` as the single active desktop entry point. The implementation is intentionally lightweight: the previews are mathematical drawings of sine, triangle, sawtooth, and square waves, not rendered audio buffers.

## Mini preview widget design

`MiniWavePreview` is a small `QWidget` that draws one waveform inside a rounded, playful preview box using `QPainter`. It supports:

- `set_wave_type(wave_type)` for sine, triangle, sawtooth, and square shapes.
- `set_amplitude(value)` so louder wave settings draw taller lines.
- `set_stereo(left_gain, right_gain)` for left/right ear emphasis.
- `set_motion(active)` for timer-driven scrolling.

The preview uses inexpensive math in `paintEvent` and does not perform audio synthesis or inspect generated sample buffers.

## Where previews were added

- The main **Mix the Wave Shapes** section now includes a small `Look` preview column for each wave row.
- The **Stereo Space Per Wave** section now includes compact left/right mini preview boxes for every wave, labeled `L` and `R`.
- The global `WaveCanvas` overview remains present, but it is smaller and placed at the top of the far-right column so it no longer dominates the central layout.

## Preview animation

Preview scrolling is time-based. Each `MiniWavePreview` owns a short `QTimer` that advances a phase offset and repaints the pictogram. The window starts preview motion when:

- the user presses **Make Sound**, or
- live loop mode is enabled.

One-shot playback stops the preview timer after the generated clip duration. Live loop keeps the previews moving until live loop/stop is disabled.

## Per-ear stereo estimate

The stereo mini previews estimate the ear balance from the existing per-wave pan slider, the global stereo width slider, and the per-wave width slider. The effective pan is converted with the same equal-power left/right gain idea used by audio generation, so the left and right preview boxes visibly differ as a wave is moved toward either ear.

Per-wave ear dance is represented as a small opposing left/right visual gain sway while the previews animate. This is a pictorial hint rather than a sample-accurate display.

## Not sample-accurate yet

This task does **not** add sample-accurate playback position tracking, sounddevice buffer synchronization, worker-thread rendering, or a full playback controller. The mini waveform scrolling is intentionally time-based only.

## Recommended next task

Add a lightweight playback state/controller layer that can expose a shared playhead phase to the main `WaveCanvas` and all mini previews. That would make future visualization work more consistent without changing synthesis behavior.
