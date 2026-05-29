# Task 019 — Articulation Lab Phase 1

## Architecture overview

Phase 1 adds a new `🗣 Articulation Lab` tab between `🌊 Wave Explorer` and `🎬 Timeline`. The existing WaveToy tabs and sound-design workflows remain in place:

1. `🎛 Play`
2. `🌊 Wave Explorer`
3. `🗣 Articulation Lab`
4. `🎬 Timeline`
5. `🧰 Classic Editor`

The new tab is intentionally a toy-like vocal exploration surface. Users move mouth, tongue, lip, pitch, and strength controls instead of editing filter coefficients or low-level DSP parameters.

## Phoneme data model

`ArticulationPhoneme` is a reusable dataclass stored in `wave_toy.py`. It is designed to be small enough for the future Word Timeline to reuse directly.

Fields:

- `name`
- `ipa`
- `mouth_open`
- `tongue_height`
- `tongue_frontness`
- `lip_rounding`
- `voice_pitch`
- `voice_strength`
- `duration_ms`
- `preview_color`

Saved phonemes are JSON files in the repository-local `phonemes/` directory. Each file stores the clamped dataclass values so cards can be loaded, duplicated, renamed, deleted, and eventually placed on a word timeline.

## Vowel preset mappings

The preset buttons use these Phase 1 mappings:

| Preset | IPA | Mouth Open | Tongue Height | Tongue Front | Lip Round |
| --- | --- | ---: | ---: | ---: | ---: |
| 😀 EE | `i` | 0.20 | 0.95 | 0.95 | 0.05 |
| 🙂 EH | `e` | 0.40 | 0.70 | 0.85 | 0.05 |
| 😮 AH | `a` | 0.95 | 0.20 | 0.40 | 0.00 |
| 😯 OH | `o` | 0.55 | 0.50 | 0.20 | 0.60 |
| 😗 OO | `u` | 0.15 | 0.90 | 0.10 | 1.00 |
| 😐 UH | `ə` | 0.45 | 0.45 | 0.50 | 0.10 |

Selecting a preset updates the sliders, redraws the Vocal Explorer, refreshes the Wave Explorer articulation status line, and renders preview audio.

## Vocal Explorer design

The first Vocal Explorer is a simplified cartoon mouth, not an anatomical model. It renders:

- Mouth openness as the vertical mouth opening.
- Tongue height as the tongue indicator moving upward/downward.
- Tongue frontness as the tongue indicator moving forward/back.
- Lip rounding as thicker, rounder lips.
- Approximate F1/F2/F3 readouts for educational feedback.

This visualization is deliberately touch-friendly and large. It avoids realistic anatomy and avoids fluid simulation.

## Audio generation approach

The vowel preview renderer keeps the existing synthesis engine in the loop by creating a short `SynthSettings` patch with simple harmonic wave content and the requested pitch/strength. It then applies a lightweight numpy FFT formant layer:

- F1 is primarily derived from `mouth_open`.
- F2 is primarily derived from `tongue_frontness` and lip rounding.
- F3 is primarily derived from `tongue_height` and lip rounding.

This is intended to produce approximate vowel-like sounds for education and exploration. It is not full speech synthesis.

## Saved phoneme cards

Saved phoneme cards are large, color-coded toy cards with:

- IPA symbol.
- Friendly name.
- Articulation summary.
- Play, Load, Rename, Duplicate, and Delete actions.

Cards are loaded from `phonemes/*.json` when the Articulation Lab is built.

## Future roadmap toward consonants

Future phases can add consonant articulation without changing the Phase 1 vowel model shape:

- Add constriction location and constriction amount.
- Add plosive/fricative/nasal categories.
- Add noise bursts and closure/release envelopes.
- Add tongue-tip and velum controls.
- Add transition rendering between phonemes.

## Future Word Timeline integration

`ArticulationPhoneme` objects are the intended unit for future speech construction:

```text
phoneme card
  ↓
word timeline
  ↓
syllables
  ↓
words
```

The current JSON storage gives future work a simple import path for dragging phoneme cards into syllables or word lanes.

## Phase 1 limitations

- Vowels are approximate and educational, not realistic voice synthesis.
- No consonants are implemented.
- No syllable or word timeline is implemented.
- Preview duration is fixed at 500 ms in the UI foundation.
- The renderer uses a simple numpy formant layer rather than a full vocal-tract model.
