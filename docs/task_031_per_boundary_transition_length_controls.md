# Task 031 — Per-Boundary Transition Length Controls

## Purpose

Articulation Chains now expose a large transition-length slider between each adjacent phoneme card. The control makes the boundary timing visible and editable without inserting silence: low values create fast cut-style mouth motion, while high values create smoother/slower coarticulation.

## Per-boundary data model

- Each `ArticulationChainItem` stores the explicit transition duration to the next chain item in `transition_to_next_ms`.
- The value is stored on the left/source item for the boundary.
- The last chain item ignores `transition_to_next_ms` because there is no next phoneme.
- Saved chains still include the legacy `transition_ms` alias for compatibility, and older chains that only contain `transition_ms` continue to load.
- A `null` transition means WaveToy uses the existing family-specific transition rule rather than a custom user value.

## UI behavior

- Transition controls appear only when the chain has at least two phonemes.
- Each boundary control is visually placed between the two cards and labeled as `↔ Transition: FROM → TO`.
- The slider range is 0–250 ms, snapped to 5 ms increments.
- The control displays the current millisecond value and clear `fast`/`smooth` endpoints.
- Moving a slider updates the chain model immediately and marks the current word render dirty so Create Word, Play Word, Export Word, and Word Motion Preview use the new value.

## Gapless render interaction

- Transition sliders control overlap/interpolation length only.
- No silence is added to represent transitions.
- A 0 ms boundary produces an immediate transition/cut-style crossfade path and remains gapless.
- Longer values render a longer interpolated coarticulation clip between the two phoneme shapes.
- Stop closures remain phoneme-internal events and are not replaced by boundary silence.

## Word Motion Preview behavior

- Word Motion Preview reads the same per-boundary transition durations used by Create Word.
- Longer slider values allocate more visual timeline time to the transition region, making mouth interpolation visibly slower.
- The active transition block is highlighted during playback.
- The status line and canvas show the current transition duration while the motion playhead advances.

## Save/load and metadata behavior

- Chain JSON stores `transition_to_next_ms` with each item.
- Speech Bin metadata and Timeline speech clip metadata include the same serialized chain item transition values through the articulation metadata snapshot.
- Word export sidecar JSON includes transition values and continues to avoid embedding raw audio arrays.
- Existing saved chains without transition fields load safely and use family-specific defaults until the user moves a slider.

## Remaining limitations

- Transition values live on the source item, so complex reorder operations preserve the source item's outgoing custom timing rather than trying to infer every possible user intent.
- Slow Motion Visual Only changes visual playback speed but does not time-stretch the rendered audio.
