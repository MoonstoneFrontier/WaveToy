# Task 070a — Musical Timing Patch Safety Pass

Task 070a tightens the Task 070 foundation so Musical Timing and Singing Preview remain safe, optional overlays instead of broad singing/editor rewrites.

## Safety changes

- Musical Timing remains default OFF.
- Singing Preview remains default OFF and stays inside the collapsed Musical Timing section.
- Musical snap applies only to phoneme block durations for now.
- Transition windows remain millisecond articulation timing and do not snap to beat subdivisions.
- Continuous Mouth Motion remains opt-in and keeps priority over expanding singing behavior.

## Transition policy

Transitions describe coarticulation, stop releases, fricative holds, and diphthong movement. They are speech-shaping windows, not musical note durations, so they keep the existing millisecond drag/manual behavior even when Musical Timing snap is enabled.

## Vowel anchoring policy

Singing pitch belongs mainly to vowels and sustained voiced material:

- vowels: `1.00`
- glides: `0.75`
- liquids: `0.70`
- nasals: `0.55`
- voiced fricatives: `0.25`
- stops: `0.00`
- unvoiced fricatives: `0.00`
- affricates: `0.00`

The preview computes render-time phoneme copies and does not mutate saved phonemes or presets.

## Pitch automation scope

Pitch automation remains lightweight. `NoteEvent` still stores vibrato and portamento metadata for future work, but the current generated curve uses stable note target start/end points only.

## Pitch lane preview

A compact read-only pitch lane summary appears near the Visual Speech Timeline when note events exist. It is informational only and does not add another editor.

## Stress marker integration note

`SyllableStressMarker` should eventually coordinate `accentuation_db`, `timing_bias`, and `pitch_bias_cents` together. Automatic syllable detection and complex stress UI are intentionally deferred.
