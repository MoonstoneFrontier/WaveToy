# Task 089 — Harmony Analysis Engine

Task 089 extends the Task 088 interval descriptor idea into reusable scale and chord descriptors. The goal is educational Harmony Workbench analysis: explain scale tones, chord tones, rough stability/tension/brightness, simple roman numerals, and broad harmonic function without adding a progression editor, MIDI layer, schema migration, or audio export.

## ScaleDescriptor fields

`scale_descriptor(root_note, scale_type, spelling_mode="Auto")` returns a JSON-safe `ScaleDescriptor` dataclass with:

- `root_note` and `root_display`
- `scale_type` and `scale_label`
- `pitch_classes` normalized to WaveToy sharp pitch classes
- `displayed_names` respecting Auto/Sharps/Flats spelling
- `degrees` starting at 1
- `interval_roles` from `interval_descriptor()` for every scale tone
- `mood_label` and `description` from `SCALE_TYPES`
- `stability_score`, `brightness_score`, and `tension_score`

Unknown scale IDs fall back to Major so the helper remains deterministic and safe for UI refreshes.

## ChordDescriptor fields

`chord_descriptor(root_note, chord_type, key_root_note=None, scale_type="major", spelling_mode="Auto")` returns a JSON-safe `ChordDescriptor` dataclass with:

- `root_note` and `root_display`
- `chord_type` and `chord_label`
- `pitch_classes` normalized to WaveToy sharp pitch classes
- `displayed_names` respecting Auto/Sharps/Flats spelling
- `degrees` such as 1, 3, 5, 7, and suspended degrees where applicable
- `interval_roles` from `interval_descriptor()` for every chord tone
- `chord_quality`: major, minor, diminished, augmented, suspended, dominant, power, or extended_or_other
- `roman_numeral` relative to the supplied key root, when available
- `harmonic_function`: tonic, predominant, dominant, color, tonic/color, dominant/tension, dominant/color, predominant/tension, or chromatic
- `stability_score`, `brightness_score`, and `tension_score`
- `description` from `CHORD_TYPES`

Unknown chord IDs fall back to Major Triad.

## Roman numeral limitations

`roman_numeral_for_chord(root_note, chord_type, key_root_note, scale_type="major")` intentionally performs only lightweight educational labeling. It supports diatonic roots in Major and Natural Minor, including triads and seventh-type suffixes such as `V7`.

Current limitations are deliberate:

- No inversions or slash chords.
- No secondary dominants.
- No borrowed-chord analysis.
- No modulation analysis.
- No full chord progression editor.
- No MIDI export.

Non-diatonic roots return `chromatic`.

## Harmonic function categories

`harmonic_function_for_degree(degree, scale_type="major")` maps scale degrees to simple teaching labels:

- Major: I tonic, ii predominant, iii color, IV predominant, V dominant, vi tonic/color, vii° dominant/tension.
- Natural minor: i tonic, ii° predominant/tension, III color, iv predominant, v/V dominant, VI color, VII dominant/color.

These labels are concise UI categories, not a complete classical analysis model.

## Heuristic score meaning

Descriptor scores are floats from 0.0 to 1.0 for visual/UX use only. They are not formal analysis.

- `stability_score` is higher for roots, perfect fifths, power/open sonorities, and major/minor triads.
- `brightness_score` is higher for major thirds, major sixths, major sevenths, and augmented color.
- `tension_score` is higher for tritones, diminished color, major sevenths, dominant sevenths, and chromatic chord roots.

## Harmony Workbench UI and export

The Harmony Workbench summary now adds compact analysis lines for scale mood/stability/tension, chord quality/function/roman numeral, and the selected note's scale/chord degree context. The workbench also separates key root from chord root so examples such as E Dominant 7 in A Major can show `V7` and `dominant`.

Harmony JSON remains metadata-only and now includes optional `scale_descriptor` and `chord_descriptor` fields, plus `chord_root_note`/`chord_root_display` when the chord root differs from the key root. Import can ignore descriptor payloads and recompute state from root/scale/chord fields. No audio arrays or preview audio are exported.
