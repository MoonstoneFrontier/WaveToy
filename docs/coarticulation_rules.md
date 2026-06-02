# Coarticulation Rules

Task 065 adds a small, non-destructive neighbor coarticulation layer for Continuous Mouth Motion. Rules are applied only to render copies after Voice Source has been applied once. Saved phoneme cards and chain data are preserved.

## Rule fields

Each supported neighboring pair may report these diagnostics:

- `coarticulation_pair`
- `coarticulation_strength`
- `coarticulation_type`
- `anticipatory_tongue_shift`
- `carryover_closure`
- `lip_rounding_carryover`
- `nasal_carryover`
- `voicing_carryover`

## Supported examples

| Pair | Rule type | Intended effect |
| --- | --- | --- |
| `S T` | alveolar stop prep | Prepares the tongue for the following stop while preserving the stop burst. |
| `T R` | retroflex release | Lets the stop release anticipate the liquid. |
| `K Y` | palatal fronting | Moves the back stop slightly toward the following glide. |
| `N D` | nasal to stop closure | Carries nasal resonance into the voiced stop onset. |
| `M B` | bilabial carryover | Carries bilabial closure and nasal color into the voiced stop. |
| `D Y` | alveopalatal glide | Smooths the voiced stop into the palatal glide. |
| `T Y` | palatal stop release | Prepares a sharper stop release into the glide. |
| `L IY` | front vowel lift | Nudges the liquid toward the high front vowel target. |
| `R AH` | rhotic vowel carryover | Keeps a little rhotic color into the vowel. |

## Manual listening checklist

- Render `S T AA P` and confirm `T` is not blurred away.
- Render `T R IY` and confirm the transition is smoother without new pitch warble.
- Render `K Y UW` and confirm the glide feels connected to the stop.
- Render `N D AH` and confirm nasal carryover is present but the stop release remains audible.
