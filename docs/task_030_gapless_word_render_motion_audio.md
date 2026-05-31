# Task 030 — Gapless Word Rendering and Motion Playback Audio

## Gapless created-word rendering

Created Word renders are intended to behave as one continuous sound stream. The word renderer now treats the editable phoneme chain as articulation material, not as a set of independent clips separated by default silence.

- The default word-render gap is `0 ms`.
- Positive `gap_after_ms` values on chain items are ignored for Create Word unless `allow_word_gaps` is explicitly enabled in the word render settings.
- The word assembly path crossfades overlapping audio rather than inserting zero-valued samples at phoneme boundaries.
- Final fade-in and fade-out are applied only once at the full word edges.

Raw chain preview remains available as a comparison path and does not replace Created Word export, Speech Bin, or timeline speech rendering.

## Intentional stop closure vs. unwanted boundary silence

Stop consonants can still contain an intentional closure before their burst. That closure is generated inside the stop phoneme itself and represents the stop articulation. It is different from an unwanted boundary gap after a phoneme.

The gapless word renderer removes/bypasses boundary gaps between rendered phonemes, but it does not remove the closure portion of stop phonemes such as K, T, P, G, D, or B.

## Crossfade and transition defaults

Created Word uses short overlap/crossfade regions at joins, with family-aware defaults:

| Boundary type | Crossfade |
| --- | ---: |
| Minimum word crossfade | 12 ms |
| Default word crossfade | 24 ms |
| Vowel → vowel | 60 ms |
| Glide/liquid → vowel | 55 ms |
| Nasal → vowel | 40 ms |
| Fricative/affricate → vowel | 30 ms |
| Stop → vowel | 8 ms |

When smooth mouth transitions are enabled, the renderer also creates transition audio by interpolating articulation fields with the smoothstep curve `t * t * (3 - 2 * t)`. Interpolated fields include mouth opening, tongue position, lip rounding, voicing, air pressure, teeth gap, closure, burst strength, and nasal opening.

## Play Word Motion audio synchronization

The Word Motion Preview button is now labeled **Play Word Motion**. It renders the current smoothed word if needed, starts that word audio, and runs the mouth animation from the same duration basis. Loop Motion loops both the animation and rendered word audio. Stop Motion stops the animation timer and sounddevice playback together when sounddevice is available.

Slow Motion is labeled **Slow Motion Visual Only** because the app does not time-stretch word audio for slow preview.

## Debug gap-detection notes

Word rendering prints diagnostic messages prefixed with `[WaveToy Word]`, including:

- render start and phoneme count,
- ignored requested gaps,
- boundary crossfade duration and sample position,
- detected near-silent boundary regions longer than 5 ms,
- final rendered duration.

A detected near-silent region is a warning for review, not an automatic failure. Stop closure silence may still appear inside stop phonemes by design.

## Remaining limitations

- Slow Motion does not synthesize or time-stretch slowed audio; it is visual-only.
- Gap detection is heuristic and based on near-zero amplitude around recorded render boundaries.
- This remains a stylized sci-fi soundscape/articulation tool, not realistic speech synthesis.
