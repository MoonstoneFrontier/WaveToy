# Musical Timing Plan

WaveToy remains a millisecond-based speech editor by default. Musical Timing is an optional overlay for beat-aware speech, singing experiments, animation export, and future DAW workflows.

## Implemented foundation

`MusicalTimingSettings` includes:

- `enabled`
- `bpm`
- `time_signature_numerator`
- `time_signature_denominator`
- `snap_enabled`
- `snap_subdivision`
- `swing_percent`
- `count_in_enabled`
- `grid_visible`
- `beat_unit_ms`
- `bars_visible`

Helper functions:

- `beat_to_ms`
- `ms_to_beat`
- `note_value_to_ms`
- `quantize_ms_to_grid`

## UI behavior

The Articulation Timeline keeps Musical Timing controls in a collapsed section by default. When disabled, existing millisecond duration editing remains unchanged. When enabled with Show Beat Grid, Visual Speech Timeline draws bar and beat lines on the same scale as phoneme blocks.

## Snapping safety policy

Musical snap applies only to phoneme block durations for now. Transition windows remain millisecond articulation timing because they shape coarticulation, stop releases, fricative holds, and diphthong movement. This preserves existing transition model defaults and user-entered transition values.

## Future work

- Swing-aware offbeat quantization for phoneme durations only unless transition-safe behavior is validated separately.
- Count-in audio/metronome preview.
- Multi-tempo maps.
- Lyric syllable lanes and note editing UI.
- Task 071/072 may expand the read-only pitch lane into a safe note lane if it does not crowd the Visual Speech Timeline.
