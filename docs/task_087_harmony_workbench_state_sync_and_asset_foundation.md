# Task 087 — Harmony Workbench State Sync and Asset Foundation

Task 087 hardens the Task 086 Harmony Workbench without expanding WaveToy into a DAW, MIDI editor, piano roll, or full music-theory engine.

## Harmony refresh triggers

Harmony state is refreshed from a single workbench snapshot whenever the user changes:

- Home/root note.
- Scale type.
- Chord type.
- Spelling mode: Auto, Sharps, or Flats.
- Wheel layout: Intervals or Circle of Fifths.
- Scale/chord highlight toggles.
- Selected pitch class on the note wheel.

The centralized refresh path keeps scale notes, chord notes, labels, degree text, preview targets, and note-wheel highlights synchronized. The selected pitch class is intentionally preserved through harmony refreshes.

## Highlight layering policy

Scale and chord highlights are tracked as separate pitch-class sets even though the existing compatibility accessor still exposes their union.

Layering is intentionally simple:

1. Scale tones draw a broad light halo.
2. Chord tones draw a stronger pink halo so chord tones remain distinguishable inside the scale.
3. The root draws the strongest yellow halo.
4. The selected note draws its own glow and larger bubble on top of harmony highlighting.

Turning both highlight toggles off clears both layer sets and removes the highlight root so stale highlights are not retained after root, scale, chord, or layout changes.

## Pitch-class vs display spelling policy

Internal harmony identity remains normalized pitch classes (`C#`, `D#`, `A#`, etc.). Display spelling is a presentation layer only:

- Auto chooses flats for flat-oriented home/root notes and sharps for sharp-oriented roots.
- Sharps and Flats force compact enharmonic names.
- Changing spelling mode never changes the underlying pitch-class list.

Unknown scale IDs fall back to Major. Unknown chord IDs fall back to Major Triad. This keeps helper functions deterministic and crash-resistant without pretending to be a complete notation engine.

## Preview lifecycle behavior

Play Scale, Play Chord, and Play Arpeggio continue to use in-memory sine previews. Every note-wheel preview request stops the previous preview before starting a replacement. Closing the note wheel also requests preview stop. Preview generation uses current pitch classes plus the active octave/range, cents, tuning method, tuning root, and A4 reference where available. Preview audio is not written to disk.

Chord preview uses reduced per-tone gain and clipping safety to avoid excessive summed levels.

## Reserved harmony asset types

Task 087 reserves lightweight JSON-safe foundations for future reusable harmony assets:

- `scale_pattern`
- `chord_pattern`
- `chord_progression`

The reserved dataclasses include `uuid`, `name`, `root_note`, `spelling_mode`, `scale_type`, `chord_type`, `chord_steps`, `tags`, `notes`, `created_at`, and `modified_at`. They do not introduce a project-schema migration and do not implement full CRUD yet.

## Harmony JSON export shape

The Harmony Workbench has a low-risk **Export Harmony JSON** action. The payload is metadata only and includes:

- Schema/version marker.
- `created_at` timestamp.
- Root/home note and displayed root.
- Scale type, label, normalized pitch classes, and displayed names.
- Chord type, label, normalized pitch classes, and displayed names.
- Spelling mode.
- Reserved harmony asset type names.

No audio and no MIDI data are exported.

## Known limitations

- No full chord progression editor yet.
- No MIDI export yet.
- No piano roll yet.
- No project storage migration for harmony assets yet.
- Harmony spelling is compact enharmonic display, not context-aware classical notation.

## Task 088 follow-up

Task 088 keeps the Task 087 Harmony Workbench state-sync behavior but hardens the metadata path. Export now appends `.json` when needed, writes with `ensure_ascii=False` and `indent=2`, reports success with a root/scale/chord summary, and warns on write failures. Import Harmony JSON provides low-risk symmetry for `wavetoy.harmony_metadata.v1` metadata without importing audio or changing the project schema.

## Task 089 analysis note

The Harmony Workbench now has a compact descriptor-driven analysis summary. It keeps scale and chord refresh synchronized, separates key root from chord root for simple roman numerals, and reports educational function categories such as tonic, predominant, dominant, color, and chromatic. This remains a workbench helper, not a progression editor or MIDI workflow.
