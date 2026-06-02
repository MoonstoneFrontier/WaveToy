# Task 063 — Live Preview, Voice Source, and Workflow Foundations

Task 063 is pinned as the next major workflow-development step for WaveToy. The patch keeps existing speech workflows stable while adding small, reviewable foundations for future voice-source, character, timing, viseme, animation, and CV/VC workflows.

## Implemented foundations

- **Voice Source**: adds `VoiceSourceProfile` as an upstream voice-box/source layer before mouth articulation. It is not ML voice cloning.
- **Character Profile**: adds `CharacterVoiceProfile` and keeps the existing Neutral/Child/Female/Male/Robot/Monster/Whisper dropdown working through an internal legacy profile map.
- **Musical Timing**: adds `MusicalTimingSettings`; millisecond timing remains the default and musical timing is not forced onto speech editing.
- **Live Preview**: adds an optional, default-off Live Preview toggle with a 320 ms debounce and explicit stop-before-preview behavior.
- **CV/VC Library workflow**: Preview, Append to Chain, Replace Chain, and Add to Speech Assets are now real workflow actions. Pattern = All audits both CV and VC for the selected consonant/vowel pair.
- **Continuous tooling**: adds Reset Continuous Tuning and Stop Test workflow buttons while keeping Clip Crossfade as the default render mode.
- **Viseme/Animation export**: adds generic JSON exports derived from the existing phoneme/articulation timeline.
- **Voice Font workflow**: Import Recording now records metadata and provenance intent; Record and Analyze remain disabled placeholders with clear tooltips.

## Non-goals

- No production voice cloning.
- No Blender addon.
- Continuous Mouth Motion is not made default.
- Continuous failures must not silently fall back to Clip Crossfade.
- Generated audio/cache files should not be committed.

## Manual validation checklist

- Live Preview OFF behaves like the prior workflow.
- Live Preview ON previews the selected phoneme or timeline fragment without overlapping playback.
- Reorder chains such as `AH M OO N` in multiple directions and verify debug output includes source/target indexes plus before/after order.
- Preview CV and VC combinations; Pattern = All should include both orders.
- Run Stop Test and inspect terminal diagnostics.
- Export Viseme JSON and Animation JSON with a non-empty articulation chain.
