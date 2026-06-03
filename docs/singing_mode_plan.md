# Singing Preview Plan

Singing Preview is a low-risk bridge from speech synthesis to note-guided vocal experiments.

## Current behavior

- Default OFF.
- Stays inside the collapsed Musical Timing section.
- Uses existing phoneme chains and render infrastructure.
- Creates/uses one simple guide note only when no `NoteEvent` exists.
- Applies pitch targets primarily to vowels.
- Applies partial support only to voiced sonorants: nasals, liquids, and glides.
- Applies only conservative support to voiced fricatives.
- Does not pitch-shift stops, affricates, or unvoiced fricatives.
- Respects the existing VoiceBoxState and ResonanceTractState pipeline by changing render-time phoneme copies rather than replacing the renderer.

## Non-goals

- No ML voice cloning.
- No full Vocaloid-style editor yet.
- No MIDI or Blender dependency.
- No complex vibrato or portamento synthesis yet.
- No change to Clip Crossfade as the default render mode.
- No change to Continuous Mouth Motion being opt-in and quality-priority.

## Future work

- Manual note lane editor if it does not crowd the Articulation Timeline.
- Lyric syllable-to-phoneme assignment.
- Continuous pitch interpolation through voiced segments after validation.
- Better vibrato envelopes and expressive onset/offset controls in a later task.
