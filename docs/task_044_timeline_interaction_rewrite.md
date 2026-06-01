# Task 044 — Timeline Interaction Rewrite

## Click vs. drag model

The Timeline now follows standard DAW/video-editor interaction rules:

- **Click** selects a clip only.
- **Click and hold** creates a pending edit candidate.
- **Drag past the platform drag threshold** starts a move, trim, or Time Stretch edit.
- **Mouse release** commits an active edit and immediately returns the Timeline to idle.
- **Mouse movement after release** does not mutate clip geometry.

This prevents the previous stuck-edit behavior where clip timing could continue changing after a click/release interaction.

## Interaction state machine

`TimelineCanvas` now tracks an explicit interaction state:

- `idle` — hover only; no geometry edits.
- `pressed` — a clip and candidate operation are known, but the drag threshold has not been crossed; no geometry edits.
- `dragging` — left button is held and clip start/lane may update.
- `trimming` — left button is held and trim start/end may update.
- `stretching` — left button is held and Time Stretch duration metadata may update.
- `box_selecting` — reserved for future multi-select behavior; not implemented in this focused pass.

The state is reset to `idle` on release, Escape cancellation, stale no-button motion, leave/focus safety cleanup, and window deactivation handling.

## Drag threshold behavior

On mouse press the canvas stores:

- press position;
- candidate clip id;
- candidate operation;
- original start time;
- original lane;
- original trim start/end;
- original playback-rate duration scale;
- original visible duration;
- stretch cache state.

No clip geometry is changed until the pointer movement exceeds `QApplication.startDragDistance()` while the left mouse button remains held.

## Mouse button guard

`mouseMoveEvent` now begins with a stale-drag guard. If the canvas has an active `drag_clip_id` but the left mouse button is no longer held, it calls `_cancel_or_end_drag(commit=False)` and returns before any clip geometry can change.

This guard applies to move, trim-left, trim-right, stretch-left, and stretch-right edits.

## Escape cancel behavior

Pressing Escape while pressed, dragging, trimming, or stretching restores the original snapshot and clears all interaction state. Escape does not delete the selected clip.

The status message is:

```text
Edit cancelled
```

## Status and debug logging

Concise status messages are used for user feedback:

- Clip selected
- Move clip
- Trim clip start
- Trim clip end
- Time stretch clip
- Edit committed
- Edit cancelled

Discrete interaction events log with the `[WaveToy Timeline Interaction]` prefix:

- `mouse_press_candidate`
- `drag_threshold_crossed`
- `edit_started`
- `edit_committed`
- `edit_cancelled`
- `stale_drag_state_cleared`
- `mouse_move_ignored_no_button`

Per-mouse-move logging is intentionally avoided.

## Time Stretch regression notes

Task 043 pitch-preserving Time Stretch remains intact. Stretch ratio changes only during a held-button drag after the threshold is crossed. Releasing the mouse commits the stretch and clears the active drag state. The inspector continues to report stretch ratio, pitch preservation, rendered duration, and the stretch algorithm.

## Manual verification results

Runtime GUI verification could not be completed in the current container because PySide6 cannot load without the system `libGL.so.1` dependency. The interaction rewrite was verified by code review and syntax checks, and should be manually checked in a desktop environment with Qt/OpenGL dependencies installed.
