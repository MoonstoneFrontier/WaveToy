# Continuous Mouth Motion Validation

Continuous Mouth Motion is the primary development renderer for improving connected speech articulation. Clip Crossfade remains the stable user-facing default while Continuous is validated.

## Diagnostic panel

The Articulation Timeline contains a **Continuous Mouth Motion Diagnostics** panel. It updates after every Continuous render and stores the latest diagnostics in a UI-visible dictionary.

Displayed metrics:

- `active_render_mode`
- `output_duration`
- `output_peak`
- `voiced_rms`
- `noise_rms`
- `source_rms`
- `transition_count`
- `transition_duration_total`
- `final_buffer_length`
- `voiced_phoneme_count`

## Status thresholds

- `EMPTY RENDER`: `final_buffer_length == 0`
- `SILENT BUFFER`: `final_buffer_length > 0` and `output_peak <= 0.000001`
- `VOICED PATH MISSING`: voiced phonemes exist and `voiced_rms <= 0.000001`
- `PASS`: `output_peak > 0.001` and a non-empty final buffer exists
- `LOW OUTPUT`: non-empty render below the PASS threshold
- `EXCEPTION`: Continuous raised an exception

Normal diagnostic failures are reported in the panel and terminal debug output rather than modal warnings.

## Validate Continuous

The **Validate Continuous** button renders known built-in chains using Continuous Mouth Motion, then restores the user's previous chain and render mode:

- `M OO N`
- `B AH D`
- `SH IY`
- `TH IH S`
- `S T AA P`
- `D AE D`

Each row reports chain label, duration, peak, voiced RMS, noise RMS, status, and notes. Validation does not create Speech Assets or WAV files.

## Voice profile baseline behavior

Voice profile changes are applied from a captured baseline chain. `Neutral` restores the baseline and clears it. Leaving `Whisper` for another profile restores voiced phonemes before applying the new profile, preventing Whisper from permanently muting the chain. Profile changes mark the word render cache dirty.
