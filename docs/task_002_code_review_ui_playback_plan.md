# Task 002 Code Review: UI and Playback Improvement Plan

## 1. Executive summary

WaveToy is a feature-rich single-file PySide6 desktop synthesizer. The current app already covers waveform synthesis, stereo shaping, recipe save/load, export, direct playback, command-line playback fallback, and Paulstretch-style ambience. The biggest near-term problem is not missing functionality; it is that too many controls are visible at once and too much expensive audio work can happen synchronously on the UI thread.

For this task, the only code change made is a low-risk centralized slider style helper. It makes existing `QSlider` controls larger and rounder without changing slider ranges, recipe serialization, synthesis math, playback, export, or Paulstretch behavior. The rest of the work should be handled as focused follow-up tasks.

Top findings:

- `wave_toy.py` is about 2,400 lines and is too large for sustainable feature work, but it should not be split in this review task.
- The current layout uses a three-column, all-controls-visible design that targets a large desktop window and scrolls vertically on smaller screens.
- Slider ranges already have high internal resolution, but value changes trigger immediate full regeneration, including Paulstretch when enabled.
- The waveform viewer is animated and zoomable but does not currently know playback position, show a playhead, or scroll in response to playback.
- Stop behavior currently stops only the sounddevice/live-loop path. It does not manage spawned system-player processes and cannot interrupt synchronous generation/Paulstretch work while the UI thread is busy.

## 2. Current architecture observations

### Repository layout

Current top-level files are intentionally small in number:

```text
AGENTS.md
README.md
requirements.txt
wave_toy.py
wave_toy_single_module.py
```

Observations:

- `wave_toy.py` is the active application entry point and contains synthesis, audio processing, file export, waveform canvas rendering, UI construction, presets, recipe handling, playback, and application startup.
- `wave_toy_single_module.py` appears to be a similar snapshot or alternate single-file copy. Treat it as historical/reference until the project explicitly decides whether to remove, archive, or compare it.
- `README.md` and `AGENTS.md` accurately describe the project as a PySide6/numpy single-file GUI with optional `sounddevice` playback and ffmpeg export support.
- `requirements.txt` should remain minimal; avoid new dependencies until playback lifecycle and UI structure are stabilized.

### Is `wave_toy.py` too large?

Yes. A single file near 2,400 lines is becoming difficult to maintain because unrelated responsibilities are intertwined:

- Audio constants and synthesis data model.
- Waveform generation and Paulstretch processing.
- File export and ffmpeg conversion.
- Canvas drawing and visual overlays.
- Main window construction and styling.
- Presets and recipe persistence.
- Playback and live-loop control.

Recommended eventual module boundaries:

```text
wave_toy.py                  # thin app entry point, main window bootstrap
wave_toy_app/settings.py     # SynthSettings and constants
wave_toy_app/synthesis.py    # waveform generation, envelopes, normalization
wave_toy_app/modules.py      # Paulstretch and future processors
wave_toy_app/export.py       # WAV and ffmpeg export helpers
wave_toy_app/canvas.py       # WaveCanvas and playback visual state
wave_toy_app/ui.py           # WaveToyWindow or smaller UI builders
wave_toy_app/presets.py      # built-in and user recipe helpers
wave_toy_app/playback.py     # playback controller/state machine
```

Do not do this all at once. Start by extracting pure, testable helpers such as synthesis and export, then introduce a playback controller.

## 3. UI problems found

### Current layout behavior

The current UI creates a scroll area, a root widget with a minimum size, and three side-by-side columns. The window starts at `1280x820`, with a `960x680` minimum window and a root content minimum of `940x660`.

The visible groups are:

- Title and subtitle.
- Left column:
  - Mix the Wave Shapes.
  - Choose Pitch.
- Center column:
  - WaveCanvas.
  - Explanation box.
- Right column:
  - Change Over Time.
  - Sound Modules.
  - Stereo Space.
  - Stereo Space Per Wave.
  - Sound Experiments.
- Bottom row:
  - Make, Stop, Save, Load, Loop status.

### Problems

- The three-column design is wide and vertically busy. It can work on a large desktop monitor but feels cramped on common laptop heights once title, subtitle, margins, group titles, and bottom transport controls are included.
- Many controls are advanced or secondary but are always visible.
- The bottom transport row competes with the rest of the UI for vertical space and is not sticky inside the scroll area.
- `Stereo Space Per Wave` is powerful but advanced; it consumes a lot of vertical and horizontal space.
- `Sound Modules` is also advanced because enabling Paulstretch can greatly change render time and playback length.
- The explanation panel is educational and useful, but it takes fixed vertical space that could be collapsible or tabbed for compact layouts.
- Group titles and large rounded boxes make the app friendly, but the spacing/padding is too expensive when every group is visible at once.

### Minimum practical window size

Recommended targets:

- Comfortable desktop target: `1280x800` or larger.
- Minimum practical laptop target after layout work: about `1024x700`.
- Absolute minimum with scroll fallback: about `900x640`.
- Tablet-like target: design around `1024x768` landscape with larger controls and fewer visible groups.

## 4. Slider improvement recommendations

### Current slider strengths

- Sliders already use high-resolution internal scaling for dB, MIDI pitch, seconds, percentages, rates, and Paulstretch values.
- Most sliders already connect directly to `_generate`, giving immediate visual/audible feedback for lightweight patches.
- Value labels use friendly text and icons, which is appropriate for the project tone.

### Current slider problems

- Every value change can regenerate the full audio buffer. When Paulstretch is enabled, this can become expensive and make dragging feel sticky.
- Some sliders are narrow because they live inside dense grids.
- The app has several duplicated slider construction patterns, so future style and behavior changes are easy to miss.
- There is no debounced render path for expensive modules.
- There is no distinct fast-preview path for dragging versus final high-quality render after release.

### Safe change implemented in this task

A centralized slider style helper was added to `wave_toy.py`:

- `SLIDER_MIN_HEIGHT = 44`
- `SLIDER_GROOVE_HEIGHT = 18`
- `SLIDER_HANDLE_SIZE = 34`
- `SLIDER_HANDLE_RADIUS = 17`
- `_slider_style_sheet()`

This is a visual/touch-target polish change only. It does not change synthesis values, saved recipes, playback behavior, or export behavior.

### Recommended next slider changes

1. Add one slider factory/helper for all app sliders.
   - Apply consistent minimum width.
   - Set page/single step values by control type.
   - Optionally support labels and tooltips from one definition.
2. Add debounced regeneration.
   - Lightweight settings can update immediately.
   - Expensive module renders should wait 50-120 ms after the last slider event.
3. Use `sliderPressed`, `sliderMoved`, and `sliderReleased`.
   - During drag: update labels and maybe a cheap preview.
   - On release: run full render with Paulstretch if enabled.
4. Keep internal resolution high, but tune steps.
   - dB: 0.1 dB to 0.25 dB is enough for most UI changes.
   - pitch: cents-level precision is useful, but labels should avoid excessive numeric churn.
   - percent controls: 0.5% or 1% perceived increments are usually better than ultra-fine twitchy updates.
5. Add numeric tooltip/value display for advanced mode.
6. Keep touch-friendly target size at or above 44 px, preferably 48 px for future tablet layouts.

## 5. Waveform playback visualization recommendation

### Current waveform drawing behavior

The waveform viewer currently:

- Stores current stereo audio, frequency envelope, loudness envelope, mascot text, and visual condition data.
- Repaints on a 50 ms timer, about 20 frames per second.
- Uses animation phase for decorative motion and condition overlays.
- Can zoom using the mouse wheel and reset zoom on double-click.
- Draws a waveform snapshot and stereo/condition visuals.

The viewer currently does not:

- Track playback start time.
- Receive playback progress from the playback path.
- Display a playhead tied to audio output.
- Scroll the waveform during playback.
- Distinguish between generated waveform position and actual audio device position.

### Recommended visualization model

Use a playback state model independent of drawing:

```text
PlaybackState
  is_playing: bool
  started_monotonic_seconds: float
  paused_or_stopped_at_sample: int
  current_sample_estimate: int
  total_samples: int
  sample_rate: int
  source: sounddevice | system-player | render-preview
```

Recommended first implementation:

- Add a thin playhead to the static waveform.
- Estimate playhead position from monotonic time and sample rate.
- Refresh at 30 FPS while playing, and lower to 10-20 FPS while idle.
- When zoomed, auto-scroll the visible window so the playhead remains in view.
- Keep the waveform static by default; add scrolling-under-fixed-playhead only after the playhead model is stable.

Why start with playhead-over-static-waveform:

- It is easier to reason about.
- It keeps zoom behavior simpler.
- It avoids large changes to `WaveCanvas._visible_slice` and drawing paths.
- It is less likely to hurt audio performance.

Future option:

- Add a performance mode where the playhead is fixed near the center and the waveform scrolls underneath. This is visually engaging but requires careful view-window math and should be a follow-up task.

## 6. Stop/cancel/playback lifecycle findings

### Play path

Current one-shot play path:

```text
Make Sound / Space
  -> _play()
  -> _generate()
  -> _play_current_audio_once()
  -> sounddevice sd.stop() + sd.play(..., blocking=False)
     OR system-player fallback using subprocess.Popen(...)
```

### Stop path

Current stop path:

```text
Stop button
  -> _stop()
  -> _disable_live_loop()
  -> stop live-loop timer
  -> sd.stop() if sounddevice is available
```

### Live loop path

```text
Shift+Space
  -> _toggle_live_loop()
  -> _restart_live_loop(regenerate=True)
  -> _generate()
  -> sd.stop()
  -> sd.play(...)
  -> start timer for clip duration
```

### Why stop can fail or feel broken

- `_generate()` is synchronous on the UI thread. If Paulstretch is expensive, the UI cannot process the Stop button until generation returns.
- `paulstretch_process()` has nested loops over channels and windows with FFT work and no cancellation checks.
- `_stop()` only stops live-loop/sounddevice playback. It does not track or terminate system-player fallback subprocesses.
- Exceptions from `sounddevice` playback are swallowed in `_play_current_audio_once`, which makes lifecycle diagnosis harder.
- There is no single source of truth for playback state. State is split across `current_audio`, `live_loop_enabled`, `live_loop_is_refreshing`, a timer, `sounddevice`, and optional subprocess players.
- Temporary WAV files created for system-player playback are not tied to process completion, which may eventually leave stale temp files.

### Recommended lifecycle changes

1. Add a `PlaybackController` class.
   - Own sounddevice calls.
   - Own fallback process handles.
   - Own temporary playback files.
   - Expose `play(audio)`, `stop()`, `is_playing`, and progress estimate.
2. Add cancellation for expensive generation.
   - Use `threading.Event` or a generation token.
   - Check cancellation inside Paulstretch channel/window loops.
   - Avoid updating `current_audio` if the generation token is stale.
3. Move long generation to a worker thread.
   - Keep UI label updates immediate.
   - Disable or mark render controls while a full render is in progress.
4. Add debug logging around lifecycle events.
   - `play_requested`
   - `generate_started`
   - `generate_finished`
   - `generate_cancelled`
   - `sounddevice_play_started`
   - `sounddevice_stop_requested`
   - `fallback_process_started`
   - `fallback_process_terminated`
   - `playback_error`
5. Avoid broad playback rewrites in one patch. First add logging and state centralization, then add cancellation, then add visualization progress.

## 7. One-screen layout proposal

### Recommended hierarchy

```text
WaveToyWindow
├── Top transport/preset strip (always visible)
│   ├── Make / Play
│   ├── Stop
│   ├── Live Loop toggle + status
│   ├── Save
│   ├── Load
│   └── Preset selector or compact preset buttons
│
├── Main visual area (always visible)
│   ├── Waveform viewer
│   ├── Playhead/progress indicator
│   └── Compact explanation/status line
│
└── Control area (scrollable or tabbed)
    ├── Tab: Sound
    │   ├── Mix the Wave Shapes
    │   ├── Choose Pitch
    │   └── Change Over Time
    │
    ├── Tab: Stereo
    │   ├── Global Stereo Space
    │   └── Per-Wave Stereo Space
    │
    ├── Tab: Modules
    │   └── Paulstretch Dream Space
    │
    └── Tab: Learn / Recipes
        ├── Beginner explanation
        └── Sound Experiments / user recipes
```

### Always visible

- Play / Make Sound.
- Stop.
- Live loop state.
- Waveform viewer.
- Minimal current preset/name/status.
- Most important clip settings: duration, pitch, loudness/mix summary.

### Advanced/collapsible

- Per-wave stereo controls.
- Paulstretch controls.
- Detailed beginner explanation.
- Saved recipe management.
- Export options beyond default WAV save.

### Scroll-area strategy

- Keep the app shell itself stable.
- Make only the lower control area scrollable.
- Avoid placing the transport controls at the bottom of a scrolling page.
- On small screens, stack tabs vertically or use a compact tab row.

## 8. iPad/tablet future design notes

WaveToy is currently a Python desktop application. Do not implement iPad-specific platform support yet, but keep the UI direction tablet-safe.

### Touch target guidance

- Minimum target: 44x44 px.
- Preferred target for performance controls: 48-56 px.
- Slider handles: 34-40 px visual handle, 44+ px widget height.
- Buttons: 48+ px height for transport actions.
- Leave enough space between adjacent sliders to avoid accidental touch input.

### Responsive grouping strategy

- Treat the waveform viewer and transport controls as the primary performance surface.
- Use tabs/collapsible panels for editing depth.
- Avoid dense four-column grids on tablet-sized layouts.
- Prefer one or two columns in touch layouts.
- Keep labels next to controls, but allow compact icon/value labels when width is tight.

### Future platform options

1. **PySide6 responsive desktop layout**
   - Lowest disruption.
   - Best immediate path for laptops and touch Windows/Linux tablets.
   - iPad support remains indirect/non-native.

2. **Web front-end**
   - Strongest route for iPad browser interaction.
   - Requires an audio/render backend boundary.
   - Larger architectural change; do not begin until playback state and synthesis modules are separated.

3. **Remote-controlled local audio engine**
   - iPad could control a desktop Python engine over LAN.
   - Useful for performance setups.
   - Requires security, discovery, and latency planning.

4. **Separate simplified performance mode**
   - Best user experience for tablet/touch.
   - Keep only transport, waveform, presets, macro sliders, and emergency stop visible.
   - Advanced design/editing remains in desktop mode.

Recommended direction: first improve PySide6 responsiveness and extract a clean audio engine boundary. That preserves the current app while keeping a future web/tablet controller possible.

## 9. Prioritized next tasks

1. **Playback lifecycle logging and state centralization**
   - Add explicit playback state and diagnostic logs without changing audio behavior.
2. **Stop/cancel reliability for Paulstretch**
   - Add cancellation token/event checks inside long generation paths.
   - Make Stop request cancellation even when render work is pending.
3. **Debounced slider/render pipeline**
   - Separate label updates, lightweight preview generation, and expensive module rendering.
4. **Waveform playhead visualization**
   - Add static-waveform playhead based on playback start time and sample rate.
   - Add auto-scroll only after playhead state is reliable.
5. **One-screen/tabbed layout pass**
   - Move transport to the top.
   - Keep waveform always visible.
   - Put advanced controls into tabs or collapsible sections.
6. **Module extraction phase 1**
   - Extract pure synthesis/settings/export helpers after tests or compile checks are in place.
7. **System-player fallback cleanup**
   - Track spawned process handles and temp files so Stop can terminate fallback playback.

## 10. Risks and regression concerns

- Changing playback/threading can easily break sounddevice behavior, live loop timing, or fallback playback. Keep those changes isolated and test both with and without `sounddevice` installed.
- Moving generation off the UI thread requires careful handling of Qt object updates; only update widgets from the main thread.
- Paulstretch cancellation must avoid returning half-written invalid buffers unless the caller explicitly handles cancellation.
- Debouncing slider renders can improve responsiveness but may make the app feel less immediate if delays are too long.
- A tabbed layout can hide educational controls that are currently discoverable. Use clear labels and a beginner-friendly default tab.
- Any file split can break recipe compatibility or import assumptions if done too broadly.
- System-player process management is platform-sensitive. Terminating process groups should be tested on Linux/macOS/Windows separately if cross-platform support matters.
