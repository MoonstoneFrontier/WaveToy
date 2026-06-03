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
