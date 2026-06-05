# Task 092 — Waveform Analysis and Articulation Inspector Foundations

Task 092 adds a compact inspection layer for generated and imported speech/audio without changing WaveToy render defaults or audio lifecycle behavior.

## Analysis helpers

The analysis code is centralized in `WaveformAnalysisEngine` and exposed through small module-level helper wrappers in `wave_toy.py`, keeping the analysis engine independent from the inspector UI. The engine uses NumPy only:

- `waveform_peak_series(audio, samples_per_bucket)` returns per-bucket absolute peak envelopes.
- `waveform_rms_series(audio, samples_per_bucket)` returns per-bucket RMS envelopes.
- `zero_crossing_count(audio)` counts mono sign changes for noisy/voiced debugging.
- `estimate_pitch_autocorrelation(audio, sample_rate)` provides a conservative pitch estimate or `None`, with autocorrelation capped to a short analysis window for long audio.
- `short_time_energy(audio, sample_rate, frame_ms, hop_ms)` returns bounded energy summary metadata.
- `simple_spectrogram(audio, sample_rate, frame_ms, hop_ms)` returns a modest uint8-normalized JSON-safe spectrogram preview, not a full matrix.
- `selection_audio_stats(audio, sample_rate, start_seconds, end_seconds)` clamps selection ranges and reports start, end, duration, peak, RMS, DC offset, zero crossings, and estimated pitch.

All helpers accept mono or stereo input, convert stereo to mono where appropriate, handle empty audio safely, and avoid mutating source buffers.

## Articulation Inspector routing

The Articulation Inspector is placed in the Articulation Timeline `Render / Export` workflow, near word rendering but outside the Build tab. Its source selector supports:

1. Current Rendered Word.
2. Current Phoneme Preview.
3. Selected Speech Asset.
4. Selected Imported WAV / Audio Asset.
5. Current Timeline Mix.

The inspector falls back to the current phoneme preview when a preferred source is unavailable. Audio remains in memory only. Inspector cache invalidation uses a stable content hash instead of sum-based signatures.

## Waveform selection behavior

The waveform canvas displays an amplitude envelope, duration labels, optional playhead marker support, zoom controls, fit-to-audio, and drag selection. Selection changes update the statistics panel immediately. A click without a meaningful drag resets to whole-audio stats.

## Pitch estimate limitations

Pitch uses simple autocorrelation for a conservative debugging estimate. It may return `None` for unvoiced consonants, fricatives, plosives, breath noise, very short clips, heavy effects, or mixed/polyphonic material. The UI labels this as a basic estimate and does not claim scientific accuracy.

## Spectrogram limitations

The spectrogram preview uses a modest FFT summary capped to small time and frequency buckets and stores normalized `0..255` preview values to reduce metadata footprint. It is designed to make vowels, fricatives, and plosive bursts visually inspectable enough for debugging while avoiding UI stalls and large project JSON payloads.

## WaveformAnalyses assets

`WaveformAnalysisRecord` serializes compact analysis metadata only and uses the standard `Waveform Analysis - <Source>` asset naming convention: source reference, sample rate, duration, channel count, peak/RMS/DC/zero-crossing metrics, pitch estimate, bounded energy summary, bounded spectrogram summary, selection range, notes, and timestamps. Raw audio arrays are never stored in analysis assets.

## Non-goals

- No ML or neural analysis.
- No voice cloning.
- No realtime recording.
- No external dependencies.
- No audio engine rewrite.
- No render default changes.
- No project schema change.
- No preview audio file saving as part of analysis metadata.

## Task 093 follow-up note

Task 093 extends the same Articulation Inspector with speech-aware formant, vowel-space, resonance, and bounded speech-frame metadata. The waveform inspector remains primary. The new formant data is model-derived from generated articulation/resonance frames, not measured from imported audio, and any saved FormantAnalyses metadata remains bounded and raw-audio-free.
