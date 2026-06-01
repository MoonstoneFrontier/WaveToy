# Task 037: Fix Graphical Editor Startup Crash With Empty Chain

## Root cause

The Graphical Editor refresh path evaluated `0 <= self.articulation_selected_chain_index` even when `articulation_selected_chain_index` was `None`. At startup, or after clearing the Articulation Chain, there may be no selected chain item, so comparing `None` with integers raised:

```text
TypeError: '<=' not supported between instances of 'int' and 'NoneType'
```

## Fix

- `_refresh_graphical_chain_editor` now copies the selected index into a local variable and validates it with `isinstance(selected_index, int)` before doing range checks.
- Invalid, missing, or out-of-range selections are normalized to `selected = None`.
- The graphical chain mouth preview falls back to the current phoneme when there is no valid selected chain item.
- `_graphical_set_selected_chain_curve` uses the same `None`-safe selected-index guard before mutating a chain item.
- `ArticulationTimelineCanvas` now accepts `set_items(items, selected_index)` from the Graphical Editor and tracks a safe selected index for rendering.

## Empty state

When the graphical chain editor has no items, it renders this empty-state message instead of drawing an apparently selectable chain or crashing:

> No articulation chain yet. Add phonemes from Articulation Lab, then return here to arrange them visually.

## Verification

- `python -m py_compile wave_toy.py`
- Startup smoke check with `QT_QPA_PLATFORM=offscreen timeout 5s python wave_toy.py`

Manual interaction should confirm the Graphical Editor opens with an empty chain, adding/removing phonemes refreshes safely, and clearing the chain returns to the empty state.
