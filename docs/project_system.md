# WaveToy Project System

WaveToy projects are human-readable `.wavetoy-project.json` files stored by default under `WaveToyData/Projects`. Project JSON stores workstation state and references source audio paths, but it does not embed raw audio arrays.

## Saved project state

Projects capture:

- Current synthesizer recipe/settings.
- Active Articulation Chain, selected chain item, render settings, syllable markers, and phrase markers.
- Saved phoneme snapshots.
- Voice Source, Voice Box, Resonance Tract, and Character Voice Profile state.
- Musical timing settings, note events, pitch curves, and stress markers.
- Timeline lanes, snap settings, Audio Assets metadata, Speech Assets metadata, clips, and timeline palette metadata.
- Window metadata including the selected tab.

## Restore behavior

Opening a project restores chain/profile/timing/timeline metadata and switches back to the saved tab when that tab index is available. Imported audio palette items and imported/generated timeline clips are rehydrated from `source_path` when the file still exists. Missing audio sources are represented visibly as muted timeline clips rather than crashing or silently disappearing.

## Dirty state and prompts

Changes to articulation chains, profiles, timing-related state, library assets, and timeline edits mark the project dirty. The window title and project label show an unsaved marker. New Project, Open Project, and Exit prompt the user to save, discard, or cancel when unsaved changes exist. Recovery auto-save does not clear dirty state.

## Recovery workflow

WaveToy writes a recovery JSON file under `WaveToyData/Recovery/autosave_recovery.wavetoy-project.json`. On startup, if that file exists, WaveToy prompts with:

- Restore Recovery
- Ignore This Time
- Delete Recovery

The prompt displays the recovery timestamp and source project path. Restored recovery data is loaded without silently overwriting the current project path, and the user is offered a normal project save location.
