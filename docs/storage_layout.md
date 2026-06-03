# WaveToy Storage Layout

WaveToy uses a `WaveToyData` directory. The location can be overridden with `WAVETOY_DATA_DIR` for testing or portable runs.

## Default directories

- `Projects/` — normal `.wavetoy-project.json` project files.
- `Assets/` — reusable asset metadata JSON grouped by type.
- `Exports/` — user-directed export metadata when applicable.
- `Cache/` — generated temporary/support files such as speech-cache WAVs.
- `Recovery/` — auto-save recovery project JSON.
- `wavetoy_storage.json` — global metadata such as recent projects and last project path.

## Asset subdirectories

Asset JSON is grouped into stable subdirectories such as `Phonemes`, `Chains`, `Words`, `VoiceSources`, `VoiceBoxes`, `Resonance`, `Characters`, `ImportedWav`, and `GeneratedWav`.

## Audio persistence policy

Project and asset JSON keep source paths and metadata. They do not embed raw audio arrays. Imported and generated WAV-backed items are reloaded from `source_path` where possible. Missing source paths are reported in the UI and represented as missing/muted metadata rather than causing project load failure.

## Recovery file

The recovery file is `Recovery/autosave_recovery.wavetoy-project.json`. It includes an `autosave` block with `created_at` and `source_project_path` so the startup recovery prompt can explain what is being restored.
