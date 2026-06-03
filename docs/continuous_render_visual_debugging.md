# Continuous Render Visual Debugging

The Articulation Lab Continuous diagnostics section includes a waveform editor for rendered word audio. It is a diagnostic viewer, not a destructive editor.

## Optional overlays

The **Show waveform diagnostic overlays** checkbox controls all overlay drawing. Turning it off leaves playback and cached render audio unchanged.

Overlay types:

| Overlay | Color | Meaning |
| --- | --- | --- |
| Clipping / high peak | Red | Samples or short windows near unsafe peak levels. |
| Stop burst | Yellow | Release burst windows for P, B, T, D, K, and G style stops. |
| Transition | Teal | Continuous transition windows between neighboring phonemes. |
| Diphthong glide | Purple | Internal vowel target movement inside a single diphthong timeline item. |
| Pitch instability | Red/pink | Intended-vs-estimated pitch error above the diagnostic threshold. |
| Formant processing | Orange | Regions where Continuous formant/resonance shaping is active. |

Hovering an overlay updates the tooltip with the label and diagnostic values.

## Pitch tracks

The waveform editor draws two pitch traces when pitch diagnostics are available:

- Navy solid line: intended Continuous pitch.
- Red dotted line: estimated pitch from the rendered waveform.

A large mismatch is marked as a pitch-instability overlay. Noisy consonants can produce weak estimates; evaluate them together with audible quality.

## Formant safety

The formant overlay tooltip compares base articulation F1/F2/F3 with resonance-biased F1/F2/F3. Extreme resonance controls are clamped before rendering, and the Continuous formant layer uses conservative gain/rms compensation.

Use **Bypass formants** to confirm that resonance/formant shaping is fully removed from Continuous rendering when isolating pitch or source-excitation issues.
