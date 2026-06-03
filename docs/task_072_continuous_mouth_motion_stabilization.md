# Task 072 — Continuous Mouth Motion Stabilization

Task 072 keeps **Clip Crossfade** as the stable default word render path while improving the opt-in **Continuous Mouth Motion** renderer with waveform-editor diagnostics.

## Regression guard

- The application entry point remains `wave_toy.py`.
- Clip Crossfade remains the default word render mode.
- Continuous Mouth Motion remains opt-in through the Word Render Mode combo.
- Musical Timing and Singing Preview remain default off.
- The waveform diagnostics editor is visual-only: overlays do not change rendered audio or playback routing.

## Continuous stabilization changes

- Oscillator phase remains continuous across frames; pitch updates use the existing glide smoothing control.
- Pitch diagnostics now compare intended pitch against short-window estimated pitch and mark instability regions when the error is high.
- The Continuous limiter uses a softer knee before final peak scaling, reducing harsh saturation while preserving short consonant transients.
- Stop bursts are added after transition smoothing, remain visible in diagnostics, and report:
  - `burst_peak`
  - `burst_rms`
  - `burst_duration_ms`
  - `burst_status`
- Diphthongs remain one timeline item and expose glide labels/regions when their internal vowel motion is active.
- Formant diagnostics expose base F1/F2/F3 and resonance-biased F1/F2/F3. Bypass Formants continues to set Continuous formant intensity to zero.

## Validation chains

Use both Clip Crossfade and Continuous Mouth Motion for these chains:

- `AH`
- `IY`
- `UW`
- `AY`
- `AW`
- `S T AA P`
- `T R IY`
- `N D AH`
- `M AY`
- `B OY`
- `K Y UW`

## Manual audio checklist

For every validation pass, confirm:

1. App launches and the Articulation Lab is reachable.
2. The waveform editor appears in Continuous diagnostics.
3. Existing playback buttons still play rendered audio.
4. Clip Crossfade output has no regression.
5. Continuous output is not silent.
6. Continuous output has no harsh distortion.
7. Pitch motion is stable except intentional consonant/noise regions.
8. Stop bursts remain audible and visible.
9. Diphthongs audibly move between vowel targets.
10. Generated/exported audio files are not staged or committed.
