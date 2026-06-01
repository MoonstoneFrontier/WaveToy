# Task 043 — Pitch-Preserving Timeline Stretch

## Problem

The Timeline stretch edit path used `TimelineClip.playback_rate` as a direct sample playback-speed control during mix/export. When a clip was stretched longer, the renderer generated more samples by resampling the clip more slowly, which lowered pitch. When a clip was shortened, the renderer resampled faster, which raised pitch.

That behavior is a speed change, not a time stretch.

## Resampling vs. time-stretching

- **Resampling / playback-rate change** changes duration and pitch together because it effectively plays the same waveform cycles at a different speed.
- **Time-stretching** changes duration while keeping the original sample rate and preserving the perceived pitch as much as practical.

Timeline Stretch should be a time-duration edit. It should not destructively modify imported audio, generated WaveToy clips, or rendered speech assets, and it should not retune voices or melodies by default.

## Metadata model

`TimelineClip.playback_rate` is retained for compatibility and editing math, but its practical meaning is now **duration scaling metadata**. It determines the visible target duration:

```text
visible duration = trimmed source duration / playback_rate
stretch ratio = visible duration / trimmed source duration
```

New clip metadata clarifies the default rendering behavior:

- `stretch_mode = "preserve_pitch"`
- `stretch_algorithm = "numpy_phase_vocoder"`
- `pitch_preserve_enabled = true`
- `stretch_ratio` is exported with clip metadata.

## Render pipeline

Timeline playback, mixdown, and export now use this order:

1. Source clip audio.
2. Trim start/end.
3. Convert source sample rate to the Timeline sample rate if needed.
4. Pitch-preserving time stretch to the visible Timeline duration.
5. Mix into the Timeline arrangement.
6. Export/playback the rendered arrangement.

This keeps the visible clip width, rendered clip duration, and exported duration aligned.

## Algorithm used

The default helper is:

```python
time_stretch_preserve_pitch(audio, source_rate, target_duration_seconds)
```

It is implemented with numpy only:

- stereo-safe float32 input/output;
- phase-vocoder style short-time Fourier transform processing for normal clips;
- overlap-add fallback for very short clips;
- edge fades to reduce clicks;
- output length fitting so rendered audio matches the visible Timeline duration.

A **Stretch Quality** selector controls FFT size tradeoffs:

- Fast;
- Balanced (default);
- Best available.

## Inspector and UI language

The Timeline toolbar now labels the stretch edit as **Time Stretch**. The inspector reports:

- source duration;
- trimmed duration;
- stretched duration;
- rendered duration;
- stretch ratio;
- whether pitch preservation is enabled;
- stretch algorithm.

Clip badges use duration-ratio language rather than "playback rate" language.

## Debug logging

Each clip render logs with the `[WaveToy Stretch]` prefix and includes:

- clip id;
- source duration;
- trim duration;
- target duration;
- stretch ratio;
- algorithm;
- output duration;
- pitch-preserve state.

## Known audio-quality limitations

- This is a lightweight numpy implementation, not a studio-grade elastique/rubberband engine.
- Extreme stretch ratios can create transient smearing or robotic artifacts.
- Very short clips use a simple overlap-add fallback because there is not enough material for stable phase-vocoder analysis.
- Timeline stretching of rendered speech assets preserves pitch, but it is not articulation-aware retiming; future work could re-render speech from phoneme timing metadata for higher quality.
