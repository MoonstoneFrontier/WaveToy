# MIDI Import/Export Roadmap

MIDI support is roadmap-only for Task 070. No MIDI dependency is implemented yet.

## MIDI notes to NoteEvent mapping

Future MIDI import can map each MIDI note to a `NoteEvent`:

- MIDI start tick → `start_ms` through the imported tempo map.
- MIDI duration ticks → `duration_ms`.
- MIDI note number → `midi_note`, `note_name`, and `target_pitch_hz`.
- Velocity → `velocity`.
- Track lyric or marker events → `lyric` where available.

## Lyric syllable alignment

A future alignment pass should map lyric syllables to phoneme indices without replacing direct phoneme controls. Manual correction should remain available.

## Pitch bend support

Pitch bend events can become automation points or per-note `pitch_bend_cents`, depending on density and editor needs.

## Tempo map import

Tempo and time-signature events can extend the current single-entry `tempo_map` into multiple tempo regions.

## Future export workflows

Potential exports include DAW-friendly MIDI notes, Vocaloid-style note/lyric sketches, and sidecar JSON that preserves WaveToy-specific articulation data.
