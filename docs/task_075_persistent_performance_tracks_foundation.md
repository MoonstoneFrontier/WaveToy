# Task 075 — Persistent Performance Tracks and Automation Foundations

Task 075 adds the first persistent performance layer on top of the project and Speech Asset Library foundation from Tasks 073 and 074.

## Scope

- Adds JSON-safe models for `PerformanceAsset`, `AutomationTrack`, and `AutomationPoint`.
- Persists automation tracks in project snapshots and autosave recovery files.
- Adds `performance` and `automation_curve` asset types to the Speech Asset Library.
- Adds a simple **Performance** tab with editable track and point tables.
- Applies `accentuation_db` automation non-destructively during word render.

## Deliberate limits

This is not a DAW automation editor. It intentionally avoids a complex curve canvas, destructive chain mutation, ML voice cloning, or broad playback lifecycle changes.

## Verification focus

Manual verification should cover creating a track, adding a point, saving a project, reopening it, saving/loading a performance asset, and confirming the dirty project marker changes after automation edits.
