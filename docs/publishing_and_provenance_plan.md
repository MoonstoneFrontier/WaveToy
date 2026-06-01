# Publishing and Provenance Plan

WaveToy outputs can become unique audio, speech, SVG, or animation-prep assets. This plan defines metadata needed for publishing, provenance, and consent-aware attribution without changing current export behavior.

## Metadata fields

- `author`
- `project_name`
- `created_at`
- `app_version`
- `render_hash`
- `source_hashes`
- `license`
- `voice_font_id`
- `export_type`
- `consent_notes`
- `provenance_manifest_version`

## Foundation stubs added in `wave_toy.py`

- `compute_render_hash()` computes a SHA-256 hash for rendered bytes, numpy audio arrays, or simple metadata strings.
- `build_export_provenance_manifest()` builds a sidecar-ready metadata dictionary.

## Publishing direction

- Every exported audio, speech, SVG, or animation package should be able to include a sidecar manifest.
- Voice-font-derived exports should retain consent notes and the originating voice font ID.
- Source hashes should allow projects to identify which recipes, imported audio files, speech assets, and timeline clips contributed to an output.

## Future work

- Wire manifest creation into WAV/MP3/OGG/FLAC/SVG/animation exports.
- Add UI fields for author, project, license, and consent notes.
- Add optional manifest validation before publishing.
- Add project-level metadata persistence.
