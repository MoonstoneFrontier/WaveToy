# Task 027 — Speech Bin Workflow Polish

## Overview

This pass polishes the Speech Bin and Articulation-to-Timeline workflow so speech units can be created, named, managed, previewed, placed on a phrase-oriented lane, and exported with compact metadata.

## Articulation Chain cleanup

- Grouped Articulation Chain controls into explicit sections:
  - Chain Editing
  - Render Speech
  - Send to Timeline
  - Save/Load
  - Wave Source
- Emphasized the primary workflow: **Add Current → Create Word → Send Word to Timeline**.
- Kept secondary actions available while making them visually less dominant.
- Changed **Play Word** to render for preview without accidentally creating a new Speech Bin word card.
- **Create Word** now asks for a default chain-derived name and reports success through the inline status label.

## Speech Bin management

Speech Bin cards now support:

- Preview/play
- Rename
- Duplicate
- Add to Timeline
- Delete from Speech Bin
- Context-menu access to the same management actions

The Speech Bin drawer also includes a **Clear Bin** action with confirmation. Removing or clearing Speech Bin source cards does **not** remove existing Timeline clips; Timeline clips keep their copied audio and metadata.

## Timeline phrase building

- Added a speech-focused lane action: **➕ Add Voice Lane**.
- Speech clips default to the first lane named **🗣 Voice Lane** when present.
- If no voice lane exists, speech clips fall back to lane 0.
- The left Timeline drawer now separates reusable imported audio and created speech with **🎧 Audio** and **🗣 Speech** tabs so the two palettes do not visually compete.
- Speech clips retain distinct purple/pink Timeline styling from generated and imported audio clips.

## Inspector and metadata hardening

The Timeline inspector now makes speech clips more explicit by showing:

- Speech type
- Phoneme display sequence
- IPA sequence
- Cache status
- Articulation source mode
- Muted warnings when cache/metadata recovery fails

Export sidecars continue to store compact speech and clip metadata without embedding raw audio arrays.

## Cache behavior

- Speech WAV caches are written under `.wavetoy_speech_cache/`.
- If a Speech Bin item has in-memory audio but a missing cache file, WaveToy rewrites the cache path before placing or previewing it.
- If in-memory audio is unavailable and the cache path is missing, WaveToy attempts to re-render from articulation metadata.
- If re-rendering fails, a visible muted clip can still be created with a warning in the inspector and exported sidecar metadata.

## Verification notes

Required automated syntax check:

```bash
python -m py_compile wave_toy.py
```

Suggested manual checks:

1. Create an M + OO + N chain.
2. Create Word and confirm the name prompt/default.
3. Confirm the word appears selected in Speech Bin.
4. Rename, preview, duplicate, and delete a Speech Bin card.
5. Add Voice Lane and send speech to Timeline.
6. Arrange several speech clips into a phrase.
7. Export Timeline mix and inspect the `.wave-toy-arrangement.json` sidecar.
8. Delete a Speech Bin source after adding it to Timeline and confirm the clip remains.
9. Remove a cache WAV and confirm cache rewrite or metadata re-render fallback.
10. Confirm imported audio and generated WaveToy clips still add and export normally.
