# Task 025 — Vocal Explorer Canvas Clarity

## Why global scrolling is allowed

The Articulation Lab now treats the vocal-tract drawing as the primary workspace instead of compressing the whole lab into a single above-the-fold view. The tab uses a global vertical scroll area so the Vocal Explorer can keep a tall, readable canvas while articulation controls may continue lower on the page.

This avoids nested scroll conflicts by removing the local scroll wrapper around the articulation controls. Local scrolling remains in the phoneme drawer, where it is useful for long preset and saved-phoneme lists.

## New Vocal Explorer layout

The Vocal Explorer card is organized into three clear zones:

1. **Header row** — current phoneme, IPA badge, and Play/Loop/Stop buttons.
2. **Visual canvas** — mouth, lips, tongue, airflow, nose, and voice indicators only.
3. **Status area** — separate formant and articulation summary strips below the drawing.

The card has a larger fixed minimum height so the canvas remains visually dominant and is not vertically crushed to keep controls onscreen.

## Canvas/status separation

Formant text and articulation summaries are no longer part of the canvas drawing. They live in dedicated status strips below the visual area, preventing text or translucent status bars from crossing the mouth cavity, tongue, airflow, or lip shape.

## Mouth drawing geometry changes

The mouth drawing now uses a centered vocal-tract bounding box with larger top, bottom, left, and right padding. The face, mouth cavity, lips, tongue, airflow, nose, and voice marker are all positioned relative to this stable box.

The geometry emphasizes articulation changes:

- Mouth openness increases the vertical aperture.
- Lip rounding thickens and expands the lip outline while narrowing the mouth.
- Tongue height and frontness move the tongue peak visibly inside the mouth cavity.
- Airflow is drawn as light dashed lines that remain visible without overpowering the mouth.
- Nose and voice indicators remain inside the padded drawing area to reduce clipping risk.

## Remaining limitations

- The Vocal Explorer is still a simplified cartoon visualization rather than an anatomically accurate vocal-tract model.
- Manual checks still require a GUI-capable environment with PySide6 and an available display server.
- Phoneme playback still depends on optional audio backends available in the runtime environment.
