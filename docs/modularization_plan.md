# WaveToy Modularization Plan

## Goal

Move WaveToy away from a single giant `wave_toy.py` file without breaking the current desktop app. The main script remains the launch entry point while low-risk pure logic and data models are gradually extracted.

## Principles

1. Keep `wave_toy.py` runnable throughout the transition.
2. Extract pure helpers before UI lifecycle code.
3. Avoid changing playback, stop/cancel, and audio-device lifecycle behavior during structural work.
4. Preserve saved recipe, phoneme, chain, and timeline metadata compatibility.
5. Prefer JSON-friendly models for anything that may be shared with web/iPad frontends.

## Proposed package boundaries

### `wavetoy/synthesis/`

Pure waveform and envelope generation:

- oscillator functions;
- harmonic stack helpers;
- gain envelopes;
- modulation curves;
- Paulstretch-style offline transforms when isolated safely.

### `wavetoy/audio/`

Audio I/O and sample utilities:

- WAV read/write;
- import/resample helpers;
- stereo normalization;
- peak/waveform summary functions;
- playback-adjacent helpers only after lifecycle behavior is covered by tests.

### `wavetoy/timeline/`

Timeline data and non-UI edit operations:

- clip metadata;
- trim/stretch math;
- arrangement serialization;
- mixdown planning;
- snap/grid calculations.

### `wavetoy/articulation/`

Speech and vocal tract models:

- phoneme models;
- articulation chains;
- coarticulation interpolation;
- source-wave metadata;
- renderer functions after parity checks exist.

### `wavetoy/assets/`

Asset catalogs and reusable UI-independent descriptors:

- preset definitions;
- phoneme defaults;
- color/accent tokens;
- future icon/vector assets.

### `wavetoy/ui/`

PySide-only presentation code:

- shared theme and sizing tokens;
- reusable widgets;
- canvas widgets;
- dialogs;
- window assembly.

### `wavetoy/svg/`

Future SVG/vector audio model:

- visual object identity;
- editable handles;
- expression references;
- geometry metadata;
- SVG render hints.

### `wavetoy/project/`

Project persistence and portability:

- project schema;
- JSON migrations;
- sidecar import/export;
- validation helpers.

## Safe first extractions

1. Data-only models that do not depend on PySide.
2. Pure math helpers that accept and return numpy arrays.
3. Serialization helpers for recipes, clips, phonemes, and articulation chains.
4. Theme tokens after UI screenshots confirm parity.

## Deferred/risky extractions

- Audio playback lifecycle and fallback player handling.
- Stop/cancel behavior.
- Timeline drag state machines.
- Live loop refresh timing.
- Large canvas refactors without visual regression checks.

## Current task foundation

This task introduces `wavetoy/svg/` only. It is deliberately isolated and imported by `wave_toy.py` to provide additive metadata for timeline clips while keeping launch behavior unchanged.
