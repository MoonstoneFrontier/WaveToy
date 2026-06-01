# iPad and Web Portability Plan

## Current state

WaveToy is currently a Python/PySide6 desktop prototype. This is appropriate for rapid audio-lab iteration, but PySide is not the long-term iPad target because native iPad distribution, touch-first layout, browser audio APIs, and Pencil-oriented SVG editing are better served by a web/PWA or native frontend architecture.

## Recommended future stack

### Frontend

- React
- TypeScript
- SVG
- WebAudio API
- Progressive Web App (PWA)

### Optional shared/core layer

- Rust DSP core later, compiled to WebAssembly for browser/iPad and native libraries for desktop.
- Python remains the current desktop research lab until models and DSP paths stabilize.

## Why SVG matters

SVG provides a portable interaction model for editable visual audio:

- waveform layer paths;
- stereo field curves;
- pitch and pan automation;
- vocal tract control points;
- articulation timelines;
- clip boundaries and trim handles;
- signal-flow diagrams.

A React/TypeScript frontend can render these objects as native SVG while WebAudio schedules or renders the associated expression model.

## Models that must become JSON-serializable

- Synth recipes and per-wave oscillator settings.
- `WaveExpression` metadata.
- Timeline clips, lanes, trims, stretch modes, and clip handles.
- Audio palette item references.
- Speech asset metadata.
- Articulation phonemes and chains.
- Pitch curves, pan curves, envelopes, modulation curves.
- Graphical editor nodes/layers and SVG visual object geometry.
- Project-level dependency references for imported audio files.

## Compatibility strategy

1. Keep desktop WaveToy intact.
2. Add JSON-friendly model objects alongside existing sample rendering.
3. Build schema migration tools before changing saved-project formats.
4. Extract DSP logic only after tests cover output shape, duration, and peak behavior.
5. Prototype SVG editors against exported JSON before replacing PySide canvases.

## Important limitation

This plan does not claim current iPad support. It defines the path for making WaveToy portable once the data and expression models are separated from the PySide desktop UI.
