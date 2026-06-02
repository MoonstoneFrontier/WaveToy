# Voice Source Model

WaveToy now separates **Voice Source** from **mouth articulation**.

- The **Voice Source** layer represents upstream vocal-fold and laryngeal behavior: fold length, thickness, tension, closure, breathiness, rasp, jitter, shimmer, larynx height, tract length bias, and age looseness.
- The **mouth/nose articulation** layer still shapes phonemes: mouth opening, tongue position, lip rounding, nasal opening, closure, airflow, voicing, and formant shaping.

`VoiceSourceProfile` is a safe, serializable data foundation. Its normal numeric range is `0.0` to `1.0`, and the safe default is intentionally neutral. The current mapping nudges pitch, voicing, air pressure, and noise color before rendering without changing editable phoneme controls.

This is not ML voice cloning. Future patches may add small UI controls, additional presets, and better source synthesis, but the model should remain consent-aware and transparent.
