# Task 026 — More Articulations, Fine Clip Timing, and Expandable Waves

## New default articulation presets

The Articulation Lab now includes additional built-in presets while preserving the existing vowel, fricative, stop, and nasal presets.

Added presets:

- **Vowels:** AE `/æ/` cat vowel, IH `/ɪ/` bit vowel, IY `/i/` beet vowel, UH `/ʌ/` cup vowel, ER `/ɝ/` bird vowel.
- **Glides:** W `/w/`, Y `/j/`.
- **Liquids:** L `/l/`, R `/ɹ/`.
- **Affricates:** CH `/tʃ/`, JH `/dʒ/`.
- **Extra Fricatives:** TH `/θ/`, DH `/ð/`, ZH `/ʒ/`.

The drawer rail remains icon-only so the added categories fit in the Articulation Lab sidebar. Saved phoneme JSON loading remains backward compatible because missing articulation fields continue to fall back to safe defaults in `ArticulationPhoneme.from_json_dict()`.

## Smaller timeline and clip timing behavior

WaveToy's generated clip duration control now uses a 0.005-second UI step with a minimum of 0.01 seconds. Generated audio is clamped to at least 0.01 seconds before rendering so zero-length clips are avoided.

Timeline drag placement snaps clip starts to the same 0.005-second timing grid. Timeline mixdown still clamps sample ranges before adding clip audio, so very short clips render/export without producing zero-length slices.

## Dynamic Mix Wave Shapes behavior

Mix Wave Shapes now has a **➕ Add Wave** button. The original four default rows remain in place and cannot be removed. User-added rows can be removed with **➖ Remove** and include practical matching controls:

- waveform shape selection,
- mute and solo,
- start/end level,
- envelope time,
- per-wave pitch follow/custom note controls,
- per-wave stereo pan/width/auto-pan controls.

A soft limit of 12 wave rows prevents runaway UI or render cost. If the user tries to exceed the limit, WaveToy shows a warning instead of adding more rows.

## Stereo Placement synchronization

Each added wave row includes its own stereo placement controls alongside the mix controls. Added waves participate in the same generation path as default waves, including per-wave pan, width, and auto-pan depth. Removing a user-added wave removes its corresponding stereo and pitch controls and clears its mute/solo state.

## Recipe schema migration

Saved recipes remain compatible with the previous fixed `ui.waves` dictionary. New recipes also write `ui.dynamic_wave_entries`, an ordered list containing each wave row's ID, shape, user-added flag, level envelope, stereo placement, mute/solo-compatible state, and pitch settings.

Loading behavior:

1. Old fixed-wave recipes load through the existing `ui.waves` fields.
2. New dynamic recipes recreate user-added wave rows from `ui.dynamic_wave_entries` before applying slider values.
3. The settings object also stores `wave_order` and `wave_shapes` for synthesis/export code paths.
4. Missing fields default safely to existing wave defaults or silence-friendly values.

## Remaining limitations

- The default four wave rows still use their established fixed waveform identity; shape selection is currently exposed for user-added rows.
- The dynamic rows use a more compact card layout than the original four large flow-style rows to keep the existing Classic Editor readable.
- Full audio playback still depends on the user's environment. WaveToy does not require `sounddevice`; when it is absent, existing fallback export/playback behavior is preserved.

## Priority 4b: Waveform Source for Articulation

WaveToy now supports optional waveform sources for Articulation Lab phonemes and Articulation Chain cards. The source modes are Default Voice, Current WaveToy Sound, Selected Mix Wave, and Imported Audio Palette Item. Phoneme and chain metadata stores only source mode, wave id, recipe snapshot, import path, trim/loop/gain options, and timing fields; raw audio arrays are intentionally not written into articulation JSON.

The synthesis path prepares the selected waveform by resampling imported files to the app sample rate, converting to stereo, trimming or looping to the target phoneme duration, adding short fades, and normalizing safely before applying articulation shaping. Vowels use formant filtering, fricatives blend source with filtered noise, stops keep closure/burst behavior with optional voiced source onset, nasals emphasize low nasal resonance, and glides/liquids use approximate formant shaping. Missing imported source paths warn and fall back to Default Voice so old files and portable recipes remain safe.
