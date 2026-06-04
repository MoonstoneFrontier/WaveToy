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

## Task 079 engine bridge

`PerformanceTimelineEngine` now owns musical overlay queries for performance-time consumers. It exposes beat grids, measure grids, current beat/measure, and snap-time calculation while continuing to respect `MusicalTimingSettings`.

Musical Timing remains disabled by default. When disabled, the engine returns empty grid overlays and zero beat/measure state instead of quantizing speech. Transition timing stays millisecond-based even when grid snap is enabled for timeline point editing.

## Task 083 note picker spelling note

The note/color/mood picker remains a pitch-class picker, not a full music theory engine. Mood and color are calculated from the interval between the selected note and the current base note/key. Auto spelling uses sharp labels for sharp-oriented keys and flat labels for flat-oriented keys, with manual Sharps and Flats overrides for compact enharmonic display.

## Task 084 note wheel layout reminder

The note/color/mood picker now distinguishes **Intervals** layout from **Circle of Fifths** layout. Intervals is the default because mood and color are interval-relative to the current home note; Circle of Fifths remains an optional educational geometry. This does not change the future Musical Timing plan: current speech timing remains millisecond-based, and beat/measure timing is still future architecture work.
