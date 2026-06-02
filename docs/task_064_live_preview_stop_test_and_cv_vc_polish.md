# Task 064 — Live Preview, Stop Test Diagnostics, and CV/VC Polish

## Summary

Task 064 tightens the Task 063 speech-workflow foundations without changing the default rendering mode or adding external animation/voice-cloning dependencies. The patch focuses on diagnostic correctness, safer Live Preview behavior, clearer CV/VC “All” behavior, non-destructive Voice Source application, and generic JSON export validation.

## What was fixed from Task 063

- **Stop Test diagnostics** now report Continuous Mouth Motion burst diagnostics from the latest continuous render instead of labeling the full output peak/RMS as burst values.
- **Live Preview** keeps the existing debounce behavior but skips previews when playback is already busy or the global playback rate limiter refuses a new start.
- **CV/VC Pattern = All** is now labeled as **All: CV + VC** and is treated as both orders across preview, append, replace, and speech-asset creation workflows.
- **Voice Source** remains an upstream render-copy layer. It does not mutate editable phoneme or chain values.
- **Diphthongs** now use an internal vowel-to-vowel articulatory morph for Continuous Mouth Motion and motion/viseme sampling without splitting the phoneme into separate timeline blocks.
- **Viseme and Animation JSON exports** now require a non-empty chain and include generic schema metadata that does not require Blender or any external tool.

## Stop Test field definitions

The Stop Test chains are:

- `B AH`
- `D AH`
- `G AH`
- `P AH`
- `T AH`
- `K AH`
- `D AE D`
- `S T AA P`

Each chain prints a concise diagnostic line and a terminal row. When Continuous diagnostics include true stop-burst data, the row uses:

- `burst_peak`: peak absolute amplitude of the generated stop-burst bus.
- `burst_rms`: RMS level of the generated stop-burst bus.
- `stop_burst_status`: `present`, `low`, or `none` based on burst events and burst-bus level.
- `voiced_rms`: RMS of the voiced excitation bus.
- `noise_rms`: RMS of the noise bus.
- `pitch_error`: percentage error from the Continuous pitch diagnostic.
- `clipped_samples`: final clipped sample count from Continuous diagnostics.

If actual burst diagnostics are unavailable, Stop Test clearly falls back to:

- `output_peak`: full rendered output peak.
- `output_rms`: full rendered output RMS.

The fallback is intentionally **not** labeled as burst data.

## Live Preview skip behavior

Live Preview remains **off by default** and still uses debounce timing for rapid edits. When enabled:

- A busy playback state causes the current preview to be skipped.
- A global playback rate-limit refusal causes the current preview to be skipped.
- The code prints concise debug output with target, selected index, render mode, duration, and skip reason.
- The preview path does not recursively reschedule itself after a refusal.
- Preview rendering does not create Speech Assets.

The intended manual check is to enable Live Preview, edit accentuation or articulation rapidly, and confirm that the terminal shows skips rather than a runaway preview loop.

## CV/VC All behavior

The Pattern selector now labels the combined option as **All: CV + VC**. Its status text says that both `C+V` and `V+C` will be used for the selected pair.

For a selected consonant `B` and vowel `AH`:

- **Preview Combination** auditions both `B AH` and `AH B` as one selected-combination preview.
- **Append to Chain** appends both orders, using a small transition between the pair groups.
- **Replace Chain** replaces the current chain with both orders.
- **Add to Speech Assets** creates clearly named individual assets:
  - `CV B AH`
  - `VC AH B`

The combined option is no longer silently treated as CV only.

## Voice Source non-destructive render-copy behavior

Voice Source remains a foundation layer that maps upstream vocal-source traits onto temporary render copies:

- It does **not** alter editable phoneme slider values.
- It does **not** replace direct phoneme controls.
- It is included in the word-render signature so cache invalidation respects source-profile changes.
- When applied, it logs `profile_id`, `pitch_bias`, `breathiness`, `rasp`, and `glottal_closure`.

This preserves the Task 063 roadmap separation between Voice Source, direct mouth/nose articulation, and future character voice profiles.

## Diphthong transition foundation

Continuous Mouth Motion now treats these diphthongs as internal vowel transitions:

- `AY`: `AH → IY`
- `AW`: `AH → UW`
- `OY`: `AO → IY`
- `OW`: `AO → UW`
- `EY`: `EH → IY`

The internal morph interpolates tongue height, tongue frontness, lip rounding, mouth opening, nasal opening, closure, and airflow/air pressure. Diagnostics include start vowel, end vowel, progress, and interpolation curve. The phoneme remains one timeline item; saved chains do not gain extra phoneme blocks.

## Export validation

Generic Viseme JSON and Animation JSON exports now require a non-empty articulation chain. Empty chains show a user-friendly warning. Exported JSON includes:

- `schema`
- `created_at`
- `phoneme_sequence`
- `duration_ms`
- `render_mode`

No Blender add-on or external animation tool is required.
