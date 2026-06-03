# Animation Export Plan

Task 068 extends generic animation JSON for future Blender, VTuber, and rigging tools without adding target-specific code or dependencies.

## Human-readable schema fields

Animation export now includes:

- `speech_organ_state_frames`
- `voice_box_state_frames`
- `voice_source_profile`
- `character_profile`
- `render_mode`
- `phoneme_sequence`
- `timing_frames`

The export remains generic JSON. Blender-specific add-ons can consume this later, but no Blender dependency is added.

## Voice and speech state frames

Speech-organ frames provide mouth/tongue/lip/velum/glottis snapshots. Voice-box frames provide the upstream larynx state plus future formant-bias metadata for larynx height, vocal tract length, and resonance depth.

## Future singing and voice-font support

The schema is suitable for future singing because pitch, voicing, timing, and larynx metadata can be aligned with phoneme frames. Voice-font support should remain consent-first and must not imply ML voice cloning.

## Task 069 resonance schema additions

Generic animation and viseme JSON now includes resonance-oriented data while preserving existing keys:

- `resonance_tract_state_frames`
- `formant_frames`
- `resonance_profile`
- `resonance_curves`
  - `f1_curve`
  - `f2_curve`
  - `f3_curve`
  - `nasal_coupling_curve`
  - `chest_resonance_curve`
  - `head_resonance_curve`

The data remains human-readable JSON and does not require Blender or any target-specific dependency.

## Task 070 musical timing and singing additions

The generic animation export now also includes singing-ready and beat-aware fields while preserving the existing speech-organ, voice-box, resonance, formant, and viseme keys:

- `musical_timing_settings`
- `note_events`
- `pitch_curve`
- `syllable_stress_markers`
- `beat_grid`
- `tempo_map`
- `singing_mode_enabled`

These additions remain plain JSON. MIDI, Blender, DAW, and game-engine adapters should consume this generic schema later instead of adding dependencies to WaveToy's core export path.
