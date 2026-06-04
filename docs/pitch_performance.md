# Pitch Performance Foundation

Pitch performance now has serialization-ready primitives for singing and animation export, but Task 070a keeps active automation lightweight.

## Data models

- `NoteEvent` describes a target note with timing, MIDI note, target pitch, lyric text, phoneme bindings, velocity, pitch bend, vibrato, and portamento.
- `PitchAutomationPoint` describes a sampled pitch target with a curve type and source (`manual`, `note_event`, `vibrato`, or `portamento`).
- `SyllableStressMarker` describes manual phrasing emphasis with stress, accentuation, timing bias, and pitch bias.

## Lightweight pitch curve generation

WaveToy currently generates stable note target start/end points from note events. Vibrato and portamento fields remain serialized on `NoteEvent` for future tasks, but they are not actively synthesized into dense automation yet.

## Vowel anchoring policy

Singing pitch belongs mainly to vowels and sustained voiced material:

- vowels: full pitch follow (`1.00`)
- glides: partial pitch follow (`0.75`)
- liquids: partial pitch follow (`0.70`)
- nasals: partial pitch follow (`0.55`)
- voiced fricatives: conservative pitch follow (`0.25`)
- stops, unvoiced fricatives, and affricates: no pitch follow (`0.00`)

## Stress marker integration

`SyllableStressMarker` should eventually influence `accentuation_db`, `timing_bias`, and `pitch_bias_cents` together. Automatic syllable detection and stress editing UI remain deferred.

## Task 079 pitch/stress timeline bridge

Pitch and stress are now visible through the shared Performance Timeline engine. `PitchAutomationPoint` data is converted to a derived `pitch` lane targeting `pitch_hz`, and `SyllableStressMarker` data is converted to a derived `stress` lane targeting `stress_level`.

The engine exposes `pitch_value_at_ms()`, `pitch_curve_envelope()`, `stress_value_at_ms()`, and `stress_envelope()` for render, diagnostics, and future animation tracks. Note-event-derived pitch behavior remains lightweight and compatible; Task 079 does not add full vibrato or portamento editing.

## Task 083 Voice Range wording

The main octave control is labeled **Voice Range** because it changes pitch/register rather than loudness. Its labels are musical register descriptors only: contrabass, bass, baritone, tenor, alto, mezzo-soprano, soprano, high soprano, and whistle range. This wording avoids implying physical size, volume, gender, or biological identity while preserving the existing audio behavior.

## Task 084 interval note wheel and preview

The note wheel now defaults to an interval layout that places the home note at the top and moves chromatically around the wheel. The optional circle-of-fifths layout preserves the previous fifths ordering for educational comparison. In both layouts, color and mood are computed from the selected note's interval relationship to the current home note.

The picker can preview the home note, selected note, or interval relationship. Interval preview supports melodic playback (home then selected note) and harmonic playback (both notes together at reduced gain). Preview audio is generated in memory as a short sine tone and is not saved to disk.

The Voice Range label is derived from the current tuned frequency when available, with the octave slider used only as a fallback. The labels remain musical register descriptors and avoid implying gender, body size, or biological identity.

## Task 085 note wheel state synchronization

Visible note wheel dialogs and wave pitch-panel note buttons now refresh from the same current pitch state. Home note changes update interval names, semitone counts, moods, colors, relationship labels, center labels, and tooltips while preserving the selected pitch class.

Displayed spelling remains separate from stored pitch class: Auto, Sharps, and Flats only change visual note names. Preview buttons use the current home and selected pitch classes for audio and current spelling only for labels. Starting a new note-wheel preview replaces any current preview, and closing the dialog stops preview playback when safe. Preview audio remains in memory and is not exported.

Voice Range labels refresh from the current tuned frequency whenever note, octave/range, cents, tuning method, tuning root, or A4 reference changes. Slider-threshold wording remains a fallback and continues to use musical register descriptors only. The Circle of Fifths view intentionally keeps its fixed fifths order rather than rotating around Home.

## Task 086 Harmony Workbench foundation

The pitch tools now include foundational scale and chord helpers. Internal pitch classes remain normalized to sharp names, while user-facing display still respects Auto, Sharps, and Flats spelling. The Harmony Workbench can highlight scale and chord tones on the note wheel without changing the selected pitch class, and its previews use in-memory sine audio only.
