# Task 024 — Vocal Explorer Promotion and Drawer Compression

## Reason for promoting Vocal Explorer

Task 023 established the Articulation Lab drawer architecture, but the Vocal Explorer became too visually compressed. The mouth cavity, tongue, airflow, nose, and voice cues need room to read as the primary feedback surface while editing phonemes. This task promotes the Vocal Explorer into the hero element of the lab without changing phoneme rendering or playback behavior.

## Vocal Explorer changes

- Increased the Vocal Explorer card height range so it can occupy roughly 80–120 px more vertical space than the prior compact layout.
- Gave the vocal tract canvas a larger minimum drawing area so the face, mouth, tongue, airflow, nasal, and voice markers have more breathing room.
- Kept Play, Loop, and Stop in the top row near the current phoneme name and IPA badge so playback controls remain close to the selected sound without squeezing the canvas.

## Workspace column ratio changes

- Reweighted the Articulation Lab workspace so the left editing area receives the dominant share of the horizontal layout.
- Reduced the phoneme drawer shell to a smaller support panel with a 300 px minimum and 390 px maximum width, targeting a left-heavy workspace close to the requested 75% / 25% balance.
- Preserved the icon rail plus drawer stack architecture; the drawer remains visible and usable but no longer competes with the Vocal Explorer as the primary element.

## Icon rail clipping fix

- Converted the phoneme rail to icon-only buttons.
- Added tooltips and accessible names for each rail category:
  - 😀 Vowels
  - 🌬 Fricatives
  - 💥 Stops
  - 👃 Nasals
  - 💾 Saved Phonemes
- Kept checked-state styling for a clear selected drawer highlight.

## Drawer card compression

- Converted preset buttons from a stacked two-line layout into compact single-row cards showing emoji, friendly preset name, and IPA together.
- Preset cards now use a 56–64 px height range with tighter padding and left-aligned text.
- Saved phoneme cards remain larger than preset cards because they include playback and management actions.

## Canvas overlay cleanup

- Removed the formant/status text previously drawn directly inside the vocal tract canvas.
- Added a dedicated readable strip below the canvas for formants and the articulation summary.
- The canvas now focuses on visual articulation markers only: mouth shape, tongue position, airflow, nasal opening, and voice indication.

## Remaining limitations

- The application still depends on the local PySide6/numpy/audio environment for full interactive validation.
