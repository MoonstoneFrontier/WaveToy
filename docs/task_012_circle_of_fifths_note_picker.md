# Task 012 — Circle of Fifths Note Picker

## Design

WaveToy now uses a compact **🎡 Note Wheel** button for each per-wave custom note. The full selector opens in a small dialog so the wave cards stay compact while still giving pitch selection a playful, visual feel.

The picker is implemented as `CircleOfFifthsNotePicker`, a `QWidget` that draws a rounded, colorful panel with `QPainter`. It places note bubbles around a circular guide and highlights the selected note with a pressed/active look. Keyboard arrows can move around the wheel, and Return/Enter/Space can confirm the current note.

## Fifths ordering

The wheel uses sharps only, matching WaveToy's existing note names:

```text
C → G → D → A → E → B → F# → C# → G# → D# → A# → F
```

This order visually implies fifth-neighbor relationships without adding full music-theory complexity or flat/enharmonic spelling.

## Per-wave pitch integration

Each wave still has the same pitch behavior:

- **👯 Follow Main** remains the default.
- Switching to **🎯 My Note** reveals the per-wave note controls.
- The old internal note combo still exists as hidden state, so existing signal flow and recipe data remain simple.
- The visible **🎡 note button** opens the Note Wheel dialog.
- Selecting a note updates the hidden combo, the button label, the pitch label, previews, and the debounced sound generation path.
- The **🧸 Size** octave control and **🎯 Wiggle** cents/fine-tune control remain next to the Note Wheel button.

## Tuning map interaction

The Note Wheel only chooses the note name. The active **Tuning Map** still decides the exact spacing and frequency for that note. Equal temperament remains the default, while non-equal tuning maps continue to receive the selected note name as input.

The Note Wheel tooltip and dialog copy clarify this split:

> The wheel picks the note. The Tuning Map decides how the note is spaced.

## Recipe compatibility

Recipes continue to save per-wave notes as plain note strings. No widget-specific data is written.

Compatibility behavior is unchanged:

- Recipes with `wave_note` fields load those note strings.
- Recipes without `wave_note` fields default each wave's custom note to `A`.
- Loading a recipe updates the hidden combo and therefore the visible Note Wheel button/label.

## Remaining limitations

- The wheel currently uses sharps only.
- It does not display alternate flat/enharmonic spellings.
- The selector is modal for simplicity; a future version could use a non-modal popover if desired.
