# Character Voice Profiles

Task 068 starts a bridge from character presets to `VoiceBoxState` mappings without replacing direct phoneme controls.

## Presets

The compact Voice Box panel provides these mapping presets:

- Neutral
- Child
- Adult Narrator
- Elder
- Bright Feminine
- Deep Masculine
- Breathy
- Raspy
- Robot

Each preset updates the current `VoiceBoxState` defaults. Users can still adjust individual voice-box sliders afterward, and direct articulation sliders still control phoneme shaping.

## Legacy profile compatibility

The existing Articulation Timeline legacy voice profile dropdown remains in place. It continues to support Neutral, Child, Female, Male, Robot, Monster, and Whisper mappings while Task 068 adds a separate larynx-layer preset bridge.

## Future relevance

The character bridge is intended to support future voice fonts, singing, timing, accentuation, and expressive delivery. It does not implement ML voice cloning and does not remove direct phoneme editing.
