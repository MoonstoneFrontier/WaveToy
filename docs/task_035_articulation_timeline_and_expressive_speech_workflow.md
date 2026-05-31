# Task 035 — Articulation Timeline and Expressive Speech Workflow

WaveToy's Articulation Chain now acts as a visual speech composer layered on top of the existing phoneme cards, Speech Bin, Timeline sends, Clip Crossfade fallback, and Continuous Mouth Motion renderer.

## Timeline editor architecture

- The Articulation Chain tab includes a horizontally scrollable **Visual Speech Timeline**.
- Every chain item is painted as a phoneme block whose width is proportional to `duration_ms`.
- Each block shows the phoneme name, IPA symbol, family icon, duration, and source badge.
- Dashed transition regions appear between phoneme blocks.
- Dragging a block's right edge edits its duration; dragging a transition region edits the boundary transition length.
- The existing phoneme cards and transition sliders remain available as fallback controls.
- Zoom buttons change the timeline scale without changing the underlying chain data.

## Scrubbing workflow

- A red draggable playhead can be moved while playback is stopped.
- Scrubbing calls the same articulation timeline sampler used by Word Motion Preview.
- The Word Motion canvas, status label, envelope tracks, and formant tracks update immediately at the scrubbed time.
- The live readout reports the current phoneme, next phoneme, transition progress, interpolated articulator values, playhead percentage, and current formants.

## Transition curves

The boundary data model now stores both transition length and transition curve:

```python
ArticulationBoundary:
  transition_ms
  transition_curve
```

Supported curves are:

- Linear
- Smoothstep
- Ease In
- Ease Out
- Ease In Out
- Sigmoid

Each boundary card has a curve dropdown, and the timeline boundary regions display the active curve label. Continuous Mouth Motion and Word Motion Preview both sample the selected curve for interpolated articulation.

## Envelope tracks

The speech workspace displays miniature automation tracks on the same playhead scale:

- `mouth_open`
- `tongue_height`
- `tongue_frontness`
- `lip_rounding`
- `voice_strength`
- `air_pressure`
- `closure`
- `nasal_open`

These tracks expose the internal control envelopes that drive the visual renderer and continuous word synthesis.

## Formant visualization

The Formant Explorer displays F1, F2, F3, and an educational F4 estimate. It is synchronized with the playhead so users can see how mouth opening, tongue height, tongue frontness, and lip rounding shift vowel-like acoustic regions over time.

## Enhanced vocal-tract feedback

The vocal-tract canvas continues to show mouth, tongue, lips, airflow, closure, and nasal indicators. It now includes a clearer voicing indicator: green and intensity-scaled for voiced phonemes, gray for unvoiced phonemes.

## Speech assets and library workflow

The existing Speech Bin remains the reusable asset area for created phonemes, syllables, words, and chains. Timeline and Articulation Chain send/drag workflows remain compatible with the new timeline metadata because phoneme durations, transition lengths, transition curves, source badges, and render settings serialize with the chain.

## Voice profiles

A non-destructive Voice Profile selector can nudge the editable chain into broad character presets:

- Child
- Female
- Male
- Robot
- Monster
- Whisper

Profiles adjust pitch, articulation/formant-related placement, voice strength, and noise balance on the editable chain. Users can edit phoneme sliders afterward.

## Save/load compatibility

Saved chain JSON now includes:

- articulation timeline items
- phoneme durations
- transition durations
- transition curves
- render mode/settings
- syllable marker placeholder data
- phrase marker placeholder data
- future pitch envelope placeholders
- future note event placeholders

Older chain files without transition curves still load by defaulting to Smoothstep.

## Future singing architecture

The articulation word render settings include placeholders for `pitch_envelopes` and `note_events`. Full singing mode is intentionally not implemented yet, but the timeline now has a stable place to attach pitch curves and note events later without replacing the speech timeline architecture.
