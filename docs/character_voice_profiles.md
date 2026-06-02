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

## Task 069 resonance mappings

Character presets can now seed both `VoiceBoxState` and `ResonanceTractState` defaults. Direct resonance controls remain editable after preset selection.

- Child: shorter vocal tract, higher head resonance, lower chest resonance.
- Adult Narrator: moderate/high resonance depth and moderate chest resonance.
- Elder: lower/looser resonance depth and lower pharyngeal tension.
- Bright Feminine: shorter vocal tract, higher brightness, higher head resonance.
- Deep Masculine: longer vocal tract, higher chest resonance, higher darkness.
- Breathy: slightly higher nasal coupling and head resonance.
- Raspy: slightly higher darkness plus pharyngeal-tension metadata.
- Robot: neutral/stable formant scale, controlled brightness, low-variation intent.

These mappings are metadata/control defaults only. They do not replace direct phoneme controls and do not implement ML voice cloning.
