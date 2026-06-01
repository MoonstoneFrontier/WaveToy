# Task 045 — Glass UI, SVG Audio, and Architecture Foundation

## Scope

This task begins the transition from a monolithic desktop prototype toward a professional visual audio and articulation workstation. The work is intentionally incremental: `wave_toy.py` remains the active application entry point and existing synthesis, export, timeline, articulation, speech asset, graphical editor, and Paulstretch-style functions stay intact.

## UI density changes

- Button sizing now targets a leaner 32–38 px range through shared sizing tokens.
- Global button padding was reduced to `4px 8px` with smaller radii and thinner borders.
- Timeline transport buttons changed from stacked two-line controls to compact single-line controls.
- Toolbar buttons keep readable labels while reducing oversized chrome.

## Icon treatment

- Button text was shortened so symbolic icons and line glyphs have more visual priority.
- Timeline transport controls use sharper compact symbols and a slim accent edge instead of large colored slabs.
- The main waveform canvas replaces cartoon mascot treatment with a compact signal glyph.

## Glass visual direction

The first glass pass moves panels away from pastel block styling and toward a dark laboratory-workstation surface:

- translucent panel backgrounds;
- thin blue-white borders;
- restrained cyan/green/magenta accent colors;
- color focused on waveform energy, selected states, and signal strokes;
- softened highlights instead of heavy decorative card fills.

## Vertical waveform treatment

The WaveCanvas still uses vertical waveform identity. Left, Mid, and Right are now drawn inside subtle glass tube boundaries with sharper waveform strokes and restrained glow, making the waveforms read as audio signals flowing through transparent vertical containers.

## SVG audio groundwork

A lightweight `wavetoy.svg` package now defines JSON-friendly primitives for future vector editing:

- `WaveExpression` for expression/source metadata;
- `SvgAudioObject` for visual object identity, geometry, handles, and render metadata;
- `EditableHandle` for future trim/envelope/control handles;
- `svg_metadata_for_clip()` to attach non-breaking expression and SVG metadata to timeline clips.

The active renderer still uses sample arrays. The new metadata is additive and intended to support future SVG editors for waveform layers, stereo field, pitch curves, vocal tract, articulation timeline, and main timeline clips.

## Professional language cleanup

This pass keeps the WaveToy name while replacing visible toy-like wording where it was low risk, including pitch controls and panel titles. Internal object names that are tied to existing style selectors or compatibility paths are left in place for now.

## Verification performed

- Syntax check: `python -m py_compile wave_toy.py`
- Launch smoke check attempted: `timeout 5s python wave_toy.py` (blocked in this container by missing `libGL.so.1` for PySide6)

## Remaining limitations

- This is not a full UI rewrite; many widgets still live in `wave_toy.py`.
- PySide remains the current desktop prototype and does not imply iPad support.
- The SVG metadata does not yet render or edit SVG; it is a foundation for future editors.
- Some internal names still contain legacy `toy`/`storyboard` identifiers to avoid risky renames.
