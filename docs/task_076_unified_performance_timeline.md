# Task 076 — Unified Performance Timeline

Task 076 turns the Performance tab into a unified time-based performance system. Automation, pitch-curve viewing, stress-marker viewing, musical-grid snapping, and future expression lanes now share a `TimelineParameterTrack` / `TimelineParameterPoint` model.

## Canonical model

Canonical project and library performance data lives under the `performance` object:

```json
{
  "performance": {
    "performance_id": "uuid",
    "name": "Current Performance",
    "version": 2,
    "timeline_tracks": [
      {
        "track_id": "uuid",
        "name": "Accentuation",
        "track_kind": "automation",
        "target_parameter": "accentuation_db",
        "points": [
          {"time_ms": 0, "value": 0.0, "curve": "linear", "label": "", "metadata": {}}
        ],
        "muted": false,
        "visible": true,
        "color": "#ffd166",
        "lane_order": 0
      }
    ]
  }
}
```

Supported `track_kind` values are `automation`, `pitch`, `stress`, `musical_grid`, and `marker`. Points remain JSON-safe and do not contain generated audio arrays.

## Legacy Task 075 compatibility

Task 075 `automation_tracks` are still accepted on load:

- `performance.automation_tracks` is converted to canonical `performance.timeline_tracks`.
- legacy top-level `automation_tracks` is read only when no canonical performance timeline exists.
- new project snapshots do not write duplicate top-level `automation_tracks`.

## UI behavior

The tab is now named **Performance Timeline**. It contains:

- a visual lane editor with one horizontal lane per visible track;
- millisecond ruler and playhead;
- line segments and draggable point markers;
- double-click point creation;
- Delete/Backspace point deletion;
- optional musical timing snap;
- inspector tables for fallback editing.

This is intentionally not a full DAW editor: no Bezier handles, MIDI dependency, or target-specific animation export is introduced.

## Real render targets

Task 076 has two render-active targets:

- `accentuation_db`: summed dB envelope, clamped to `[-24, 24]`, applied as gain on the rendered copy.
- `pitch_bias_cents`: summed cent envelope, clamped to `[-1200, 1200]`, applied as a lightweight non-destructive pitch-shift hook on the rendered copy.

The pitch-bias implementation is deliberately conservative and keeps the original audio buffers out of JSON. A future frame-aware oscillator integration can refine voiced-only behavior further.

## Bridge lanes

Existing time-based systems are represented as bridge lanes where safe:

- `SyllableStressMarker` data appears as a stress lane with marker metadata.
- `PitchAutomationPoint` data appears as a pitch lane.
- Basic edits to bridge point time/value are mirrored back to the source objects.

Automatic syllable detection, vibrato editing, and portamento editing are intentionally out of scope.

## Waveform overlay hook

The articulation waveform diagnostics canvas now has a lightweight performance overlay API:

- `performance_points`
- `active_track`
- `playhead_ms`

The selected timeline track can be drawn over the waveform without a large waveform-editor rewrite.
