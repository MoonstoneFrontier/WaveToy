# Diphthong Profiles

Task 065 keeps diphthongs as a single articulation-chain item while letting Continuous Mouth Motion move through a render-only internal vowel glide.

## Render behavior

Saved chains still contain one phoneme symbol such as `AY`, `AW`, `OY`, `OW`, or `EY`. During Continuous rendering, the renderer looks up a per-diphthong profile, starts from the configured start vowel, and glides toward the end vowel after the profile's glide-start percentage. This does not split the timeline or mutate editable phoneme data.

## Profiles

| Diphthong | Start vowel | End vowel | Curve | Glide starts |
| --- | --- | --- | --- | --- |
| `AY` | `AH` | `IY` | Ease In | 55% |
| `AW` | `AH` | `UW` | Ease In Out | 45% |
| `OY` | `AO` | `IY` | Smoothstep | 40% |
| `OW` | `AO` | `UW` | Ease Out | 35% |
| `EY` | `EH` | `IY` | Ease In Out | 45% |

## Diagnostics

Continuous diagnostics include:

- `diphthong_profile`
- `glide_start_percent`
- `diphthong_start_vowel`
- `diphthong_end_vowel`
- `diphthong_progress`
- `diphthong_interpolation_curve`

## Manual listening checklist

- Render `AY`, `AW`, `OY`, `OW`, and `EY` in Continuous Mouth Motion.
- Confirm each diphthong visibly moves in the mouth animation.
- Confirm each diphthong audibly moves between vowel targets without pitch warble or distortion.
- Confirm saved chains still show one timeline item per diphthong.
