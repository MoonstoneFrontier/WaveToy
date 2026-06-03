# WaveToy Project System

Task 073 introduces explicit projects as the durable container for a speech workstation session.

## User operations

The File menu now exposes:

- **New Project**: creates a named project under `WaveToyData/Projects/` and clears active timeline/chain session lists.
- **Open Project**: loads a `*.wavetoy-project.json` file.
- **Save Project**: writes the current project snapshot.
- **Save Project As**: writes the snapshot to a user-selected project path.
- **Recent Projects**: repopulates from `WaveToyData/wavetoy_storage.json`.

The active project path is visible below the global command bar.

## Project contents

A project snapshot stores JSON-safe references and metadata for:

- Synthesis settings/recipe metadata.
- Active articulation chain and markers.
- Saved phoneme snapshots available in the project context.
- Voice Source, Voice Box, Resonance, and Character profiles.
- Musical timing settings, note events, pitch curves, and stress markers.
- Timeline lanes, palette metadata, speech bin metadata, clip metadata, and last export paths.
- Window size and active tab index.

## Auto-save and recovery

WaveToy writes a recovery project file every five minutes by default:

```text
WaveToyData/Recovery/autosave_recovery.wavetoy-project.json
```

Startup restore uses `wavetoy_storage.json` to reopen the previous project when enabled. If a recovery file exists, WaveToy logs its path for recovery awareness; the next pass can add a blocking startup prompt once more crash-state UX is validated.
