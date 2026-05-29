# Task 016: Audio Timeline Clip Editor

## Rebase note

The timeline editor has been rebased onto the Task 015 tab-oriented Wave Explorer architecture. The timeline is now added as a fourth top-level tab without replacing the existing Play, Wave Explorer, or Classic Editor surfaces.

Final tab order:

1. **🎛 Play**
2. **🌊 Wave Explorer**
3. **🎬 Timeline**
4. **🧰 Classic Editor**

The Wave Explorer dashboard, visual panel buttons, no-wheel controls, recipe save/load behavior, per-wave mute/solo and pitch behavior, tuning controls, and Paulstretch controls remain owned by the existing WaveToy UI. The timeline is integrated as an additional editor tab that requests the current generated audio through `WaveToyWindow` helper callbacks.

## Overview

WaveToy includes a **🎬 Timeline** tab for arranging generated sounds as layered clips across multiple storyboard-like lanes. This first version is intentionally lightweight and session-focused: clips keep their playable audio arrays in memory while the app is open, and timeline export writes rendered audio plus lightweight arrangement metadata.

## Timeline data model

The timeline classes live in `wave_toy.py` to match the current single-file app structure.

### `TimelineClip`

A clip represents one generated WaveToy sound placed on the timeline.

Fields:

- `id`: unique UUID string.
- `name`: internal/user-facing clip label.
- `audio_data`: in-memory NumPy audio array used for playback and mixdown.
- `sample_rate`: source sample rate.
- `start_time_seconds`: clip start on the arrangement timeline.
- `duration_seconds`: clip duration.
- `track_index`: destination lane row.
- `gain`: per-clip gain multiplier.
- `muted`: per-clip mute flag.
- `color`: block color used by the timeline canvas.
- `source_recipe_snapshot`: recipe/settings snapshot captured when the clip is created.
- `waveform_peaks`: small cached peak list for fast clip waveform thumbnails.

### `TimelineTrack`

A track is presented to users as a storyboard lane.

Default lanes:

- `🎵 Melody Lane`
- `🥁 Rhythm Lane`
- `🌌 Atmosphere Lane`
- `✨ Effects Lane`

Fields:

- `index`: lane index.
- `name`: user-facing lane name.
- `muted`: excludes the lane from mixdown.
- `soloed`: if any lane is soloed, only soloed lanes are mixed.
- `gain`: per-lane gain multiplier.

### `TimelineArrangement`

An arrangement owns the session timeline state.

Fields:

- `clips`: ordered list of `TimelineClip` objects.
- `tracks`: list of `TimelineTrack` objects; four toy lanes are created by default.
- `total_duration_seconds`: dynamic timeline duration with trailing space after the last clip.
- `bpm_optional_future`: reserved for future beat-grid work.
- `sample_rate`: mixdown sample rate.

## Implemented clip and lane behavior

The **🎬 Timeline** tab contains:

- A top transport row with **Play Story**, **Stop**, **Mix Story**, **Drop Current Sound**, **Add Lane**, and zoom buttons.
- Left lane headers with per-lane mute and solo toggles.
- A custom `TimelineCanvas` that draws:
  - a horizontal second ruler,
  - multiple horizontal lanes,
  - colored rounded sound/story blocks,
  - cached waveform peak previews,
  - a magenta playhead line.
- A bottom inspector for the selected sound block.

Implemented interactions:

- **Drop Current Sound** copies the current generated audio into an in-memory clip.
- New clips are placed at the current playhead on the selected clip's lane, or the first lane when nothing is selected.
- Click a clip to select it.
- Drag a clip left/right to change its start time.
- Drag a clip up/down to move it between lanes.
- Use the inspector to adjust selected clip gain.
- Use the inspector to mute the selected sound block.
- Duplicate the selected sound block.
- Delete the selected sound block.
- Add new lanes.
- Mute or solo lanes.
- Zoom the timeline horizontally.

## Playback and mixing method

Arrangement playback uses `sounddevice` when available, matching WaveToy's existing optional playback approach and without removing the existing main playback code.

Mixing steps:

1. The arrangement allocates a stereo float32 buffer large enough for all clips plus trailing timeline space.
2. Each unmuted clip on an audible lane is copied into the buffer at `start_time_seconds`.
3. Overlapping clips are layered by summing samples.
4. Clip gain and lane gain are applied during summing.
5. Muted lanes are skipped.
6. If any lane is soloed, only soloed lanes are included.
7. The final mix is peak-normalized only when needed to keep output below clipping.

The playhead is advanced with a Qt timer during arrangement playback, and **Stop** calls `sounddevice.stop()` when `sounddevice` is installed.

## Render and export behavior

**Mix Story** creates the current arrangement mix in memory and stores it as the timeline editor's last rendered mix.

**Export Last Mix** renders the arrangement, then uses WaveToy's existing `save_audio_file` path for WAV/OGG/MP3/FLAC output. A sidecar `.wave-toy-arrangement.json` file is also written next to the exported mix.

The sidecar metadata includes lane metadata, clip metadata, timing, gain/mute state, colors, and recipe snapshots. It intentionally does **not** embed raw clip audio arrays, avoiding giant JSON files.

## Session-only and future-regenerable behavior

Implemented now:

- Clip audio arrays remain in memory for the current app session.
- Recipe snapshots are preserved in exported metadata.
- Raw audio arrays are not embedded in JSON.

Future versions should use `source_recipe_snapshot` to regenerate clips from recipes and/or relink exported audio files for full arrangement reloads. This first version does not claim full persistent session reload.

## Deferred work

Not implemented in this first version:

- Crossfades.
- Clip splitting.
- Clip time-stretching.
- Beat grid or BPM snapping.
- Undo/redo.
- External audio import.
- Automation lanes.
- Persistent full session reload with audio relinking or recipe regeneration.
- Lane renaming UI.

## Known limitations

- Timeline clips are in-memory for the current app session.
- Arrangement playback requires the optional `sounddevice` package and working native audio support.
- The metadata sidecar records recipe snapshots and timeline placement, but it cannot fully reconstruct arbitrary clip audio until future recipe regeneration or audio relinking is implemented.
- The canvas waveform previews use cached peak thumbnails rather than full waveform rendering for performance.
