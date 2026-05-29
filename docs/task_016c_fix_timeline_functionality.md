# Task 016c — Fix Timeline Tab Functionality

## Root causes

The Timeline tab had been implemented as a static storyboard mockup rather than a functional arrangement editor. Its transport buttons reused the app-level preview play/save callbacks instead of timeline-specific render, play, stop, and export callbacks. Dropping a sound only inserted a decorative `StoryboardClipWidget`; it did not copy rendered audio into arrangement state, did not select the clip, did not render a mix, and did not provide draggable timeline coordinates.

The previous UI also lacked timeline state for clips, playhead position, selected clip id, mix cache, sidecar export metadata, and playhead timer control. Because no real canvas/arrangement model existed, visible cards could not move across time or lanes and could not be duplicated, deleted, mixed, or exported as an arrangement.

## Debug logging added

Timeline diagnostics now use the prefix `[WaveToy Timeline]` and cover:

- Timeline tab construction.
- Drop Sound clicks.
- Forced current sound rendering for timeline drops.
- Current audio shape, duration, and peak.
- Clip creation with id, start time, lane, and duration.
- Clip selection.
- Clip movement with updated start time and lane.
- Arrangement mixdown clip count, duration, and peak.
- Play Story clicks.
- Stop clicks.
- Export attempts, success, cancellation, and failure.

Logging is intentionally not emitted from `paintEvent`.

## Workflow fixed

The Timeline tab now keeps real `TimelineClip` objects containing copied audio, recipe metadata, start time, lane, and duration. Drop Sound forces a fresh render before copying audio, rejects empty or silent audio with a clear warning, appends the clip, selects it, refreshes the canvas size, updates the inspector, and repaints immediately.

A new `TimelineCanvas` draws lane headers, a time ruler, a playhead, large clip blocks, clip names, durations, and waveform thumbnails. Clicking a clip selects it. Dragging left/right changes `start_time_seconds`; dragging up/down changes lanes; start time is clamped to zero. Clicking empty timeline clears selection and moves the playhead.

Play Story renders the arrangement mix first, starts the playhead timer, and uses `sounddevice` when available. If `sounddevice` is missing or fails, the rendered mix remains available and the user gets a clear warning. Stop halts the timer and calls `sounddevice.stop()` when available.

Duplicate and Delete operate on the selected clip and refresh arrangement duration, canvas size, selection, and inspector state. Export Last Mix renders first, saves through the existing `save_audio_file` helper, and writes a `.wave-toy-arrangement.json` sidecar without embedding raw audio arrays.

## Timeline iconography and touch UI changes

Timeline controls are large icon-first toy buttons with multi-line labels for Play Story, Stop, Mix Story, Drop Sound, Add Lane, Zoom In, Zoom Out, Duplicate Clip, Delete Clip, and Export Last Mix. Main tabs were enlarged to make the tab iconography more readable. Timeline lanes use readable emoji lane headers, and clips are drawn as large toy blocks with an icon, name, duration, lane number, and waveform thumbnail.

## Manual test results

Automated syntax verification passed with `python -m py_compile wave_toy.py`.

Launching `python wave_toy.py` could not be completed in this container because the PySide6 Qt import fails before the app starts: `ImportError: libGL.so.1: cannot open shared object file: No such file or directory`. Because Qt cannot launch in this environment, interactive manual checks for sounddevice playback, mouse dragging, and file-dialog export need to be performed on a desktop system with Qt/OpenGL runtime libraries installed.

## Remaining limitations

- External audio import remains unchanged and is still not implemented as a waveform reverse-analysis/import feature.
- Crossfades, clip splitting, and external audio import were intentionally not added.
- If `sounddevice` is unavailable, timeline render/export still work, but live audio playback cannot be verified until `sounddevice` and an audio device are available.
- Export still uses a native save-file dialog, so fully automated export testing is best done later with a small non-dialog test seam.
