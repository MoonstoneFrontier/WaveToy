# SVG Audio Representation Plan

## Vision

WaveToy should eventually represent audio as editable visual objects connected to mathematical expressions, not only as rendered sample arrays. The current renderer remains sample-based, but each visual element can gain metadata that describes source expressions, geometry, handles, and render hints.

## Initial data concepts

### `WaveExpression`

Represents the mathematical or procedural source behind sound:

- `expression_id`
- `label`
- `expression_text`
- `parameters`
- `renderer_hint`
- `sample_rate`
- `duration_seconds`

Possible expression metadata:

- oscillator formula;
- harmonic stack;
- envelope function;
- modulation function;
- pitch curve;
- pan curve;
- articulation envelope.

### `SvgAudioObject`

Represents a visual/editable object:

- `visual_object_id`
- `expression_source_id`
- `geometry`
- `editable_handles`
- `render_metadata`

### `EditableHandle`

Represents a vector control point or direct manipulation handle:

- trim start/end;
- envelope points;
- pitch anchors;
- pan anchors;
- formant/vocal tract controls;
- articulation timing boundaries.

## Existing canvases that should become SVG-like

1. Waveform layer editor.
2. Stereo field.
3. Pitch curve.
4. Vocal tract.
5. Articulation timeline.
6. Main timeline clips.

## Rendering strategy

- Keep numpy sample rendering as the authoritative audio path for now.
- Attach expression and visual metadata to generated clips and assets.
- Render SVG-like overlays first, then move selected canvases to true SVG/exportable vector models later.
- Keep waveform strokes vertical where WaveToy already uses vertical waveform identity.
- Use glass tube/container metadata for vertical waveform renderers.

## Persistence strategy

- Store expression and SVG metadata in sidecar JSON.
- Avoid embedding large sample arrays in project JSON.
- Reference imported files by path or project asset ID.
- Version the schema before replacing existing saved formats.

## Current implementation seed

The `wavetoy/svg/audio_objects.py` module defines the first JSON-friendly dataclasses and a helper that creates clip-level expression and SVG metadata. `TimelineClip.metadata()` includes the new fields without removing or changing existing sample rendering.
