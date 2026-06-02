# Export Package Manifest Foundation

This document keeps publishing/provenance work moving without adding publishing UI.

## Package concept

A future WaveToy export package should contain:

- `audio.wav`
- `recipe.json`
- `articulation.json`
- `diagnostics.json`
- `viseme.json`
- `provenance.manifest.json`

## Manifest metadata

`provenance.manifest.json` should include:

- `project_name`
- `author`
- `created_at`
- `app_version`
- `render_mode`
- `render_hash`
- `phoneme_sequence`
- `voice_profile`
- `voice_source_profile`
- `character_profile`
- `musical_timing_settings`
- `source_files`
- `license`
- `consent_notes`

## Draft JSON skeleton

```json
{
  "schema": "wavetoy.export_package_manifest.v1",
  "project_name": "Example WaveToy Render",
  "author": "",
  "created_at": "2026-06-01T00:00:00Z",
  "app_version": "",
  "render_mode": "Clip Crossfade or Continuous Mouth Motion",
  "render_hash": "",
  "phoneme_sequence": [],
  "voice_profile": "Neutral",
  "voice_source_profile": {},
  "character_profile": {},
  "musical_timing_settings": {},
  "source_files": [],
  "license": "",
  "consent_notes": ""
}
```

## Requirements before implementation

- Generated WAV files should not be committed.
- Source-file and consent metadata should be explicit, especially for imported recordings or future voice-font experiments.
- Continuous diagnostics should be included when Continuous Mouth Motion is used.
- Publishing UI is future work and intentionally out of scope for this task.

## Task 063 workflow note

Task 063 starts feeding manifest-ready metadata from rendered speech workflows: render mode, phoneme sequence, legacy voice profile, upstream voice source profile, character profile, musical timing settings, render hash, and consent notes should remain human-readable where practical.
