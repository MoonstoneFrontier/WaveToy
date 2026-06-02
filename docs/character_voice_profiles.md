# Character Voice Profiles

`CharacterVoiceProfile` is a creative delivery layer above phoneme controls. It can point at a `VoiceSourceProfile` and provide defaults for pitch bias, timing bias, and accentuation bias without replacing direct phoneme editing.

The existing dropdown profiles remain available:

- Neutral
- Child
- Female
- Male
- Robot
- Monster
- Whisper

Internally, those legacy profiles now map to character/source identifiers so future patches can migrate behavior gradually while preserving the current UI.

MBTI-style hints should only be broad creative delivery shortcuts, not rigid psychology. For example, an introversion hint might reduce projection and accentuation range, while a perceiving hint might loosen timing. These hints must remain optional and editable.
