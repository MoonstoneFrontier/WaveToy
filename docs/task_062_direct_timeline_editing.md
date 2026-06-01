# Task 062 — Direct Timeline Editing and Speech Workstation Foundation

## Direct manipulation workflow

The Visual Speech Timeline is now treated as the primary editing surface for articulation chains:

1. Select or add a phoneme from the Articulation Lab.
2. Add it to the speech timeline.
3. Drag phoneme block bodies horizontally to reorder them.
4. Drag block edges to edit phoneme duration.
5. Drag dashed transition regions to edit boundary duration.
6. Adjust accentuation with the compact selected-phoneme controls when a numeric edit is needed.
7. Create and preview the word using the existing clip crossfade or Continuous Mouth Motion renderers.

The timeline keeps the playhead scrub path separate from block manipulation: the red playhead remains the scrub target, while phoneme bodies and edges are the manipulation targets. Ctrl/Shift + mouse wheel zooms the visible scale, with the existing zoom buttons retained.

## Visual feedback

Direct manipulation uses DAW-style visual feedback:

- Reordering shows an insertion marker plus a translucent ghost block before committing the move on release.
- Duration and transition drags update live value text and tooltip text in milliseconds.
- Selected phoneme blocks receive a stronger outline and contrast glow.
- Transitions remain visually distinct with dashed purple regions showing duration and curve type.

## Accentuation visualization

Accentuation is visible without reading the label:

- Positive accentuation makes blocks taller and adds a brighter upper edge.
- Negative accentuation makes blocks shorter with a subdued top edge.
- Nonzero accentuation displays an accent badge and effective gain marker.
- Hover tooltips include accentuation in dB and the effective linear gain multiplier.

Examples:

- `+6 dB` visibly raises the block and shows an effective gain near `×2.00`.
- `-6 dB` visibly reduces the block and shows an effective gain near `×0.50`.

## Selected component controls

The selected-phoneme inspector is intentionally compact:

- Basic controls stay visible: duration, accentuation, and transition duration.
- Advanced controls are collapsible: voice strength, air pressure, transition curve, and notes about experimental/source parameters elsewhere in the Articulation Lab.
- Direct edits in the timeline still update the inspector through the existing chain refresh path.

## Continuous renderer notes

Timeline edits continue to call the articulation dirty path, which clears cached word-render audio and signatures before refreshing motion and diagnostics views. Accentuation remains part of chain item state and is available to Continuous Mouth Motion timeline segments through the existing `accentuation_db` fields.

Manual regression checks should cover:

- Clip crossfade word rendering.
- Continuous Mouth Motion rendering.
- Cache invalidation after duration, transition, accentuation, and reorder edits.
- Pitch interpolation and burst handling diagnostics.

## SVG future architecture notes

The current implementation remains raster/PySide based. Widgets suitable for future SVG migration:

- `ArticulationTimelineCanvas` for phoneme blocks, transitions, playhead, selection, ghost previews, and insertion markers.
- `ArticulationTrackCanvas` for envelope and formant lanes.
- `WaveformCanvas` and timeline waveform renderer classes for waveform paths and peak previews.

Reusable rendering primitives to preserve for SVG migration:

- Time-to-x scale mapping.
- Rounded phoneme block geometry.
- Transition-region geometry.
- Playhead marker geometry.
- Accentuation-derived height and gain badges.
- Timeline ruler ticks and track labels.
