# Articulation Timeline Workflow

## Primary Editing Model

The recommended workflow is visual-first:

1. Choose or shape a phoneme in **Articulation Lab**.
2. Use **Add to Articulation Timeline** at the top-right near the phoneme drawer.
3. Open **Articulation Timeline**.
4. Click phoneme blocks in the **Visual Speech Timeline**.
5. Edit the selected block in **Selected Component Controls**.
6. Use **Create Word**, **Play Word**, **Play Chain**, or **Send Word to Timeline** from the word action controls.

The older chain cards are still present for detailed review and fallback actions, but the visual timeline and selected-component panel are the primary editing surface.

## Selecting Blocks

- Single-click a phoneme block to select it.
- The selected block receives a stronger fill and bright outline.
- The block label shows phoneme name, IPA, duration, source badge, and a dB badge when accentuation is nonzero.
- Single-clicking a transition region selects the nearest phoneme until transition regions have their own persisted selection object.
- Dragging the playhead continues to scrub the Word Motion Preview.
- Dragging block edges still edits duration.
- Dragging transition regions still edits transition duration.

## Selected Component Controls

The panel directly under the Visual Speech Timeline edits the selected phoneme:

- Duration in milliseconds.
- Accentuation in dB.
- Voice strength.
- Air pressure.
- Transition duration to the next phoneme.
- Transition curve.
- Remove, duplicate, move left, and move right.

Changes immediately mark the cached word render dirty and repaint the timeline.

## Accentuation / Per-Phoneme Gain

Accentuation is a per-chain-item gain control stored as `accentuation_db`.

- Default: `0.0` dB.
- UI slider: `-12` dB to `+12` dB.
- Numeric entry: `-24` dB to `+24` dB.
- Formula: `gain = 10 ** (accentuation_db / 20)`.
- Runtime gain clamp: `0.05` to `4.0`.
- Positive values emphasize the phoneme.
- Negative values soften the phoneme.

Accentuation is applied before final limiter/normalization so boosted phonemes remain controlled. Continuous Mouth Motion diagnostics report the active accentuation value, the maximum accentuation in the chain, and the gain currently applied.

## Saving and Loading

Saved chains include `accentuation_db` for each item. Older chains that do not include the field load with `0.0` dB, preserving neutral behavior.

## Articulation Lab Placement

**Add to Articulation Timeline** is placed near the preset phoneme drawer because it appends the currently selected/shaped phoneme from that area. **Save Phoneme** remains available as a separate current-phoneme action for saving reusable presets.

## Future Redesign Opportunities

- Add explicit transition selection and a transition-only inspector state.
- Collapse legacy chain cards behind an advanced disclosure once the visual panel reaches full parity.
- Add keyboard navigation for selecting neighboring phoneme blocks.
- Add batch accent reset and normalize-accent helpers.
