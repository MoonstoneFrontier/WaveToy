# Speech Asset Library

The Speech Asset Library is the global reusable library independent of any project.

## Categories

The storage foundation creates these categories:

- Phonemes
- CV Combinations
- VC Combinations
- Words
- Phrases
- Voice Sources
- Voice Boxes
- Resonance Profiles
- Character Profiles
- Note Patterns
- Pitch Curves
- Waveform Analyses
- Articulation Chains
- Imported WAV
- Generated WAV
- Animation Exports

## UI

The **Speech Asset Library** tab provides:

- Search across asset name, type, tags, description, and notes.
- Category filtering.
- Sorting by modified date, name, or type.
- Import Library Entry.
- Export Library Entry.
- Save Current Profiles.

## Current save integrations

The following user actions now mirror entries into the persistent library:

- Save Phoneme.
- Save Chain.
- Create Word.
- Export Word.
- Timeline Import Sounds.
- Timeline Export Mix.
- Save generated sound.
- Export Viseme JSON.
- Export Animation JSON.
- Save Current Profiles.

## Articulation chain metadata

Saved chain envelopes include the universal asset metadata plus chain payload metadata. `favorite`, `tags`, and `notes` are present on the envelope; dates are stored as `created_at` and `modified_at`.
