# Task 084 — Note Wheel Interval Education and Preview

Task 084 upgrades the note/color/mood picker so its geometry matches the interval-relative mood system introduced in Task 083 while preserving the existing circle-of-fifths teaching view.

## Wheel layout modes

The note wheel now has a **Wheel Layout** selector:

- **Intervals** is the default. The current home/root note is placed at the top of the wheel, and the wheel proceeds chromatically through root, minor second, major second, minor third, major third, perfect fourth, tritone, perfect fifth, minor sixth, major sixth, minor seventh, and major seventh.
- **Circle of Fifths** keeps the previous fifths ordering: C, G, D, A, E, B, F#, C#, G#, D#, A#, F.

Colors and moods remain interval-relative in both layouts. Changing the layout changes only the teaching geometry, not the selected pitch class.

## Interval-relative mood and color

Each pitch class is compared to the current home note/key. The same absolute note can therefore receive a different label, color, and mood when the home note changes. For example, C# is a **Major Third** above A, but a **Minor Third** above Bb/A#.

The selected note label combines theory and emotional language:

`Selected Note: C# • Major Third • 4 semitones • Bright / Happy • Major Color`

## Spelling and tooltips

The spelling selector remains compact:

- **Auto** follows the home key orientation.
- **Sharps** forces sharp note names.
- **Flats** forces flat note names.

Bubble tooltips include the displayed note name, interval name, semitone distance, mood, active spelling mode, and active layout mode. The center label shows the home note, spelling mode, and wheel layout.

## Audio preview behavior

The picker adds three in-memory preview buttons:

- **Play Home** plays the home note briefly.
- **Play Note** plays the selected pitch class briefly.
- **Play Interval** previews the relationship between home and selected notes.

Preview audio is short, uses a simple sine tone, respects current octave/cents/tuning reference settings where practical, and is played directly through `sounddevice`. No preview audio is written to disk.

## Melodic vs harmonic interval preview

The interval preview mode selector defaults to **Melodic**:

- **Melodic** plays home briefly, pauses, then plays the selected note.
- **Harmonic** plays home and selected note together at a lower gain to avoid clipping.

Starting a new preview stops/replaces any currently playing preview.

## Voice Range label derivation

The **Voice Range** display now derives its register label from the current note, octave, cents, and tuning-derived frequency. The slider position remains a fallback if a frequency is unavailable. Labels are musical register descriptors only and avoid implying gender, body size, or biological identity.

## Known limitations

- The wheel remains a pitch-class picker, not a full music theory engine.
- Note preview uses a simple sine tone rather than the full synthesis chain.
- In-memory preview requires `sounddevice`; otherwise WaveToy shows the existing playback warning path.
- The first animation/export representation remains future work and should start with generic human-readable JSON before target-specific formats.

## Task 085 synchronization note

Task 085 tightened live refresh behavior for the Task 084 controls. Visible wheel dialogs now refresh when the home note changes, spelling and layout changes redraw labels/tooltips without changing the stored pitch class, and closing a dialog stops any active in-memory preview when safe. The Circle of Fifths layout still uses the fixed fifths order listed above.

## Task 086 follow-up

The note wheel preview system now also supports scale, chord, and arpeggio workbench previews. These still use the same in-memory preview path and do not write preview audio files.

## Task 088 interval engine follow-up

Interval education labels now flow through `interval_descriptor()`, which centralizes semitone distance, theory name, mood, relationship, emoji, color, and display spelling. This prevents stale labels when the same selected pitch class changes role under a different Home note.

Auto spelling now uses `key_spelling_orientation()` to make the UI alias policy explicit: `A#`, `D#`, and `G#` may display as flat-oriented homes (`Bb`, `Eb`, `Ab`) for compatibility, while Sharps and Flats remain explicit overrides.
