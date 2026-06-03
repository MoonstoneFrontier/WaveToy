# Waveform Analysis Workflow

This workflow uses WaveToy's Articulation Lab to compare stable Clip Crossfade rendering against opt-in Continuous Mouth Motion.

## Setup

1. Open `wave_toy.py`.
2. Go to Articulation Lab / Articulation Timeline.
3. Confirm Word Render Mode starts on **Clip Crossfade**.
4. Confirm **Musical Timing** and **Singing Preview** are off unless intentionally testing those foundations.
5. Build or load one validation chain.

## Compare render modes

For each validation chain:

1. Render/play in Clip Crossfade.
2. Switch Word Render Mode to Continuous Mouth Motion.
3. Render/play again.
4. Open Continuous diagnostics and inspect the waveform editor overlays.
5. Toggle overlays off to confirm the visual layer is optional and does not affect playback.

## What to inspect

- **Silence:** waveform should have visible energy and audible output.
- **Distortion:** red high-peak regions should be rare; harsh formant artifacts should be checked with Bypass formants.
- **Pitch:** intended and estimated tracks should stay close during voiced vowels, glides, nasals, and liquids.
- **Stops:** P/B/T/D/K/G bursts should remain sharp, visible, and audible.
- **Diphthongs:** AY/AW/OY/OW/EY should show one timeline item with internal start/end vowel glide labeling.
- **Resonance:** base and resonance-biased formants should remain in safe ranges; Bypass formants should remove shaping.

## Repository hygiene

Do not stage generated WAV files, cache files, or manual audio exports. Commit only source and documentation changes.
