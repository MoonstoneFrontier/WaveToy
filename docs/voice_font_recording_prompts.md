# Voice Font Recording Prompt Foundation

This document is a dataset-planning foundation only. It does **not** implement microphone capture, production voice cloning, or automatic speech asset creation.

## Consent and provenance

Only record speakers who have explicitly consented to the intended use. Preserve speaker identity, recording date, device/context notes, license, and any restrictions in provenance metadata before using recordings for a voice-font experiment.

## Prompt groups

| Group | Purpose | Prompts | Known phoneme sequences |
| --- | --- | --- | --- |
| Vowels | Capture steady-state formants and source identity for Continuous tuning. | `AH`, `IY`, `OO`, `AE`, `AA`, `ER`, `AX` | Same as prompt labels. |
| Stop CV | Compare closure, release, and voiced/voiceless stop onset. | `BA`, `DA`, `GA`, `PA`, `TA`, `KA` | `B AH`, `D AH`, `G AH`, `P AH`, `T AH`, `K AH` |
| Fricative CV | Capture noisy onset plus vowel handoff for fricatives. | `SA`, `SHA`, `FA`, `THA`, `ZA`, `VA` | `S AH`, `SH AH`, `F AH`, `TH AH`, `Z AH`, `V AH` |
| Nasal / liquid / glide | Preserve voiced consonant identity through vowel transitions. | `MA`, `NA`, `LA`, `RA`, `WA`, `YA` | `M AH`, `N AH`, `L AH`, `R AH`, `W AH`, `Y AH` |
| Words | Exercise the current Continuous listen-test vocabulary. | `moon`, `bad`, `dad`, `stop`, `she`, `this`, `river`, `banana` | `M OO N`, `B AH D`, `D AE D`, `S T AA P`, `SH IY`, `TH IH S`, `R IH V ER`, `B AX N AE N AX` |
| Phrases | Test longer coarticulation, rhythm, and provenance-package examples. | `good morning`, `she sells sea shells`, `the quick brown fox`, `this is a voice test` | Approximate: `G UH D M AO R N IH NG`, `SH IY S EH L Z S IY SH EH L Z`, `DH AX K W IH K B R AW N F AA K S`, `TH IH S IH Z AX V OY S T EH S T` |

## Recording guidance

- Record several seconds of room tone per session.
- Keep distance and level consistent.
- Capture at least three takes per prompt.
- Do not normalize individual clips destructively; keep original files and derived analysis separate.
- Store consent/provenance next to any future dataset manifest.
