# Task 088 — Interval Engine and Harmony Export Hardening

Task 088 centralizes interval-derived UI theory into a small helper layer while keeping WaveToy pitch classes internally normalized to sharp names. The goal is to prevent stale mood/color/emoji/relationship labels when the same pitch class changes role under a different home/root note.

## Interval descriptor helper policy

- `interval_descriptor(note, root_note, spelling_mode="Auto")` is the single source for interval role, theory name, semitone distance, mood label, relationship label, emoji, and color.
- Convenience helpers (`interval_color`, `interval_emoji`, `interval_mood_label`, `interval_relationship_label`, and `note_display_descriptor`) delegate to the descriptor rather than keeping separate mappings.
- Legacy callers such as `note_emotion`, `note_relationship`, and `interval_theory_name` remain available for compatibility but now derive from the same descriptor path.

## Pitch-class vs spelling policy

- Internal pitch classes remain normalized sharp names such as `A#`, `C#`, and `D#`.
- Display spelling is presentation-only. Auto/Sharps/Flats changes what the user sees without changing the selected pitch class or preview pitch.
- Example: `C#` relative to `A` is a Major Third (4 semitones), while the same `C#` relative to `Bb`/`A#` is a Minor Third (3 semitones), so its mood and color change with interval role.

## Key orientation alias behavior

`key_spelling_orientation(home_note, spelling_mode="Auto")` documents the UI orientation policy. In Auto mode, user-facing sharp aliases that commonly stand in for flat keys (`A#`, `D#`, and `G#`) prefer flat display (`Bb`, `Eb`, and `Ab`). This is a spelling orientation for the interface, not a music-theory proof of harmonic function. Sharps and Flats still override Auto.

## Note wheel polish

The Note Wheel uses the descriptor summary for compact tooltips/status text. Selected notes remain visually dominant over root, scale, and chord highlight halos, and emoji sizing was kept large enough to remain readable after harmony highlighting.

## Voice Range wording audit

Voice Range/Register language remains frequency-derived and avoids size, loudness, gender, body-size, or identity implications. The control tooltip states that it affects musical pitch/register and does not affect loudness or volume.

## Harmony JSON export/import foundation

- Export writes metadata-only Harmony JSON with `ensure_ascii=False` and `indent=2`.
- Export defaults missing file suffixes to `.json`.
- Export catches write errors and shows a friendly warning instead of failing silently.
- Successful export reports the path plus root/scale/chord summary.
- Import reads metadata-only JSON, requires schema `wavetoy.harmony_metadata.v1`, and applies root note, scale type, chord type, and spelling mode to the Harmony Workbench.
- Import does not import audio, save preview audio, or change the project schema.

## Reserved harmony asset base cleanup

The reserved `ScalePatternAsset`, `ChordPatternAsset`, and `ChordProgressionAsset` names remain public. Their shared JSON-safe fields now live in `HarmonyAssetBase` to reduce duplication without adding Asset Library CRUD or project migrations.

## Known limitations

- No full chord progression editor.
- No MIDI export.
- No piano roll.
- No project schema migration.
- Harmony import/export remains metadata-only and does not export audio.

## Task 089 descriptor export extension

Task 089 keeps the Task 088 Harmony JSON schema string and adds optional descriptor fields rather than requiring a migration. Exports now include `scale_descriptor` and `chord_descriptor` JSON-safe objects, plus chord-root metadata for key-relative roman-numeral analysis. Import still validates the metadata schema and applies core state fields; descriptors are safe to recompute and do not contain audio.
