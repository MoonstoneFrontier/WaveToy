# Task 032: Troubleshoot Phoneme Transition Synthesis

## Observed problem

Increasing an Articulation Chain transition length made Create Word / Play Word Motion sound as if an extra region had been inserted between phonemes. That region could sound like a sustained buzz or noise rather than a smooth change from phoneme A into phoneme B.

## Root cause found

The smooth/coarticulated word renderer rendered each phoneme as a complete clip, then rendered a separate interpolated transition clip with `_render_interpolated_transition_clip`, and appended that transition between adjacent phoneme clips. The transition clip was produced by repeatedly rendering short interpolated phoneme snapshots with the normal phoneme renderer. For voiced or fricative-like interpolated states, that separate clip could become a generic voiced tone, centered tone, or noise segment.

That meant `transition_ms` was effectively extra rendered duration between phonemes:

```text
phoneme A + standalone interpolated transition segment + phoneme B
```

rather than overlap/coarticulation:

```text
phoneme A tail overlaps phoneme B head
```

The gap-like perception was not primarily zero insertion in the smooth renderer. Word gaps are normally disabled by `allow_word_gaps = False`; the buzz came from the standalone transition render being inserted as its own audio region.

## Transition semantics

`transition_ms` now means overlap/coarticulation duration between adjacent phoneme clips. It does not mean added time between clips.

The intended model is:

1. Render phoneme A normally.
2. Render phoneme B normally.
3. Overlap A's tail with B's head for the effective transition duration.
4. Apply an equal-power crossfade across the overlap.
5. Continue with the non-overlapped remainder of phoneme B.

No silence is inserted to represent transition length, and no standalone generic transition buzz is rendered in the current coarticulated path.

## Implemented fix

The coarticulated renderer now uses Strategy A: overlap crossfade.

- It pre-renders the phoneme clips in the chain.
- For each boundary, it reads the requested transition from the per-boundary slider or family rule.
- It clamps the transition to available audio, using no more than 45% of the shorter adjacent clip.
- Stop-related transitions are clamped more conservatively so stop closure/burst identity is less likely to smear.
- It overlaps the left tail and right head using equal-power sine/cosine fades.
- It logs a compact diagnostic line for every boundary.

The older interpolated transition clip renderer is retained for future Strategy B experiments, but the smooth/coarticulated word path no longer inserts it as an independent segment.

## Debug logging format

Each coarticulated boundary prints one compact line with this prefix:

```text
[WaveToy Transition]
```

The line includes:

- from phoneme and to phoneme
- from family and to family
- requested transition duration in ms
- effective transition duration in ms
- crossfade samples
- inserted silence samples
- standalone transition render samples
- whether interpolated articulation was used for audio
- voiced gain start/end
- noise gain start/end
- tonal gain start/end

Example shape:

```text
[WaveToy Transition] M->OO families=nasal->vowel requested_transition_ms=200 effective_transition_ms=200.0 crossfade_samples=8820 inserted_silence_samples=0 transition_render_samples=0 interpolated_articulation_used=False voiced_gain_start=0.700 voiced_gain_end=0.820 noise_gain_start=0.035 noise_gain_end=0.060 tonal_gain_start=0.490 tonal_gain_end=0.574
```

A deeper optional flag is available in `articulation_word_render_settings`:

```python
"transition_debug_verbose": False
```

Set it to `True` while debugging to print additional clip/source context. It is intentionally off by default.

## Remaining limitations

This fix is intentionally conservative. It removes the inserted buzz/gap behavior, but it is still a clip-overlap strategy rather than a true continuous vocal-tract/articulator renderer.

Known limitations:

- Equal-power crossfades do not truly morph formant filters sample-by-sample.
- Very long overlaps can still smear transient phonemes, especially stops, though stop transitions are clamped more aggressively.
- The retained `_render_interpolated_transition_clip` can still be useful for a future hybrid bridge, but it should not be inserted as standalone audio without replacing part of adjacent clips.
- Word Motion Preview remains an articulation animation timeline; audio now uses matching transition durations as overlap durations, so rendered word duration can be shorter than the sum of individual phoneme durations.

## Recommended future architecture

The best long-term synthesis architecture is Strategy C: render the whole word as one continuous stream driven by time-varying articulation envelopes.

A future continuous renderer should:

- build per-parameter envelopes for mouth opening, tongue height/frontness, lip rounding, voicing, airflow, closure, burst strength, and nasal opening;
- keep stop closures and bursts as explicit events in the envelope;
- drive the tone/noise/formant renderer continuously from those envelopes;
- use the same envelope timeline for Word Motion Preview and audio export;
- reserve crossfade-only rendering as a fallback for source-audio modes or imported audio.

Strategy B is a useful intermediate step: replace part of A's tail and B's head with an interpolated bridge, rather than inserting the bridge between them. That bridge must inherit real phoneme filtering and source gains so it does not become a generic drone.
