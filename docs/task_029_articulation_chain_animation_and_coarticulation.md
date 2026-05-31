# Task 029: Articulation Chain Animation and Coarticulation

## Word Motion Preview

The Articulation Lab now includes a **🗣 Word Motion Preview** panel under the Articulation Chain controls. It reuses the toy vocal-tract drawing so chain playback can show the mouth moving through the current phoneme, upcoming phoneme, transition percentage, and a small phoneme timeline/playhead.

The preview animates the same articulation dimensions shown by the main canvas:

- mouth openness
- tongue height and frontness
- lip rounding
- nose opening
- closure
- airflow
- voicing indicators

The motion controls are:

- **▶ Play Motion**: animate the mouth/timeline only.
- **🔁 Loop Motion**: repeat the mouth/timeline animation for classroom review.
- **⏹ Stop Motion**: stop the motion timer and request audio stop when sounddevice is active.
- **🐢 Slow Motion**: play the same articulation timeline at a slower educational speed.

`Play Chain` remains the raw comparison path and starts the same motion preview beside its raw concatenated audio. `Play Word` plays the rendered word and starts the same motion preview so the mouth movement stays roughly aligned with the chain timeline.

## Interpolation model

Transitions are modeled as if the articulation sliders physically move from one phoneme snapshot to the next. The interpolation helper creates a new clamped `ArticulationPhoneme` snapshot and does not mutate saved presets or chain items.

Interpolated fields:

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

The boolean `voiced` field remains boolean. Transition audio and animation use the continuous `voice_strength` slider for smoother voiced/unvoiced energy, while the boolean switches at the midpoint of a transition snapshot.

## Smoothstep curve

The default transition curve is smoothstep:

```text
t * t * (3 - 2 * t)
```

This eases in and out of each transition so vowels and glides do not snap between mouth shapes.

## Family-specific transition durations

When a chain boundary does not have an explicit `transition_ms`, the renderer and motion preview use family rules:

| Boundary | Duration |
| --- | ---: |
| vowel → vowel | 70 ms |
| vowel → glide | 60 ms |
| glide → vowel | 70 ms |
| liquid → vowel | 60 ms |
| nasal → vowel | 45 ms |
| fricative/affricate → vowel | 35 ms |
| vowel → fricative/affricate | 35 ms |
| stop → vowel | 12 ms |
| vowel → stop | 18 ms |
| stop → stop | 8 ms |
| default | 35 ms |

Stops keep short transition windows so closure and burst character remain recognizable. Vowels and glides receive longer windows so their visible mouth movement is smoother.

## Coarticulated Word Render

The **Smooth Mouth Transitions** toggle defaults on. When enabled, **🧩 Create Word** uses the coarticulated render path:

1. Render each phoneme clip with its existing synthesis/source behavior.
2. Insert short transition clips between adjacent chain items.
3. Build each transition clip from 5 ms smoothstep-interpolated articulation snapshots.
4. Crossfade into/out of transition clips to avoid abrupt formant and amplitude jumps.
5. Apply boundary smoothing, final edge fades, and normalization.

When the toggle is off, Create Word uses the older simple clip-crossfade path for comparison. The status label reports either **Using smooth slider transitions** or **Using simple clip crossfades**.

## Current limitations

- This remains a toy articulation renderer, not realistic speech synthesis.
- The first-pass coarticulation path inserts interpolated transition clips between rendered phoneme clips rather than driving every sample from one continuous articulatory synthesizer.
- `Play Word` and `Play Chain` start the motion preview from the same chain timeline; synchronization is approximate when audio output falls back to an external system player.
- Per-boundary transition durations are serialized as `transition_ms`, but there is not yet a dedicated UI editor for that value.

## Future roadmap

- Replace transition-clip insertion with a fully continuous articulation envelope sampled across the entire word.
- Expose per-boundary transition duration controls in the chain card editor.
- Add a more detailed vocal-tract side view for tongue constriction and nasal coupling.
- Add educational overlays that compare raw Play Chain boundaries against smooth Create Word transitions.
