# WaveToy Asset Library

The persistent Speech Asset Library stores reusable WaveToy records as human-readable JSON under `WaveToyData/Assets`.

## Asset table

The Library tab shows selectable rows with these columns:

- Favorite
- Name
- Asset type
- Modified timestamp
- Tags
- Source path status

Search, category filtering, and sorting remain available above the table.

## CRUD actions

Library buttons support:

- Load
- Rename
- Duplicate
- Delete
- Favorite/Unfavorite
- Tags/Notes
- Refresh, import, export, and save profile snapshots

Rename and tag/note edits preserve the asset UUID. Duplicate and import create new UUIDs. Deleting an asset removes only the library metadata JSON and does not delete source audio files.

## Load actions

Loading a library asset applies the most direct usable workflow:

- `phoneme`: loads/selects the phoneme in Articulation Lab and adds it to saved phoneme choices if needed.
- `articulation_chain`: replaces the current chain after confirmation.
- `word`: restores chain metadata when available.
- `voice_source`, `voice_box`, `resonance_profile`, `character_profile`: apply the corresponding profile/state.
- `imported_wav`, `generated_wav`: add the source file to Audio Assets when the referenced path exists; otherwise WaveToy shows a missing-source warning.

## Metadata rules

Library records retain descriptive fields such as name, tags, notes, favorite status, source path, creation time, modification time, and payload. Raw audio arrays are not embedded in JSON.

## Task 075 performance assets

The Speech Asset Library now recognizes `performance` and `automation_curve` asset types. A performance asset stores the current persistent automation tracks. An automation curve asset stores one selected track and its points. Existing library CRUD operations such as duplicate, rename, delete, favorite, import, and export continue to operate through the shared asset envelope.

Loading a performance asset replaces the current performance tracks with a fresh imported performance UUID. Loading an automation curve appends the imported track with a fresh track UUID.

## Task 087 reserved harmony assets

WaveToy now reserves lightweight JSON-safe shapes for future harmony assets: `scale_pattern`, `chord_pattern`, and `chord_progression`. Each reserved shape carries `uuid`, `name`, `root_note`, `spelling_mode`, `scale_type`, `chord_type`, `chord_steps`, `tags`, `notes`, `created_at`, and `modified_at`.

These foundations do not yet add Asset Library CRUD integration or a project-schema migration. The Harmony Workbench metadata export is separate from audio export and writes only root, scale, chord, pitch-class, displayed-name, spelling, and timestamp metadata.

## Task 088 reserved harmony asset cleanup

Reserved harmony asset dataclasses now share common JSON-safe fields through `HarmonyAssetBase` while preserving the public `ScalePatternAsset`, `ChordPatternAsset`, and `ChordProgressionAsset` class names. This reduces duplication for future scale, chord, and progression assets without implementing Asset Library CRUD, MIDI export, piano roll editing, or a project schema migration.
