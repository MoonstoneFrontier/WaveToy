# Task 065: Continuous Coarticulation and Diphthong Refinement

## Scope

This task improves connected-speech realism in Continuous Mouth Motion while keeping Clip Crossfade as the stable default. The patch focuses on three foundations:

1. Voice Source safety in the Continuous renderer.
2. Per-diphthong render profiles.
3. Non-destructive neighbor coarticulation rules.

## Voice Source single-application check

Continuous rendering now builds one list of render phoneme copies, applies Voice Source exactly once to each copy, and reuses those copies for envelope segments, source-cache preparation, pitch decisions, and stop burst rendering. The editable chain phoneme values are not changed.

Diagnostics include `voice_source_applied_count`. A value of `1` indicates the render copy received Voice Source exactly once.

## Per-diphthong behavior

Diphthongs remain a single timeline item. During Continuous rendering, the held diphthong item internally morphs through a profile-specific start vowel, end vowel, curve, and glide-start percentage. See `docs/diphthong_profiles.md` for profile details.

## Coarticulation foundation

The coarticulation layer is render-copy only. It adjusts supported neighboring pairs before the envelope timeline is built, then exposes the active pair diagnostics on hold/transition frames. See `docs/coarticulation_rules.md` for examples and field meanings.

## Manual listening checklist

- Render `AY`, `AW`, `OY`, `OW`, and `EY` in Continuous.
- Confirm each diphthong visibly and audibly changes.
- Render `M AY`, `N OW`, and `B OY`.
- Render `S T AA P` and confirm the `T` remains audible.
- Render `T R IY` and `K Y UW`.
- Render `N D AH`.
- Confirm Voice Source debug shows `voice_source_applied_count = 1` per render copy.
- Confirm Clip Crossfade remains the default render mode.
