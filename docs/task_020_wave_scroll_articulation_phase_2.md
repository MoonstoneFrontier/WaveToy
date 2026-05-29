# Task 020 — Wave Explorer Playback Scrolling and Articulation Lab Phase 2

## Wave Explorer playback-follow fix

WaveToy now tracks one-shot and loop playback with explicit monotonic-time state instead of relying on canvas painting to infer playback progress:

- `playback_start_monotonic`
- `playback_duration_seconds`
- `playback_audio_sample_count`
- `playback_sample_rate`
- `playback_timer`

Playback tracking starts when WaveToy plays generated audio and advances on a 33 ms timer. The timer updates visible waveform canvases with a playback fraction. When playback reaches the rendered duration, the timer stops and clears the visible playheads. Stop also stops the timer and clears playheads.

The Wave Explorer keeps its own lightweight follow timer so a floating/explorer window can continue to update while audio is playing. Its canvas receives the same duration/sample-count information and scrolls a zoomed view by moving the zoom center toward the current playback fraction. The user zoom factor is not reset by playback start.

## WaveCanvas playback API

`WaveCanvas` now exposes playback-position helpers that can be reused by the Play tab, dashboard, and Wave Explorer:

- `set_playhead_fraction(fraction)`
- `set_playhead_sample(sample_index, sample_count=None)`
- `center_on_playback_fraction(fraction)`
- `center_on_sample(sample_index)`

When the canvas is not zoomed, it can show the moving playhead without changing the view. When zoomed, it preserves the zoom level and shifts the visible slice so the current playback location stays visible.

## Debug logging

Playback debug messages use the prefix:

```text
[WaveToy Playback]
```

Logged events include playback start, audio duration, timer start, Wave Explorer scrolling enablement, stop, and end. Timer ticks are intentionally not logged.

## Articulation Lab Phase 2 consonants

The Articulation Lab now keeps the Phase 1 vowel model and adds toy consonant families:

### Fricatives

Presets: `S`, `Z`, `SH`, `F`, `V`, `H`

Approach:

- Generate a noise source.
- Color/filter the noise based on tongue frontness, lip rounding, teeth gap, and air pressure.
- Add a low voiced component for voiced fricatives such as `Z` and `V`.

### Stops

Presets: `P`, `B`, `T`, `D`, `K`, `G`

Approach:

- Generate a short closure/silence portion.
- Add a short burst of colored noise.
- Add a voiced onset for voiced stops such as `B`, `D`, and `G`.
- Use tongue frontness/noise color to make front and back stops differ.

### Nasals

Presets: `M`, `N`, `NG`

Approach:

- Generate a voiced tone.
- Apply a nasal-style resonant low-frequency envelope.
- Soften upper frequencies to keep the sound humming/nasal rather than bright.

## New articulation controls

The phoneme model and UI now include:

- `🌬 Air Pressure` → `air_pressure`
- `🦷 Teeth Gap` → `teeth_gap`
- `🔒 Closure` → `closure`
- `💥 Burst` → `burst_strength`
- `👃 Nose Open` → `nasal_open`
- `🎤 Voice On` → `voiced`

Saved phoneme JSON includes these fields for new consonant cards. Older vowel cards load safely because missing consonant fields default to vowel-friendly values.

## Vocal Explorer drawing updates

The vocal tract drawing now adds consonant-oriented cues:

- Air stream lines for pressure/noise sounds.
- Closure bar for stop and nasal closures.
- Nose opening indicator for nasals.
- Voice marker when voicing is enabled.

## Limitations

- This is an educational toy model, not realistic speech synthesis.
- Playback tracking is approximate and monotonic-time based; it does not use a sample-accurate audio callback.
- System-player fallback playback may not be stoppable once handed to an external player.
- The WaveCanvas time view is a stylized vertical waveform picture; playback-follow shifts the zoomed visible slice while preserving the existing visual design.

## Next phase recommendation

For Phase 3, add a small phoneme sequence/word timeline that reuses saved phoneme cards as clips, then crossfade between vowel/consonant clips with editable durations.
