# Task 091 — Harmony Workbench Layout Cleanup

Task 091 reorganizes the note-wheel Harmony Workbench into a workflow-oriented **Music Theory** area. The change is intentionally layout-only: harmony analysis algorithms, interval calculations, chord/scale detection, note-color mappings, synthesis, export formats, and project schema remain unchanged.

## Music Theory subtabs

The Music Theory area now uses internal subtabs so each workflow has a clear home:

- **Notes** — note wheel, note picker, base-note display, spelling controls, wheel layout, note coloration, and selected-note mood.
- **Intervals** — interval preview controls, interval mood, interval educational summary, and selected-note relationship text.
- **Scales** — key root, scale selector, scale highlighting, Play Scale, scale descriptors, stability/tension/brightness summary, and future mode/degree expansion space.
- **Chords** — chord root, chord selector, chord highlighting, Play Chord, Play Arpeggio, chord quality, harmonic-function summary, and future inversion space.
- **Harmony Analysis** — contextual scale/chord/selected-note summary, roman numeral display, harmonic function, and descriptor reporting.
- **Export** — Import Harmony JSON and Export Harmony JSON actions, with metadata-only wording.

## Sidebar policy

Music Theory picker/list/library sidebars use the same compact dimensions as other recent workflow cleanup work:

- minimum: `220` px;
- preferred: `300` px;
- maximum: `380` px.

The helper pair is:

- `music_theory_picker_width_policy()` for deterministic width metadata;
- `apply_music_theory_sidebar_width_policy(widget)` for applying the policy to note lists, scale lists, chord lists, progression lists, educational libraries, and future harmony assets.

## Behavior preservation

The cleanup preserves all existing callback attributes and actions:

- spelling and wheel-layout controls still refresh note labels;
- note selection still calls the existing picker refresh path;
- key/scale/chord controls still feed `_current_harmony_state()`;
- scale/chord highlight toggles still update `CircleOfFifthsNotePicker` highlight layers;
- Play Home, Play Note, Play Interval, Play Scale, Play Chord, and Play Arpeggio still use the existing preview callback path;
- Import/Export Harmony JSON still use the existing metadata payload helpers.

No analysis, synthesis, export, or schema helpers were changed for this task.

## Future expansion

The split layout leaves dedicated homes for planned follow-ups such as progression analysis, cadence analysis, songwriting tools, harmonic movement visualization, composition assistance, and ear-training tools without forcing them into one large vertical page.
