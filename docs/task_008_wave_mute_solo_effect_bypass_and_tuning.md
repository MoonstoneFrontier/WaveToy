# Task 008 — Wave Mute/Solo, Effect Bypass, and Tuning Picker

## Mute and solo behavior

Each waveform card now has compact toy-style toggles near the Shape stage:

- **🎵 On / 🤫 Quiet** mutes or unmutes that wave without changing loudness, envelope, stereo placement, or timing sliders.
- **⭐ Only Me / 👑 Star Sound** solos one wave at a time. Soloing a wave makes the other waves inaudible but does not erase their mute states.
- **🌈 All Waves** clears the active solo and restores the full mix while still respecting any waves left muted.

Muted cards are dimmed, soloed cards are highlighted, and previews for inaudible waves draw a quiet/off state. The audio engine skips muted waves and skips non-soloed waves when a solo is active, so mute/solo is not implemented by moving sliders.

## Effect bypass behavior

Paulstretch is treated as a small sound module with the toy-style bypass language:

- **✨ Effect On** lets the Paulstretch processor run when its stretch amount is above normal.
- **😴 Effect Nap** bypasses Paulstretch without changing Stretch Amount or Sound Evolution slider values.

The settings model also stores `muted_modules`, so future effects can follow the same pattern: keep their controls intact, then skip processing while their module key is muted/bypassed.

## Toy-style tuning picker

The pitch section includes **🎼 Tuning Playground** with:

- **🎼 Tuning Map** — a toy-name combo box with technical IDs stored internally.
- **Home Note** — the root note used by root-sensitive tuning maps.
- **A4 Sparkle** — the reference A4 pitch in Hz, defaulting to 440.0 Hz.

Equal temperament remains first and default as **Piano Steps** (`equal_temperament_12`). Tooltips include technical descriptions while the visible names stay beginner-friendly.

## Supported tuning methods

- `equal_temperament_12` — **Piano Steps**
- `just_intonation_major` — **Sweet Simple Ratios**
- `pythagorean` — **Stacked Fifths**
- `quarter_comma_meantone` — **Old Keyboard Glow**
- `werkmeister_iii` — **Baroque Adventure**
- `kirnberger_iii` — **Old Harpsichord**
- `pelog` — **Island Bells**
- `slendro` — **Five Smooth Steps**
- `pentatonic_equal` — **Five-Step Playground**
- `nineteen_equal` — **Tiny 19-Step Ladder**
- `twenty_four_equal` — **Quarter-Tone Sprinkle**
- `harmonic_series` — **Nature Ladder**

## Approximation notes

The pelog and slendro options are explicitly approximate, playful mappings for this toy synthesizer. They are not authoritative cultural models. Some historical temperaments are compact cents/ratio maps suitable for a first version rather than full scholarly temperament tables with every spelling distinction.

## Frequency calculation

Pitch conversion is centralized in:

```python
frequency_for_note(note, octave, cents, tuning_method, root_note, reference_hz)
```

The helper keeps `frequency_from_note()` available for standard 12-tone equal temperament. Unknown tuning IDs fall back to equal temperament. The selected tuning is applied to the base note/root/reference pitch, then the cents slider acts as a fine adjustment after the tuning map. The start/end pitch sliders continue to work as continuous equal-ratio sweep controls, scaled relative to the selected base tuning so older pitch-sweep behavior remains predictable.

## Recipe compatibility

Existing recipes without mute, solo, bypass, or tuning fields load with these defaults:

- all waves unmuted,
- no solo wave,
- Paulstretch bypass state inferred from the old checkbox/enabled state,
- `equal_temperament_12`, root `A`, and A4 reference `440.0` Hz.

New recipes save the added state through both the dataclass settings payload and UI fields, including per-wave mute states, solo wave, `muted_modules`, tuning method, root note, and reference Hz.

## Remaining limitations

- Only one solo wave is active at a time.
- Pitch sweep sliders remain continuous equal-ratio controls relative to the tuned base pitch; they do not step through non-equal tuning degrees yet.
- Pelog and slendro are approximate toy mappings.
- Paulstretch is the only current effect/module using the bypass pattern.

## Recommended next task

A good follow-up would add a small effect rack data structure with a shared module row component, then migrate Paulstretch into it before adding more lightweight effects.
