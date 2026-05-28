# Task 003: Fix Startup Stylesheet Regression and Debounced Generation

## Summary

Task 003 restores WaveToy startup after the Task 002 slider styling regression and adds a shared debounced generation path for high-frequency UI changes.

## Startup bug and fix

The startup crash happened because the main application stylesheet in `_apply_style()` had been changed to a Python f-string so it could inject the larger centralized slider stylesheet. Qt stylesheets also use braces for CSS-like selector blocks, so selectors such as `QMainWindow { ... }` were interpreted by Python as f-string expressions. That made plain CSS declarations such as `background: #7bdff2;` eligible for Python evaluation and could raise `NameError` before the app window opened.

The fix keeps the main Qt stylesheet as a plain triple-quoted string named `base_style`, then concatenates `self._slider_style_sheet()` when calling `setStyleSheet()`. The slider helper remains centralized and still applies the larger groove/handle metrics from Task 002, but the broad application stylesheet no longer contains f-string interpolation.

## Debounced generation approach

WaveToy now owns one shared single-shot `QTimer` for UI-triggered rendering. The delay is `90 ms`, which is short enough to feel responsive while preventing dozens of full synchronous renders during rapid slider dragging.

The generation flow is:

1. UI-control changes call `_schedule_generate(reason)`.
2. `_schedule_generate()` marks `render_dirty`, records `last_generate_reason`, and restarts the shared debounce timer.
3. When the timer expires, `_run_scheduled_generate()` calls `_generate_now()` with a debounced reason.
4. `_generate_now()` performs the actual render immediately, clears dirty state, and prints lightweight timing output.
5. Explicit actions such as initial startup, presets, recipe application, Play/Make Sound, Save, and live-loop refresh continue to call direct generation so they use current settings immediately.

This does not move synthesis to a worker thread and does not change the synthesis math, slider ranges, recipes, export format, or Paulstretch processing.

## Signals changed from direct generation to scheduled generation

The following controls now schedule debounced generation instead of connecting directly to `_generate()`:

- Per-wave envelope sliders: start loudness, end loudness, and change time.
- Per-wave stereo sliders: ear place, ear spread, and ear dance.
- General controls listed in `widgets_to_regenerate`: duration, pitch start/end, loudness start/end, curve, global stereo controls, Paulstretch enable, Paulstretch amount, and Paulstretch evolution.
- Note, octave, and cents changes update their labels and synchronized pitch sliders immediately, then schedule generation through `_sync_note_to_pitch()`.
- Duration label synchronization remains immediate, then schedules generation through `_sync_duration_slider_to_spin()`.

Label updates remain immediate so the user sees slider feedback during dragging before the debounced render runs.

## Debug output

Generation scheduling and rendering now emit lightweight console messages:

- A scheduled message is printed only when a new debounced batch starts, avoiding a line for every slider tick while the timer is already pending.
- Direct and debounced generation print start/completion messages.
- Completion output includes approximate elapsed render time from `time.perf_counter()`.

## Verification notes

- `python -m py_compile wave_toy.py` passed.
- `python wave_toy.py` could not complete in this container because importing PySide6 requires the missing system library `libGL.so.1`.
- Because the container cannot import PySide6, manual GUI checks for opening the window, dragging sliders, playback, and Paulstretch behavior were not completed here.

## Remaining limitations

- Rendering remains synchronous on the GUI thread. Debouncing reduces redundant renders but a single long render, especially with Paulstretch enabled, can still block the UI.
- Live playback and stop/cancel responsiveness can still be affected by long synchronous generation.
- No worker-thread rendering, Paulstretch cancellation, playhead, or scrolling waveform behavior was added in this task.

## Recommended next task

Task 004 should introduce a small generation controller or worker-thread rendering path with cancellation/coalescing for expensive renders, especially Paulstretch, while keeping explicit Play/Save operations deterministic.
