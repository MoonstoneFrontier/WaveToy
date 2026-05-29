# Task 017: Timeline Audio Palette Import and Playback Fallback

## Audio Palette behavior

The Timeline tab now includes a left-side **🎧 Audio Palette** panel. Use the large **📥 Import Sounds** button to select one or more audio files. Successfully imported sounds appear as large, touch-friendly cards with:

- a large audio icon,
- the imported file name,
- duration in seconds,
- a compact waveform thumbnail,
- a **➕ Add** button.

Palette sounds are reusable sources. Adding or dragging a card copies the imported audio into a new timeline clip; it does not remove the sound from the palette.

## Supported import formats

- **WAV** is supported with Python's built-in `wave` module.
- **MP3**, **OGG**, and **FLAC** are supported when `ffmpeg` is installed and available on `PATH`.
- Unsupported files, empty files, decode failures, and missing `ffmpeg` for compressed formats are reported with readable warnings and logged with the `[WaveToy Timeline]` prefix.

Imported audio is converted to stereo float audio at WaveToy's internal sample rate so existing timeline render/export behavior remains stable.

## Drag/drop behavior

Palette cards can be dragged onto the timeline canvas:

- the drop x-position determines the new clip start time,
- the drop y-position determines the target lane,
- the target lane is highlighted while dragging over the timeline,
- dropping creates and selects a new `TimelineClip`,
- drag/drop copies audio from the palette rather than moving it.

For users who do not drag, each card has a **➕ Add** button and a right-click **Add to Timeline at Playhead** menu action. These place the palette sound at the current playhead on lane 1.

## Playback fallback behavior

Timeline playback still uses `sounddevice` when it is installed. When `sounddevice` is unavailable, WaveToy now:

1. renders the timeline mix,
2. writes a temporary WAV file,
3. attempts to open/play it with a system player command.

The fallback command search order is:

1. `xdg-open`
2. `paplay`
3. `aplay`
4. `ffplay`
5. `play`

If no playback command is found, the warning tells the user where the temporary WAV was saved and confirms that **Export Last Mix** still works. Stop terminates the tracked fallback subprocess when possible. If `xdg-open` hands playback to a separate system application, that separate player may continue independently.

## Imported-audio metadata behavior

Timeline clips created from imported palette sounds store source metadata rather than raw audio arrays. The arrangement sidecar includes:

- clip timing/lane metadata,
- imported clip source path,
- import metadata such as palette item id/name and duration,
- palette source summaries.

Raw audio arrays are intentionally not embedded in JSON. Full reload/reconstruction of imported clips requires the source audio files to remain available at their stored paths.

## Remaining limitations

- WAV import covers common PCM integer sample widths; uncommon WAV encodings may fail with a clear warning.
- MP3/OGG/FLAC import depends on an external `ffmpeg` executable.
- Fallback playback stop is best-effort for external players, especially when `xdg-open` delegates to a desktop application.
- The task adds metadata for imported clips but does not implement a full arrangement reload workflow.
