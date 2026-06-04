# Task 082 — Performance Timeline Undo/Redo QA

Task 082 hardens the Task 081 Performance Timeline undo/redo transaction system with stress-oriented regression coverage, manual QA guidance, and small stale-selection protection. The undo/redo stacks remain runtime-only and no project schema fields are added.

## Manual QA checklist

Use a normal desktop session for the checks below; do not stage generated WAV/cache output.

1. Launch WaveToy and open the **Performance Timeline** tab.
2. Add an automation track, add several points, and drag one point continuously for at least 10 seconds.
3. Confirm the drag creates one **Move Point** undo entry for the single drag gesture.
4. Undo and redo the drag, then repeat with roughly 20 drag gestures.
5. Confirm there are no duplicate stress or pitch bridge lanes, no stale selected point index, and no crashes.
6. Create at least 60 timeline edits and confirm only the newest `performance_undo_stack_limit` transactions remain undoable.
7. Undo a few edits, make a new edit, and confirm the redo stack clears and menu labels update.
8. Edit stress bridge and pitch bridge points, then undo/redo and confirm `syllable_stress_markers` and `pitch_automation_points` update through their regenerated bridge lanes.
9. Confirm bridge lanes cannot be deleted directly from the track delete action; delete the source stress/pitch data instead.
10. Rapidly change BPM and confirm the rapid changes coalesce into one undo entry.
11. Wait longer than the timing coalescing window, change BPM again, and confirm a new undo entry appears.
12. Undo/redo timing changes and confirm timing controls update without creating recursive transactions.
13. Save a project, restart the app, reopen it, and confirm undo/redo stacks are empty while timeline state persists.
14. Render a word after undo/redo and confirm `accentuation_db` and `pitch_bias_cents` automation still affect rendering.
15. Confirm undo/redo invalidates the render/cache state, waveform overlay refreshes, and Speech Diagnostics reflects the restored timeline state.

## Stack limit behavior

The main window keeps bounded runtime stacks: `performance_undo_stack` and `performance_redo_stack`. `performance_undo_stack_limit` defaults to 50 transactions. When new edits exceed that limit, the oldest undo transactions are evicted and the newest transactions are retained. A new transaction always clears the redo stack, including after a partial undo sequence.

## Bridge restore behavior

Stress and pitch bridge lanes are derived lanes. Undo/redo snapshot restore deduplicates by `track_id`, separates bridge lanes from normal tracks, writes bridge point edits back to `syllable_stress_markers` or `pitch_automation_points`, restores normal tracks, and regenerates bridge lanes once from the source lists. This keeps bridge lanes from duplicating while preserving bridge edits captured in a transaction.

Bridge lanes remain protected from direct deletion in the track-delete path because they are projections of source data. Remove or edit the source stress markers or pitch automation points instead.

## Timing coalescing behavior

Rapid musical timing changes with the **Musical Timing Change** label coalesce within the configured window. The first transaction keeps the original `before_state`; subsequent rapid changes replace only `after_state`, so one undo returns to the value before the rapid edit sequence. Timing changes after the window produce a new undo entry.

Undo/redo restoration refreshes timing controls with blocked widget signals and a restoration guard so UI updates do not recursively create new timing transactions.

## Reload behavior

Undo/redo stacks are runtime-only. Project saves persist the timeline and musical timing state, but not transaction stacks. Loading or reopening a project starts with empty undo/redo stacks, preventing undo from reaching back into a previous app session.

## Known limitations

- Manual drag stress testing still requires an interactive GUI session; automated coverage exercises the transaction and bridge restore logic headlessly.
- Runtime selection is restored only when the selected track and point still exist. Point indices are clamped to the restored track length when possible.
- Bridge restore updates existing source-list entries; it does not create new stress markers or pitch points from extra bridge points.
- `pitch_bias_cents` rendering still uses the existing conservative post-render voiced-region approximation rather than a new audio engine path.
