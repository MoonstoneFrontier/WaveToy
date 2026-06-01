# Viseme Mapping Plan

This is a foundation for future animation/export workflows. It does **not** implement a Blender addon or export pipeline yet.

## Principle

Future viseme export should be driven by **Continuous Mouth Motion state** rather than by static phoneme labels alone. The exported data should preserve timing, transition progress, mouth openness, lip rounding, tongue/frontness hints, voicing, and diagnostics.

## Initial mapping

| Viseme | Phonemes | Notes |
| --- | --- | --- |
| `closed_lips` | `P`, `B`, `M` | Closure shape; distinguish stop release from nasal sustain via timing/state. |
| `open_vowels` | `AH`, `AA`, `AE` | Wide/open jaw shapes. |
| `smile_front_vowels` | `IY`, `IH`, `EE`, `EH`, `EY` | Front tongue, spread lips. |
| `rounded_vowels` | `OO`, `UW`, `OH`, `OW`, `OY`, `W` | Lip rounding drives the shape. |
| `teeth_tongue` | `TH`, `DH` | Tongue/teeth visibility. |
| `fricative_front` | `S`, `Z` | Narrow front constriction. |
| `sh_zh_ch_jh` | `SH`, `ZH`, `CH`, `JH` | Postalveolar/affricate family. |
| `nasal` | `M`, `N`, `NG` | Nasality should use `nasal_open`; `M` also maps to closed lips. |
| `liquid` | `L`, `R` | Tongue-driven shapes; avoid over-opening. |

## Future-compatible JSON shape

```json
{
  "schema": "wavetoy.viseme_timeline.v1",
  "render_mode": "Continuous Mouth Motion",
  "phoneme_sequence": ["M", "OO", "N"],
  "frames": [
    {
      "time_ms": 0.0,
      "phoneme": "M",
      "viseme": "closed_lips",
      "transition_progress": 0.0,
      "mouth_open": 0.12,
      "lip_rounding": 0.2,
      "voiced_gain": 0.7,
      "diagnostics_ref": "frame_index:0"
    }
  ]
}
```

## Future work

- Export timeline JSON from Continuous renderer state.
- Add renderer hash/provenance links.
- Build Blender integration only after schema and Continuous timing settle.
