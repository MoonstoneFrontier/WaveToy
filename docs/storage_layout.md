# WaveToy Storage Layout

WaveToy uses a predictable, cross-platform data root named `WaveToyData`.

## Root selection

1. If `WAVETOY_DATA_DIR` is set, that directory is used. This supports portable/test runs.
2. Windows: `%APPDATA%/WaveToyData`.
3. macOS: `~/Library/Application Support/WaveToyData`.
4. Linux/Unix: `$XDG_DATA_HOME/WaveToyData` or `~/.local/share/WaveToyData`.

## Directory tree

```text
WaveToyData/
  wavetoy_storage.json
  Projects/
  Assets/
    Phonemes/
    Chains/
    Words/
    Phrases/
    VoiceSources/
    VoiceBoxes/
    Resonance/
    Characters/
    CVCombinations/
    VCCombinations/
    NotePatterns/
    PitchCurves/
    WaveformAnalyses/
    ImportedWav/
    GeneratedWav/
    AnimationExports/
  Exports/
  Cache/
  Recovery/
```

## File formats

- Projects use `*.wavetoy-project.json` and contain current workstation state without embedding audio arrays.
- Assets use one JSON envelope per entry. Payloads preserve the existing WaveToy data shape where possible.
- Recovery uses `Recovery/autosave_recovery.wavetoy-project.json` and is refreshed every five minutes by default while the app is running.

## Metadata fields

Every new asset envelope includes:

- `uuid`
- `asset_type`
- `name`
- `description`
- `tags`
- `created_at`
- `modified_at`
- `version`
- `favorite`
- `notes`
- `source_path`
- `payload`
