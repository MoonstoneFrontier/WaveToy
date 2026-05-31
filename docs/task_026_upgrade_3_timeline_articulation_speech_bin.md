# Task 026 Upgrade 3 — Timeline Articulation Speech Bin

This upgrade keeps phrase building inside the existing **Timeline Storyboard** instead of adding a second phrase timeline. The Timeline already owns clip movement, layering, playback, mixdown, and export, so articulation-created speech units now enter that surface through a dedicated **🗣 Speech Bin** palette.

## Why the existing Timeline is used

Speech phrases are just arranged audio clips once phonemes, chains, syllables, or words are rendered. Reusing Timeline clips lets speech units sit beside generated WaveToy sounds and imported audio, with the same drag/drop, playhead placement, lane layering, playback, and export path. A separate Phrase Builder tab should only be considered later if the Timeline clip model becomes too rigid for word-level editing.

## Speech Bin concept

The Timeline left drawer now contains both the existing **🎧 Audio Palette** and a **🗣 Speech Bin**. Speech Bin cards are large, toy-like cards for created articulation items:

- 🔤 phoneme cards, such as `AH /a/`
- 🔡 syllable cards
- 🧩 word cards
- 🧬 raw articulation-chain cards, such as `M + OO + N`

Each speech card stores metadata fields for its id, name, item type, IPA sequence, display sequence, duration, cache path, articulation snapshot, source mode, and creation time. Raw audio arrays are not embedded in JSON sidecars.

## Create Word to Timeline workflow

1. Shape or choose phonemes in **Articulation Lab**.
2. Add phonemes to the **Articulation Chain**.
3. Press **🧩 Create Word** to render a smoothed word.
4. The rendered word automatically appears in the Timeline **Speech Bin**.
5. Press **➕ Send Word to Timeline**, use the Speech Bin **➕ Add** button, or drag the word card into a Timeline lane.
6. Arrange multiple speech clips in lanes to build a phrase, then play or export the full Timeline mix.

The Articulation Lab also includes buttons for sending the current phoneme or raw chain directly to the Timeline, plus a simple **Create Syllable** action that uses the same smoothed render path as word creation.

## Speech clip source types

Timeline clips now record a source type so sidecars and the inspector can distinguish:

- `generated_wavetoy_sound`
- `imported_audio`
- `articulation_phoneme`
- `articulation_chain_raw`
- `articulation_word_render`
- `articulation_syllable_render`

Speech clips display distinct icons and badges while still behaving like normal Timeline clips. They can be moved, duplicated, deleted, layered with generated/imported clips, mixed, and exported.

## Save/load and cache behavior

Timeline export sidecars include `speech_bin_sources`, `clip_source_types`, and per-clip `speech_metadata`. Speech metadata stores audio cache paths plus articulation snapshots, never raw audio arrays.

When a Speech Bin item is placed on the Timeline, WaveToy first uses in-memory audio, then cached audio if available. If the cache is missing, WaveToy attempts to re-render from the saved articulation metadata. If re-rendering fails, the Timeline still creates a visible muted clip with a warning badge/message so the arrangement remains understandable.

Old Timeline arrangements remain compatible because the new clip metadata is optional and generated WaveToy clips still default to `generated_wavetoy_sound`.

## Fallback Phrase Builder conditions

A dedicated **📝 Phrase Builder** tab is still intentionally deferred. It should only be added if Timeline integration becomes unsafe, the Speech Bin makes the Timeline too crowded, or future speech-specific editing requires a separate clip model.

## Remaining limitations

- Timeline arrangement reload is still not a full workflow; exported sidecars document speech metadata for future reload support.
- Speech cards cache rendered WAV files under `.wavetoy_speech_cache`, so moving the project without those cache files may trigger re-render fallback.
- Word and syllable naming is currently automatic from the chain display sequence.
