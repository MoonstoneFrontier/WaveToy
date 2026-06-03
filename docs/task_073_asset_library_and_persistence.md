# Task 073 — Asset Library and Persistence

## Goal

Transform WaveToy from a session-only editor toward a persistent speech workstation where user-created artifacts are savable, discoverable, reloadable, and reusable across sessions.

## Implemented foundation

- Added `WaveToyStorage`, a small JSON storage layer that establishes `WaveToyData/` with Projects, Assets, Exports, Cache, and Recovery directories.
- Added `AssetLibraryRecord`, a metadata envelope for all new library assets.
- Added File menu project commands: New Project, Open Project, Save Project, Save Project As, and Recent Projects.
- Added visible project path/status below the global command bar.
- Added five-minute recovery auto-save to `WaveToyData/Recovery/autosave_recovery.wavetoy-project.json`.
- Added startup restore of the last project when enabled.
- Added a Speech Asset Library tab with search, category filter, sort, import, export, refresh, and profile-save controls.
- Mirrored key user-created assets into the persistent library: phonemes, articulation chains, words, profiles, imported wav metadata, generated wav metadata, and animation exports.
- Preserved legacy local files and sidecars for compatibility.

## Scope notes

This patch intentionally keeps the implementation small and reviewable. It establishes durable storage and discovery foundations without changing playback/audio lifecycle logic or replacing existing asset formats.

## Remaining follow-up work

- Add full CRUD dialogs for duplicate/rename/delete/favorite for every library asset type.
- Add a blocking startup recovery prompt with diff/restore/discard options.
- Add dedicated Word Asset and Phrase Asset authoring dialogs.
- Persist and restore timeline audio arrays by safe source rehydration or cache references.
- Add waveform analysis result authoring once the analysis backend exists.
- Add profile-specific duplicate/rename/delete/favorite operations.
