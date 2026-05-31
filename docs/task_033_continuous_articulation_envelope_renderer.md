# Task 033 — Continuous Articulation Envelope Renderer

## Why clip crossfade is insufficient

Task 032 removed the worst transition bug by ensuring per-boundary transition lengths do not create standalone buzz or silence regions. That renderer still treats each phoneme as a complete audio clip and overlaps the clip edges. Overlap crossfade is useful as a safe fallback, but it can still sound segmented because each phoneme has its own attack, release, source phase, noise seed, and formant snapshot.

Task 033 prototypes a second Create Word render mode, **Continuous Mouth Motion**, that builds one shared time-indexed articulator envelope and renders one continuous audio stream from that envelope.

## Render mode selector

The Articulation Chain panel now includes a **Word Render Mode** selector with two choices:

- **Clip Crossfade** — the Task 032 overlap/crossfade fallback remains available for comparison and recovery.
- **Continuous Mouth Motion** — the new prototype default, using the shared articulation envelope.

The selected mode is stored in word render settings metadata and appears in status/debug output.

## Envelope data model

The shared envelope timeline is built from the editable articulation chain. For each chain card, the phoneme `duration_ms` becomes a hold region. For each boundary, `transition_to_next_ms` becomes a morph region after the hold. Transition regions use smoothstep interpolation and do not insert silence.

Interpolated articulator fields are:

- `mouth_open`
- `tongue_height`
- `tongue_frontness`
- `lip_rounding`
- `voice_strength`
- `air_pressure`
- `teeth_gap`
- `closure`
- `burst_strength`
- `nasal_open`

`voiced` remains a phoneme-level boolean, but rendering converts it into a continuous `voiced_gain` by interpolating the effective voice gain at transitions. This lets unvoiced fricatives fade down while vowel tone fades up, and lets voiced fricatives maintain tone continuity into vowels.

## Continuous render pipeline

Continuous Mouth Motion renders the word in 5 ms frames from the shared envelope instead of rendering independent full phoneme clips. The renderer:

1. Builds hold and transition segments for the whole word.
2. Samples the envelope at frame centers.
3. Generates a continuous voiced oscillator with phase carried from frame to frame.
4. Generates a continuous noise source controlled by air pressure, teeth gap, and fricative/noise gain.
5. Shapes each frame with mouth/tongue/lip-derived formant emphasis.
6. Adds nasal low-frequency emphasis when `nasal_open` is high.
7. Smooths the final stream and applies safe edge fades/normalization.

The prototype prints debug lines with the `[WaveToy Envelope]` prefix for render mode, phoneme count, total envelope duration, frame count, transition boundaries, stop events, burst events, max voiced/noise/closure values, and final rendered duration.

## Stop and burst handling

Stops are not treated as ordinary interpolation only. The envelope builder records explicit stop closure events during stop holds and burst events near the end of stop holds. During continuous rendering, closure strongly gates tone/noise as intentional near-silence inside the stop, while the burst is added as a short noise event at release.

For stop-to-vowel cases, the transition region starts immediately after the stop hold/burst. The transition slider affects the following articulator morph duration rather than adding a post-burst gap.

## Fricative/vowel smoothing

Fricative-to-vowel transitions interpolate noise and voiced gains independently:

- S/SH/F/H to vowel: turbulent noise fades down while voiced/formant tone fades up.
- Z/V to vowel: voiced gain stays continuous while noise decreases.
- Air Pressure remains the control for noise energy across the envelope.
- Voice Strength remains the control for voiced-tone energy across the envelope.

This avoids filling transitions with a generic buzzing segment.

## Shared Word Motion timeline

Word Motion Preview now uses the same hold-plus-transition envelope timeline as the continuous renderer. Hold regions and transition morph zones share the same timing model, so active phoneme highlighting and mouth motion follow the render timeline. Transition zones are represented as morph zones rather than gaps.

## Fallback behavior

Clip Crossfade remains in the code and can be selected directly. If Continuous Mouth Motion raises an exception or produces empty audio, Create Word prints a warning, shows a warning dialog, and falls back to Clip Crossfade.

## Remaining limitations

- This is a prototype toy renderer, not realistic speech synthesis.
- Continuous Mouth Motion currently uses the internal oscillator/noise excitation path; custom WaveToy/imported phoneme sources are still best compared through Clip Crossfade.
- Frame-wise spectral shaping is intentionally lightweight and dependency-free, so formant motion is approximate.
- Manual listening checks are still needed for perceptual tuning of individual consonant/vowel combinations.
