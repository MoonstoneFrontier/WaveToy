# Task 039 — Timeline Clip Block Duration Accuracy

## Timeline duration bug

Timeline clip blocks previously used a hard-coded minimum body width of 150 pixels in `TimelineCanvas._clip_rect`. That made short phoneme, syllable, word, and imported-audio clips look much longer than their rendered audio, so visual spacing could disagree with the playhead, ruler, and exported mix timing.

## Coordinate math audit

- Timeline time-to-screen conversion is centralized in `TimelineCanvas._time_to_x(seconds)`.
- Screen-to-time conversion is centralized in `TimelineCanvas._x_to_time(x)`.
- Timeline size uses each clip's `start_time_seconds + duration_seconds` so scrolling grows from true arrangement duration.
- `TimelineClip.duration_seconds` is derived from `len(audio) / sample_rate`; stale metadata durations are not used when clip audio exists.
- Imported audio is decoded/resampled through the existing import path and its palette metadata is informational; timeline clip duration comes from the clip audio and sample rate.
- Timeline mix/export uses `clip.start_time_seconds` and the clip's actual audio length, resampling non-project-rate clip audio before mixdown when necessary.

## True-duration rendering approach

Clip body width now represents true audio duration:

```text
start_x = time_to_x(clip.start_time_seconds)
end_x = time_to_x(clip.start_time_seconds + clip.duration_seconds)
body_width = end_x - start_x
```

The clip's visible body is not padded to make it easier to click. This keeps ruler marks, playhead movement, zoom behavior, and exported audio arrangement on the same time scale.

## Short clip visualization strategy

Very short clips, including 20–100 ms phonemes, keep a true-duration body. When the body is too narrow for text:

- the actual body remains drawn at true duration;
- a small handle and dashed selection/hit halo are drawn for visibility and mouse targeting;
- a duration badge is drawn next to the body rather than widening the body;
- zooming in naturally expands the true body width because the same seconds-per-pixel scale is used.

The hitbox can be wider than the body, but the displayed duration body is not faked.

## Speech clip duration handling

Speech Bin items compute their duration from in-memory rendered audio length. If audio is restored from cache or re-rendered from metadata, the Speech Bin item duration is refreshed from the restored audio. When speech is added to the Timeline, the Timeline clip receives a copy of that rendered audio, and its duration is computed from the clip audio length.

Existing word clips remain historical renders. Changing phoneme duration controls does not silently mutate old clips; newly rendered words can have different durations and will draw at their new rendered length.

## Export and ruler consistency

- Ruler ticks, drag/drop start positions, clip body widths, and playhead x position use the same `seconds_per_pixel` scale.
- Timeline duration is recalculated from each clip start plus true clip duration.
- Mixdown/export allocates the output buffer from the true arrangement end time and places each clip at `clip.start_time_seconds`.
- Arrangement sidecars continue to store clip metadata with actual `duration_seconds`; raw audio arrays are not embedded.

## Debug and inspector visibility

Timeline debug logs include clip duration, sample count, sample rate, visual pixel width, hitbox minimum usage, and arrangement duration recalculation. The inspector now reports actual duration, source type, sample rate, audio sample count, visual width, and speech cache/render details.

## Remaining limitations

- Manual visual verification still requires launching the PySide6 desktop app in an environment with a display/audio stack.
- The short-clip badge can overlap nearby clips when many very short clips are densely stacked at low zoom; zooming in is the intended workflow for detailed editing.
- Speech cache audio is restored or re-rendered when possible, but missing cache plus insufficient metadata still creates a muted warning path rather than inventing audio.
