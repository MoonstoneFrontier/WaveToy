# Task 040a: Graphical Wave Toolbar Polish

## Selected card styling

Shape Source Wave now tracks the currently selected graphical wave card with `graphical_selected_wave_id` and applies a dedicated `waveCardSelected` object name. The selected style uses a thicker 5px accent border, a brighter blended background, and a subtle green drop-shadow glow so it wins visually over normal, muted, or solo card styling.

Selection priority is:

1. `waveCardSelected`
2. `waveCardSolo`
3. `waveCardMuted`
4. `waveCard`

This keeps the selected wave obvious after graphical refreshes without adding another audio or recipe state model.

## Full-card selection behavior

A lightweight `GraphicalWaveCard` surface emits the existing graphical wave selection signal when the user clicks empty card/header/body areas. The waveform canvas still emits selection during direct waveform interaction, while toolbar buttons continue to handle their own clicked actions for mute, solo, copy, and remove.

This prepares the card surface for later direct-manipulation interactions while keeping the current button workflow intact.

## Toolbar density changes

Per-wave action labels were shortened to the requested action names:

- `🎵 Mute`
- `⭐ Solo`
- `📄 Copy`
- `🗑 Remove`

The button minimum width was reduced from the previous 118px to 96px to fit more actions per row when many wave layers are visible. Wrapping remains handled by `FlowLayout`.

## Touch target improvements

Per-wave toolbar buttons now use a 48px minimum height, up from the earlier 44px. The shorter labels preserve readability at the denser 96px minimum width while keeping the toolbar usable on desktop and closer to future touch/tablet needs.

## Visual integration improvements

Each wave card now uses a header/body structure:

- The toolbar sits in a card header with matching top radius and a subtle divider.
- The waveform canvas sits in the card body directly below the header.
- The card itself owns the border, selected/muted/solo styling, and full-width visual grouping.

This makes the action toolbar feel like part of the waveform editing surface rather than a separate control strip.

## Future direct-manipulation readiness

The new `GraphicalWaveCard` wrapper is ready to become the event surface for future work such as:

- Dragging cards to reorder wave layers.
- Dragging vertically on card empty space for gain gestures.
- Replacing text buttons with tap-friendly icon targets.
- Long-press or right-click contextual menus.

No gestures were implemented in this task.

## Consistency audit and future recommendations

Audited Graphical Editor sections:

- **Shape Source Wave**: now uses attached wrapping header toolbars and selected-card feedback.
- **Stereo Placement**: no detached action stack; future consistency opportunity is adding an optional header for mode/help actions if stereo editing grows.
- **Pitch Motion**: no detached action stack; future consistency opportunity is a matching header if pitch presets/actions are added.
- **Sound Magic**: preview block grid is visually separate by design; future versions should use card headers if blocks become editable.
- **Vocal Tract Editor**: no detached action stack; full-width canvas remains appropriate.
- **Articulation Chain Editor**: transition curve buttons are horizontal under the timeline, not right-side detached; future polish could move them into a matching timeline-card header for consistency.

No unrelated sections were refactored for this task.
