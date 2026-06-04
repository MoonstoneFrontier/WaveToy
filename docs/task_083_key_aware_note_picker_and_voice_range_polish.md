# Task 083 — Key-Aware Note Picker and Voice Range Polish

Task 083 keeps the note/color/mood picker compact while making its meaning key-aware. The picker still stores notes as pitch classes internally, but the displayed name, interval role, mood, and color are recalculated against the selected base note/key whenever the base note changes.

## Interval-relative mood and color

Mood and color are interval-relative, not absolute-note-relative. For example, C# is the major third when the selected base note is A, but the same pitch class is not the major third when the base note changes to Bb/A#. The wheel therefore derives each bubble's role from semitone distance to the current home note:

- root
- minor second
- major second
- minor third
- major third
- perfect fourth
- tritone
- perfect fifth
- minor sixth
- major sixth
- minor seventh
- major seventh

The selected-note label includes the current interval role and relationship text so the user can see that the mood/color meaning changed after selecting a new base note.

## Enharmonic spelling rules

The wheel preserves pitch-class identity independent of spelling. By default, Auto spelling follows the selected base note/key:

- Sharp-oriented keys prefer sharp names: C, G, D, A, E, B, F#, C#.
- Flat-oriented keys prefer flat names: F, Bb, Eb, Ab, Db, Gb, Cb.
- Existing sharp-only UI values such as A#, D#, and G# are treated as flat-oriented aliases for display, so A# can present the wheel as Bb-oriented without changing stored pitch class identity.

The picker does not display both enharmonic spellings at once. A future advanced theory mode could add dual names, but the default remains compact.

## Auto / Sharps / Flats toggle

The note picker contains a compact spelling selector:

- **Auto** follows the selected base note/key.
- **Sharps** forces sharp note labels.
- **Flats** forces flat note labels.

Changing the toggle updates the wheel labels immediately while preserving the selected pitch class.

## Voice Range rename

The former Voice Size wording was misleading because the control changes octave/register and therefore pitch range, not loudness or physical size. Task 083 renames the control to **Voice Range**, updates compact pitch-panel wording to **Range**, and adds tooltip text explaining that the slider affects musical pitch/register rather than volume.

## Register label mapping

The Voice Range label uses musical register descriptors only and does not imply biology or identity. Slider movement maps smoothly from low to high:

1. contrabass
2. bass
3. baritone
4. tenor
5. alto
6. mezzo-soprano
7. soprano
8. high soprano
9. whistle range

Audio behavior is unchanged; these labels are descriptive UI text for the existing octave/range control.
