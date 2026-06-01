# Task 061 — Articulation Timeline Workflow Redesign

## Summary

Task 061 makes the Visual Articulation Timeline the primary surface for selecting and editing phoneme blocks. The older chain cards remain available as a compatibility and advanced-action fallback, but everyday edits now start by clicking a block in the visual timeline and using the compact **Selected Component Controls** panel directly below it.

## Phoneme Accentuation

Each `ArticulationChainItem` now stores `accentuation_db` with a default of `0.0` dB. The value is serialized with saved chains and defaults to `0.0` when older `articulation_chain.json` files do not include it.

- Neutral: `0.0` dB.
- Positive values emphasize a phoneme.
- Negative values soften a phoneme.
- UI slider range: `-12` dB to `+12` dB, centered at `0`.
- Numeric field range: `-24` dB to `+24` dB.
- Render gain: `10 ** (accentuation_db / 20)`.
- Gain is clamped to `0.05` through `4.0` and is applied before final limiting/normalization.

Accentuation participates in word-render signatures because chain serialization includes the field. Changing it invalidates the current word render cache.

## Rendering Coverage

Accentuation is applied in these render paths:

- Clip Crossfade / coarticulated word rendering.
- Plain/raw chain rendering and Play Chain.
- Continuous Mouth Motion frame rendering, including interpolated transition frames.

Continuous diagnostics now expose:

- `active_phoneme_accentuation_db`
- `max_accentuation_db`
- `gain_applied`

The built-in Continuous validation applies a low-risk `+3 dB` accent to the OO phoneme in the `M OO N` chain.

## Workflow Changes

### Visual Timeline Selection

Clicking a phoneme block selects that chain item and updates:

- selected block highlight,
- the Articulation Lab phoneme controls,
- Word Motion Preview state,
- the Selected Component Controls panel.

Clicking a transition region selects the nearest phoneme because dedicated transition-object editing is not yet modeled separately.

### Selected Component Controls

The compact panel below the Visual Articulation Timeline includes:

- selected phoneme label and IPA,
- duration,
- accentuation,
- voice strength,
- air pressure,
- transition-to-next duration,
- transition curve,
- remove, duplicate, move-left, and move-right actions.

Edits mark the word render dirty and refresh the timeline graphics immediately.

### Articulation Lab Button Placement

**Add to Articulation Timeline** now appears at the top-right of Articulation Lab, directly above/near the phoneme drawer that provides its input. The bottom duplicate placement was removed. **Save Phoneme** remains in the current-phoneme action area as a distinct save-to-library action.

## Backward Compatibility

Older chains without `accentuation_db` load with neutral accentuation (`0.0` dB). The main entry point remains `wave_toy.py`, and existing Play Word, Play Chain, Create Word, Send Word to Timeline, save/load, and source-assignment features remain available.

## Remaining Opportunities

- Promote transition regions to first-class selected components with their own persistent selection state.
- Collapse the legacy chain cards by default once the contextual panel covers every advanced chain action.
- Add keyboard shortcuts for moving and duplicating selected blocks.
- Add optional per-phoneme accent badges to exported speech-asset metadata summaries.
