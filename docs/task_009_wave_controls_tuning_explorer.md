# Task 009: Per-Wave Pitch, Tuning Map, and Wave Explorer

## Per-wave pitch model

Wave Toy now keeps the global pitch controls as the default/main pitch source and adds an optional pitch override for each oscillator wave:

- `sine`
- `triangle`
- `sawtooth`
- `square`

Each wave card has a compact pitch area with:

- **👯 Follow Main** enabled by default.
- A note picker for custom **🎯 My Note** mode.
- An octave picker.
- A cents slider for fine tuning from -50 to +50 cents.

When **Follow Main** is on, that wave follows the existing global note, pitch-motion sliders, and tuning behavior. When it is off, that wave uses its own note, octave, and cents value. This lets the four wave shapes form tuned harmonies without changing old presets by default.

The saved `SynthSettings` model includes:

- `wave_note`
- `wave_octave`
- `wave_cents`
- `wave_follow_main_pitch`

Missing fields load with safe defaults equivalent to the old behavior.

## Tuning methods

The default tuning method is `equal_temperament_12`, shown as **Piano Steps**. Equal temperament uses the existing A4-based pitch behavior, so old sounds keep their pitch unless a user chooses another tuning.

The tuning map picker includes these toy-facing methods:

| ID | Toy label | Notes |
| --- | --- | --- |
| `equal_temperament_12` | Piano Steps | Modern 12 equal steps per octave. |
| `just_intonation_major` | Sweet Simple Ratios | Simple major-scale ratios near the selected root. |
| `pythagorean` | Stacked Fifths | Ratios derived from stacked fifths. |
| `quarter_comma_meantone` | Old Keyboard Glow | Historical meantone-style cents map. |
| `werkmeister_iii` | Baroque Adventure | Historical well-temperament-style cents map. |
| `kirnberger_iii` | Old Harpsichord | Historical well-temperament-style cents map. |
| `pentatonic_equal` | Five-Step Playground | Five equal steps mapped from toy note names. |
| `nineteen_equal` | Tiny 19-Step Ladder | 19 equal divisions mapped from chromatic note names. |
| `twenty_four_equal` | Quarter-Tone Sprinkle | 24 equal divisions mapped from chromatic note names. |
| `harmonic_series` | Nature Ladder | Harmonic-ratio-inspired note map. |
| `pelog` | Island Bells | Approximate pelog-inspired cents map, not authoritative. |
| `slendro` | Five Smooth Steps | Approximate slendro-inspired mapping, not authoritative. |

The helper `frequency_for_note(note, octave, cents, tuning_method, root_note, reference_hz)` falls back to 12-tone equal temperament for unknown methods. Cents are applied as a final fine adjustment.

## Wave Explorer popup

The old cramped Wave Overview panel has been replaced by a large toy-style **🌊 Wave Explorer** button. The button opens a non-modal popup window that can stay open while controls change.

The popup:

- Reuses the existing `WaveCanvas` drawing logic.
- Opens at a large default size of about 760 × 520.
- Updates whenever generated audio/wave data changes.
- Includes a status label for sound-picture length and usage hints.
- Leaves room for future composite mix/stereo display hooks without adding duplicate rendering code.

## Playback scrolling implementation

`WaveExplorerWindow` tracks playback with a monotonic start time and the current audio length. A timer updates the `WaveCanvas` zoom center while playback is active. If the canvas is zoomed in, the visible waveform window scrolls approximately with playback position.

This first version is intentionally approximate and time-based. It does not add a sample-accurate callback position, seeking, loop markers, or a full playback controller.

Stopping playback or ending playback stops the scroll timer. Live-loop restarts reset the follow timer for the new render.

## Recipe compatibility

Old recipes still load because missing tuning and per-wave pitch fields fall back to:

- `equal_temperament_12`
- root note `A`
- reference `440.0 Hz`
- all waves following main pitch
- all per-wave custom notes set to A4 with 0 cents

New recipes save the tuning map, tuning root/reference, per-wave pitch controls, and existing Task 008 mute/solo/effect-bypass state when present.

## Task 008 interaction

The existing mute/solo and module-bypass fields are preserved. Per-wave pitch only changes oscillator frequency selection; it does not change whether a wave is muted, soloed, or whether the Paulstretch module is bypassed.

## Remaining limitations

- Custom per-wave pitch is a fixed note for that wave rather than a full per-wave pitch envelope.
- Wave Explorer playback following is approximate and timer-based.
- Historical and cultural tuning maps are simplified toy approximations where noted.
- The popup currently focuses on the existing waveform picture; richer mix/stereo explorer modes can be added later.

## Recommended next task

Add an optional per-wave pitch-motion lane so custom wave notes can glide independently while still preserving the simple **Follow Main** default.
