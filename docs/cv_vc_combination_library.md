# CV/VC Combination Library

The CV/VC foundation library is generated from the expanded English consonant and vowel inventories.

- Consonants: 24
- Vowels: 16
- Pattern types: CV and VC
- Expected count: `24 * 16 * 2 = 768`

Each combination stores:

- ID and display label
- pattern type (`CV` or `VC`)
- first and second phoneme
- phoneme and IPA sequences
- transition duration and curve
- Clip Crossfade as the recommended render mode
- Continuous Mouth Motion tuning placeholders:
  - `coarticulation_weight`
  - `airflow_blend`
  - `voicing_blend`
  - `tongue_blend`
  - `lip_blend`

Clip Crossfade remains the stable default/recommendation until Continuous Mouth Motion passes validation consistently. The Articulation Timeline also includes a JSON-only export button for the generated library; it does not write WAV files.
