# Musical Timing Plan

`MusicalTimingSettings` provides a foundation for future beat-locked speech workflows while preserving current millisecond timing as the default.

Fields:

- `enabled`
- `bpm`
- `time_signature_numerator`
- `time_signature_denominator`
- `snap_enabled`
- `snap_subdivision`
- `swing_percent`
- `count_in_enabled`

Future track types may include tempo, pitch, lyric, phoneme, accentuation, and viseme tracks. MIDI import/export should remain a future feature and should not force musical timing onto ordinary speech workflows.
