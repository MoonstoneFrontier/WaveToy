# Task 067 — Anatomical Speech Organ Model and Visualization Foundations

## Goal

Create a normalized anatomical speech-organ model and SVG visualization foundations that can support animation, diagnostics, generic JSON export, and future rig workflows without changing audio behavior or saved-chain data.

## Implemented foundations

- Added `SpeechOrganState` as the render-only anatomical source of truth.
- Added SVG builders for the anatomical mouth, vocal tract side-cutaway, airflow particles, and voice-source readout.
- Added a Simple/Anatomical display mode for the Articulation Lab mouth preview.
- Added an optional collapsed vocal-tract side-cutaway in the Word Motion Preview.
- Added a hidden-by-default, dockable read-only Speech Diagnostics panel available from the View menu.
- Updated viseme generation to derive viseme labels from `SpeechOrganState` while retaining a phoneme compatibility function.
- Extended generic animation JSON with `speech_organ_state_frames`, `viseme_frames`, `phoneme_frames`, and `timing_frames`.

## Not changed

- Saved articulation-chain format is unchanged.
- Existing simple visualization remains available.
- Audio synthesis and playback lifecycle logic are unchanged.
- No Blender dependency was added.
- No ML voice cloning was implemented.
- Continuous Mouth Motion remains a selectable/validated mode, not the default.

## Manual verification checklist

- Play AH and observe jaw opening.
- Play OO/UW and observe lip rounding.
- Play M and observe nasal airflow.
- Play T and observe closure/burst.
- Play AY and observe tongue movement.
- Scrub the Visual Speech Timeline and verify anatomy updates.
- Verify Continuous Mouth Motion remains functional.

## Future roadmap

- Task 068: voice-font capture workflow.
- Task 069: Blender rig export using the generic JSON state frames.
- Task 070: musical timing and singing.
- Task 071: emotion and character profile integration.
