# Task 086 — Scale, Chord, and Harmony Workbench Foundations

Task 086 turns the existing note wheel theory layer into a compact harmony helper without adding an external music-theory dependency or a persistent project-schema change.

## Theory helpers

WaveToy now defines scale and chord dictionaries as semitone offsets from a root pitch class. Helpers normalize all internal pitch classes to the existing sharp identity policy (`C#`, `D#`, `A#`, etc.) while display helpers can still render Auto, Sharps, or Flats labels.

Added helpers:

- `scale_pitch_classes(root_note, scale_type)` returns normalized pitch classes for the selected scale.
- `chord_pitch_classes(root_note, chord_type)` returns normalized pitch classes for the selected chord.
- `scale_degree_for_note(note, root_note, scale_type)` reports the 1-based scale degree or `None`.
- `chord_degree_for_note(note, root_note, chord_type)` reports harmonic chord degree labels such as 1, 3, 5, or 7 when the note is a chord tone.
- `display_pitch_class_set(notes, root_note, spelling_mode)` renders compact note names without changing internal identity.
- `harmonic_summary(root_note, selected_notes)` provides a small deterministic summary for tests and future UI reuse.

## Scale library

The initial scale library includes Major, Natural Minor, Harmonic Minor, Melodic Minor Ascending, Major Pentatonic, Minor Pentatonic, Blues, and Chromatic. Each scale has a user-facing label and a short mood or usage description.

## Chord library

The initial chord library includes Major Triad, Minor Triad, Diminished Triad, Augmented Triad, Sus2, Sus4, Dominant 7, Major 7, Minor 7, Minor Major 7, Diminished 7, Half-Diminished 7, and Power Chord. Each chord has semitone offsets, a user-facing label, and a concise mood or usage description.

## Harmony Workbench UI

The note wheel dialog now includes a compact **Harmony Workbench** section near the wheel. It provides a root selector, scale selector, chord selector, scale/chord highlight toggles, and Play Scale / Play Chord / Play Arpeggio preview buttons.

The existing spelling selector remains the spelling source for both the wheel and the Harmony Workbench. This keeps behavior compact and avoids introducing redundant state.

## Note wheel highlighting

`CircleOfFifthsNotePicker` accepts an optional highlight set plus a highlight root. Highlights are drawn as halos and stronger outlines so interval colors remain visible. The selected pitch class remains independent from the highlight set, so choosing or highlighting a scale does not silently change the selected note.

Highlights refresh when the workbench root, scale, chord, spelling mode, or wheel layout changes. If both highlight toggles are off, the wheel behaves as it did before Task 086.

## Audio preview behavior

Scale, chord, and arpeggio previews reuse the existing note-wheel in-memory sine preview path. Scale previews play sequential tones, chord previews sum tones at reduced gain to avoid clipping, and arpeggio previews play chord tones sequentially. Preview audio is not saved to disk.

## Future harmonic assets

Reserved category constants and TODO comments identify future asset directions without implementing CRUD or project persistence yet:

- `scale_pattern`
- `chord_pattern`
- `chord_progression`

## Known limitation

This is not a full music-theory engine. The foundation intentionally uses deterministic pitch-class sets and compact degree helpers rather than context-aware notation, modal mixture, secondary dominants, inversions, or progression analysis.
