# WaveToy Storage Audit

Task 073 inventory of user-created object types, current serializers, memory-only gaps, and storage locations.

## Summary

WaveToy now has a persistent storage foundation rooted at `WaveToyData/` (or `WAVETOY_DATA_DIR` when set). Existing legacy files are still respected for compatibility, while new saves mirror assets into the global Speech Asset Library as JSON envelopes.

## Asset inventory

| Asset type | Creation surface | Existing serialization before Task 073 | Memory-only gaps before Task 073 | Current storage location |
| --- | --- | --- | --- | --- |
| Phoneme presets | Articulation Lab Save Phoneme | Individual JSON files in repo-local `phonemes/` | Not discoverable outside that folder; not centralized | Legacy `phonemes/*.json` plus `WaveToyData/Assets/Phonemes/*.json` |
| Articulation chains | Articulation Timeline Save Chain | Single repo-local `articulation_chain.json` | Only one chain reliably available | Legacy `articulation_chain.json` plus `WaveToyData/Assets/Chains/*.json`; project snapshots include the active chain |
| Articulation timelines | Articulation Timeline canvas | Included indirectly in chain items/markers when chain is saved | Active timeline selection/playhead was transient | Project snapshots store chain items, syllable markers, phrase markers, timing settings, note events, pitch curves, and stress markers |
| Voice source profiles | Voice source controls/defaults | Embedded in word render settings and some exports | No standalone library entry | `WaveToyData/Assets/VoiceSources/*.json` through Save Current Profiles; project snapshots include current profile |
| Voice box profiles | Speech Diagnostics voice box controls | Embedded in word render settings and animation exports | No standalone library entry | `WaveToyData/Assets/VoiceBoxes/*.json`; project snapshots include current state |
| Resonance profiles | Resonance controls | Embedded in word render settings and animation exports | No standalone library entry | `WaveToyData/Assets/Resonance/*.json`; project snapshots include current state |
| Character profiles | Character voice profile defaults | Embedded in word render settings and animation exports | No standalone library entry | `WaveToyData/Assets/Characters/*.json`; project snapshots include current profile |
| Note events | Musical timing/singing foundations | Embedded in animation export payloads | Not loaded as project state | Project snapshots store note events |
| Pitch curves | Pitch automation foundations | Embedded in animation export payloads | Not loaded as project state | Project snapshots store pitch curves; library category reserved at `WaveToyData/Assets/PitchCurves/` |
| Stress markers | Syllable stress foundations | Embedded in animation export payloads | Not loaded as project state | Project snapshots store stress markers |
| Waveform analyses | Voice font analysis placeholders / future waveform editor | Planned stub metadata only | No durable library category | Library category reserved at `WaveToyData/Assets/WaveformAnalyses/`; project snapshots reserve analyses through timeline/export metadata |
| Animation exports | Viseme/animation JSON exporters | User-selected JSON files | Not indexed after export | Export path plus `WaveToyData/Assets/AnimationExports/*.json` library envelope |
| Imported wav files | Timeline Import Sounds | Timeline palette memory item; exported arrangement sidecar referenced source path | Palette did not survive restart unless exported externally | `WaveToyData/Assets/ImportedWav/*.json` references source path; project snapshots include palette metadata |
| Generated wav files | Save Sound, Export Word, Export Timeline Mix | Audio file plus sidecar recipe/word/arrangement JSON | Generated assets not centralized | User-selected audio/sidecar plus `WaveToyData/Assets/GeneratedWav/*.json` library envelope |
| Word assets | Create Word / Export Word | Speech Bin memory item; word export sidecar if exported | Speech Bin words did not survive restart | `WaveToyData/Assets/Words/*.json` with phoneme sequence/timing/profile references; project snapshots include speech bin metadata |
| Phrase assets | Future phrase creation | No dedicated serializer | Memory-only/planned | `WaveToyData/Assets/Phrases/` reserved for human-readable JSON |
| CV/VC combinations | Built-in combination library | Built-in generated data; JSON export button exists | User-created combos not yet implemented | `WaveToyData/Assets/CVCombinations/` and `VCCombinations/` reserved |

## Compatibility notes

- Legacy `phonemes/*.json`, `articulation_chain.json`, and `*.wave-toy*.json` sidecars remain readable/writable.
- New library entries wrap payloads with metadata fields: `uuid`, `asset_type`, `name`, `description`, `tags`, `created_at`, `modified_at`, and `version`.
- Raw audio is not embedded in JSON. Audio assets store source/export paths and sidecar metadata to avoid committing/generated binary data.

## Task 092 WaveformAnalyses storage audit

WaveformAnalyses assets are JSON metadata envelopes in the existing Speech Asset Library category. The analysis payload stores bounded summaries only, including reduced-footprint uint8 spectrogram previews, and must not include `audio_data`, `raw_audio`, full waveform sample arrays, or full spectrogram matrices. Source audio remains in memory or in its original referenced asset/path; analysis JSON can remain valid even when the source audio is unavailable.

## Task 093 FormantAnalyses storage audit

FormantAnalyses assets are JSON metadata envelopes for model-derived formant and resonance inspection. They store bounded generated-speech metadata only: phoneme sequence, F1/F2/F3 summaries, compact vowel-space points, model-derived resonance summaries, and a capped speech-frame preview. They must not include `audio_data`, `raw_audio`, raw waveform arrays, or full unbounded formant frame matrices.

Imported WAV/audio sources are explicitly marked unavailable for generated formant frames. WaveToy does not synthesize fake measured formants for imported audio in Task 093; future measured-formant extraction is a separate out-of-scope option.
