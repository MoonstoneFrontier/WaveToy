# Voice Font Workflow Plan

WaveToy can grow toward a consent-first voice-font workflow without treating voice duplication as production-ready in this foundation task. This plan documents the intended recording and analysis path while preserving the current Articulation Lab, phoneme presets, audio export, and timeline workflows.

## Scope of this foundation

- Add schema and placeholder UI only.
- Do not implement full voice cloning, speech recognition, automatic alignment, or model training.
- Keep all recordings opt-in and tied to explicit author/subject consent.
- Keep generated presets reviewable before they can affect existing articulation presets.

## Proposed workflow

1. **Recording checklist**
   - Confirm the speaker owns or is authorized to use the voice being captured.
   - Record author, project, license, and consent notes.
   - Select sample rate and storage location.
   - Verify that no generated recordings or WAV files are committed to the repository.
2. **Phoneme capture**
   - Prompt the user to record isolated vowels and consonants.
   - Store each prompt with phoneme symbols, IPA, target family, recording path, and analysis status.
3. **Word and phrase capture**
   - Prompt the user to record short words and phrases that expose coarticulation, stop bursts, fricatives, nasal resonance, and vowel transitions.
4. **Analysis review**
   - Produce editable analysis packets for pitch, amplitude, formants, voicing/noise, fricative center, stop timing, nasal resonance, durations, and transition timing.
5. **Preset derivation**
   - Derive candidate `ArticulationPhoneme` values and transition settings.
   - Require user review before saving generated presets.
6. **Voice font export**
   - Export profile metadata, prompt manifest, analysis summaries, generated presets, license, consent notes, and provenance hash.

## Data models added in `wave_toy.py`

- `VoiceFontProfile`
- `VoiceCapturePrompt`

These models are intentionally metadata containers. They do not train or clone a voice.

## Analysis stubs added in `wave_toy.py`

- `analyze_voice_phoneme_recording()`
- `analyze_voice_word_recording()`
- `derive_phoneme_preset_from_analysis()`
- `derive_transition_preset_from_word_context()`

## Future work

- Recording device selector and prompt queue.
- Safe local recording storage and cleanup controls.
- Optional manual phoneme alignment editor.
- Review UI for generated articulation presets.
- Consent-aware export and import validation.
