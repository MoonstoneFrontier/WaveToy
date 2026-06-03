# Task 074 — Asset Library CRUD and Restore Polish

Task 074 builds on the persistent storage foundation by making the Speech Asset Library practical for everyday use.

## Implemented application behavior

- Replaced the library's plain text listing with a selectable asset table that keeps search, category, and sort controls.
- Added library actions for loading, renaming, duplicating, deleting metadata, toggling favorites, and editing tags/notes.
- Kept asset metadata human-readable JSON and preserved UUIDs when renaming or editing records.
- Duplicates and imported library entries receive fresh UUIDs.
- Loading behavior now covers phonemes, articulation chains, words, voice source profiles, voice box state, resonance profiles, character profiles, and imported/generated WAV records.
- Loading WAV-backed records adds them to Audio Assets when the original source path still exists and warns clearly when it is missing.
- Startup recovery now prompts the user with Restore Recovery, Ignore This Time, and Delete Recovery choices, including recovery timestamp and source project path.
- Project restore now rehydrates imported audio palette entries and timeline clips from source paths where possible, and keeps missing-source clips visible with muted warnings.
- Dirty project state is surfaced in the window title and project label, and New/Open/Exit prompt before discarding unsaved changes.

## Manual verification checklist

- Save a phoneme, restart, then load it from the library table.
- Save an articulation chain, restart, then load it from the library table and confirm replacement.
- Save current profiles, restart, and load each profile asset.
- Rename, duplicate, favorite/unfavorite, edit tags/notes, and delete an asset metadata record.
- Create a recovery file, restart, and verify all three recovery prompt choices.
- Open a saved project and verify tab, chain, voice/resonance/profile, timing, notes/stress, palette, and timeline state.
- Import a WAV, save the project, restart, then verify source rehydration or missing-source warning if the file was moved.
