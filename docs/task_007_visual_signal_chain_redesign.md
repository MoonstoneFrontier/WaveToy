# Task 007: Visual Signal Chain Redesign

## Design decisions

- Kept the Task 006 two-column application structure and far-right **Wave Overview** placement.
- Reworked each wave card into a compact left-to-right signal path: **Shape ➜ Envelope ➜ Stereo ➜ Output**.
- Kept controls beside the visualization they affect instead of returning to a wide table of detached sliders.
- Reduced reliance on decorative wave icons: the primary shape cue is now an actual oscillator sample strip.
- Added a short explanatory note to the global stereo section so users can distinguish per-wave placement from whole-mix movement.

## Preview architecture

- Wave-card previews use lightweight cached arrays produced by `build_wave_preview_samples()`.
- Preview sample count is clamped to 120–240 samples, with the default remaining at 160 samples.
- The preview builder uses the same oscillator helper as the audio engine for sine, triangle, sawtooth, and square shapes.
- Preview updates are triggered from existing slider-change paths and scheduled generation hooks.
- Paint events draw cached arrays only; they do not run full audio rendering, Paulstretch processing, file export, playback, or cancellation logic.

## Signal-chain rationale

Each card now communicates a sound-design path:

1. **Shape** shows the raw oscillator identity.
2. **Envelope** shows start loudness, end loudness, and how quickly the loudness reaches the end value.
3. **Stereo** shows the ingredient's left/right balance, spread, and dance movement.
4. **Output** shows the resulting left/right waveform pair after that ingredient's envelope and stereo settings.

This makes a card readable before playback: users can see what the ingredient is, how it changes over time, where it sits, and what reaches each ear.

## What is accurate

- Shape previews use the same waveform math as generated audio.
- Envelope previews use the same dB-to-gain conversion and partial curve logic used by the audio render path.
- Output previews use the same equal-power panning helper used by the audio render path.
- Per-wave preview changes stay tied to the existing per-wave start, end, time, place, spread, and dance sliders.

## What remains approximate

- Preview strips are intentionally short visual summaries, not full-resolution rendered audio.
- The stereo field preview summarizes left/right energy and pan movement rather than displaying the entire final mix.
- Whole-mix stereo, global loudness, pitch motion, normalization, and optional Paulstretch can still change the final Wave Overview after generation.
- Dance movement in the preview is illustrative and uses the existing preview animation timing rather than a playback-synchronized playhead.

## Future integration points

- The cached preview arrays can feed a future playback controller or playhead without moving synthesis into paint events.
- The Envelope and Stereo preview widgets are isolated enough to be updated by a future worker-thread render result.
- The Wave Overview remains compact on the far right so a future scrolling waveform or playhead can be added there without reopening the center-layout issue.
- No playback controller, worker thread, cancellation system, playhead, or waveform scrolling was implemented in this task.
