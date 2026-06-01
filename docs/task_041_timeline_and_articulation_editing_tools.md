# Task 041 — Timeline and Articulation Editing Tools

## Time scale model

WaveToy now treats the timeline canvas as a real time surface. `TimelineCanvas.seconds_per_pixel` is the shared visual scale for the ruler, playhead, clip start, clip end, clip body width, trim handles, movement, playback, and export. Clip width is computed from the clip's edited visible duration rather than from a minimum display width.

The Articulation Chain canvas uses a matching duration-based model in milliseconds. Phoneme block widths are derived from `duration_ms`, and transition regions are derived from `transition_to_next_ms`.

## Trim vs. stretch behavior

Timeline clips have explicit non-destructive edit metadata:

- `source_audio_full_length_samples`
- `trim_start_seconds`
- `trim_end_seconds`
- `playback_rate`
- `rendered_duration_seconds`

The Trim Tool changes the in-point or out-point of the clip while keeping the original source audio in memory and, where available, preserving source paths and speech metadata. The Stretch Tool changes `playback_rate` between 0.25x and 4.00x, using simple resampling during timeline mixdown/export for this first version.

## Snap grid

The timeline has a snap toggle and grid size selector with these values: 0.005s, 0.010s, 0.020s, 0.050s, 0.100s, 0.250s, 0.500s, and 1.000s. Clip movement, trim targets, and stretch duration targets use the selected grid when snap is enabled. Turning snap off allows free editing.

## Short clip hitbox strategy

Short clips draw their true-duration bodies. They also receive larger invisible hitboxes plus visible halos/handles so phoneme-length clips remain selectable without visually lying about their duration. At high zoom, the true body naturally becomes wider.

## Articulation Chain timing editor

The Articulation Chain tab keeps the existing sliders and buttons, but the visual chain is now a direct timing editor. Drag phoneme block edges to update `duration_ms`; drag transition regions to update `transition_to_next_ms`. Blocks show duration labels, and transition regions show transition duration and curve labels.

## Split, duplicate, and delete

Timeline shortcuts:

- `V`: Select/Move Tool
- `T`: Trim Tool
- `S`: Stretch Tool
- `Ctrl+B`: Split selected clip at playhead
- `Delete`: Delete selected clip
- `Ctrl+D`: Duplicate selected clip

Splitting creates two clips that reference copied source audio data and compatible metadata while assigning different trim ranges. It does not destructively alter the original source.

## Export behavior

Timeline mixdown/export calls the same render path used by playback. Trimmed clips export only their visible region, stretched clips export at their edited duration, and sidecar JSON stores edit metadata so the visual arrangement can be recovered from clip metadata.

## Known limitations

- Stretching currently uses simple resampling, so pitch changes with playback rate.
- Join-adjacent-compatible-clips is documented as future work.
- Loading timeline arrangement sidecars remains a future workflow; export sidecars preserve the new metadata.
- Full GUI/manual verification requires a host with PySide6's native graphics dependencies available.
