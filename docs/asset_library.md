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
