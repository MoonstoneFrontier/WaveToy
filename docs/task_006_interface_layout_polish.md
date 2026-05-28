# Task 006: Interface Layout Polish

## Layout changes made

- Renamed the merged wave section to **"1. Mix Wave Shapes and Stereo Placement"** to match the intended workflow.
- Reworked the wave mix/stereo area from one very wide grid into compact per-wave cards.
- Each wave card now keeps the wave label, mini waveform preview, loudness/time sliders, stereo sliders, and L/R preview pair together.
- Split each card into two compact control rows:
  - First row: Start, End, and Time controls.
  - Second row: Place, Spread, and Dance controls.
- Shortened control captions so labels stay close to their sliders and do not stretch the row.
- Reduced group-box margins, padding, and spacing while preserving the rounded playful visual style.
- Moved the explanation panel into the main left column so the center of the interface no longer becomes a large blank area.
- Wrapped the main waveform canvas in a titled **"Wave Overview"** group on the far right.
- Reduced the overview canvas size so it behaves like a persistent side overview instead of occupying the central layout.

## Screenshot-based issues addressed

- The merged wave/stereo section no longer depends on one extremely wide row for every control.
- Sliders are visually attached to their short captions and live picture labels.
- Mini waveform previews are integrated inside each wave card instead of floating in a separate table column.
- Per-ear L/R previews have a dedicated right side area in each card to avoid right-edge clipping.
- The large empty center column was removed.
- The waveform viewport is now in a clear titled container on the far right and uses a smaller fixed size.
- Right-side secondary sections now stack underneath the overview, making the right column feel intentional.

## Remaining layout limitations

- At very narrow window widths, the interface still relies on the scroll area rather than adaptive wrapping.
- The right column can become tall when all modules, stereo controls, and experiment presets are visible.
- The compact wave cards preserve touch-friendly slider handles, so they cannot shrink as much vertically as a mouse-only desktop UI.
- Some emoji labels may render at slightly different widths depending on the installed system font.

## Recommended next task

Run a focused visual QA pass with screenshots at 1280x820 and one smaller fallback size, then tune individual row heights or consider collapsible right-column panels if the lower presets are still too far down the scroll area.
