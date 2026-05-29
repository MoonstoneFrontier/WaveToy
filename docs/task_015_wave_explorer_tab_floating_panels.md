# Task 015 — Wave Explorer Tab and Floating Toy Panels

## Summary

This change moves the Wave Explorer dashboard out of the Classic Editor scroll page and into a dedicated tabbed interface. The main window now presents three top-level tabs:

- `🎛 Play` — a lightweight performance surface with a waveform preview and transport/save/load buttons.
- `🌊 Wave Explorer` — a non-scroll-heavy waveform-centered dashboard with readable launcher buttons.
- `🧰 Classic Editor` — the original detailed scroll-based editor kept as the fallback while migration continues.

## Wave Explorer layout

The Wave Explorer tab keeps the large `WaveCanvas` in the center and arranges simplified visual buttons around it. The old dense miniature button previews were replaced with a larger label, one symbolic icon, and one short status line so the buttons stay readable.

There is no workspace form embedded underneath the center waveform in normal Explorer use. Detailed controls now open in separate non-modal toy panels, leaving the center waveform visible.

## Floating toy panel approach

Floating panels are implemented as reusable `QWidget` tool windows using the `Qt.Tool` flag. Each panel is created once, reused on later opens, and positioned around the edge of the Wave Explorer tab by default instead of over the waveform center.

Panels use synced controls that forward edits to the existing Classic Editor widgets. This keeps one underlying source of truth for synthesis, save/load, recipes, and UI state instead of introducing duplicate independent state.

## Functional panels

- `🎚 Shape Mix` — mute/solo plus per-wave start loudness, end loudness, and envelope time.
- `🎯 Pitch Toys` — main note controls, pitch bend sliders, per-wave follow/custom pitch controls, cents controls, and Note Wheel access.
- `🎼 Tuning Map` — tuning method, root note, A4 reference, and a short explanation.
- `👂 Stereo Space` — whole-mix pan/width/dance controls plus per-wave pan, width, and dance controls.
- `✨ Sound Magic` — Paulstretch bypass/enable and Paulstretch amount/evolution controls.
- `🌈 Sound Experiments` — built-in preset buttons plus save/load access.

## Classic Editor fallback

The Classic Editor tab keeps the detailed scroll-heavy controls available during the migration. It remains the fallback for full detailed editing and preserves the existing controls for synthesis, stereo placement, presets, Paulstretch, recipe save/load, and export workflows.

## Verification notes

- `python -m py_compile wave_toy.py` was run successfully.
- `python wave_toy.py` could not be fully launched in this container because the Qt/PySide6 runtime import fails without `libGL.so.1`.

## Remaining limitations

- Runtime/manual GUI checks still need to be completed in an environment with the required Qt/OpenGL system libraries installed.
- Floating panels intentionally reuse synced control copies rather than moving all original Classic Editor widgets; this preserves behavior while the migration remains incremental.
- The old Classic Editor is intentionally still present as the fallback tab.
