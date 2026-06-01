# Task 040: Graphical Editor Shape Source Wave Toolbar Layout

## Layout problem

The Graphical Editor's **1. Shape Source Wave** section already had section-level actions above the wave list, but each individual wave layer card placed its related actions in a narrow vertical stack on the right side of the wave graphic. That made the controls feel detached from the waveform representation and reserved a permanent right-side column that the graphic could not use.

## New toolbar placement

The Shape Source Wave section now uses horizontal, wrapping toolbars:

- Section-level actions (`Add Wave Layer`, `Duplicate Loudest Layer`, and `Clear Solo`) are kept in a toolbar directly above the wave layer graphics.
- Per-wave actions (`Mute`, `Solo`, `Duplicate`, and `Remove`) are moved into a toolbar at the top of each wave layer card.
- Each wave graphic is placed below its own action toolbar and can occupy the full card width without a right-side action column.
- Existing callbacks are preserved for add, duplicate, mute, solo, remove, and clear-solo actions.

## Button wrapping behavior

The toolbar layout uses a small FlowLayout helper so buttons stay horizontal when space is available and wrap onto additional rows when the window is narrow. The buttons use consistent spacing, readable labels, and minimum heights of at least 44px. The section-level buttons prefer 52px height, while per-wave card buttons keep a 44px minimum so labels remain legible without shrinking into icon-only controls.

## Consistency check

Other Graphical Editor sections were audited for similar disconnected right-side button stacks:

- **Stereo**: no detached vertical button stack; the section is primarily a single canvas.
- **Pitch**: no detached vertical button stack; the section is primarily a single canvas.
- **Sound Magic**: uses a preview block grid rather than action buttons.
- **Vocal Tract / Articulation**: uses full-width visual canvases; no detached vertical action stack.
- **Articulation Chain**: transition curve buttons are horizontal below the timeline canvas, not a right-side vertical stack.

No other section needed the same low-risk layout change for this task.
