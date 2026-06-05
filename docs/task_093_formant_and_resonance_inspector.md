# Task 093 — Formant and Resonance Inspector Foundations

Task 093 extends the Articulation Inspector in Articulation Timeline → Render / Export with speech-specific generated-formant inspection while preserving existing synthesis, render defaults, waveform analysis, export, and playback behavior.

## Metadata model

`FormantAnalysisRecord` is a compact JSON-safe metadata record for future and current `formant_analysis` assets. It stores source references, sample rate, duration, phoneme sequence, frame count, F1/F2/F3 min-mean-max values, bounded vowel-space points, a model-derived resonance summary, a capped speech-frame preview, notes, and timestamps.

The record does not store raw audio arrays, raw waveform samples, or full unbounded formant matrices.

## Analysis helpers

Task 093 adds helper functions for generated/model frame data:

- `formant_summary_from_frames(frames)` computes safe F1/F2/F3 min/mean/max summaries.
- `bounded_formant_frames_preview(frames, max_frames=96)` creates capped JSON-safe speech-frame previews.
- `vowel_space_points_from_formants(frames)` extracts compact F1/F2 plotting points.
- `resonance_summary_from_frames(frames)` summarizes model resonance fields where available and tolerates missing fields.
- `formant_analysis_from_articulation_chain(chain_items, frames, sample_rate)` assembles a compact `FormantAnalysisRecord`.

These helpers consume existing generated formant/resonance frame shapes such as viseme frames and render diagnostics. They do not implement LPC or scientific formant extraction from raw audio.

## Inspector UI

The Articulation Inspector remains in Render / Export and keeps the waveform panel primary. Additional collapsible sections avoid vertical clutter:

- Formants
- Vowel Space
- Resonance
- Speech Frames

The Formants section labels F1/F2/F3 values as generated/resonance-model values, not measured LPC values. The compact `VowelSpaceCanvas` draws F1 vs F2 using PySide painting only and does not add matplotlib, seaborn, or other plotting dependencies.

## Imported audio behavior

Imported WAV/audio sources explicitly report: "No generated formant frames available for imported audio." WaveToy does not pretend imported audio formants have been measured. A future measured-formant option would be a separate task and is out of scope here.

## Storage behavior

The Save Formant Analysis action stores compact `formant_analysis` metadata in the Speech Asset Library. Saved metadata includes source reference/path when available, bounded previews, and model-derived summaries only. It does not store raw audio, full frame arrays, or project-schema migrations.

## Non-goals

- No ML or voice cloning.
- No LPC/measured formant extraction from imported audio.
- No external plotting dependencies.
- No realtime recording.
- No audio engine rewrite.
- No render default changes.
- No project schema changes.
