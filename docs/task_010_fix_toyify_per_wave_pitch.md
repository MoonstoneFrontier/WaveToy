# Task 010 — Fix and Toyify Per-Wave Pitch Controls

## Root cause

Task 009 exposed per-wave pitch widgets, but the audio path needed one clear source of truth for choosing the pitch envelope for each wave. The fix makes that path explicit with `effective_wave_frequency_env(settings, wave_type, global_freq_env)` and calls it from both the full audio generator and the lightweight wave-card preview builder.

The other usability issue was that the note, octave, and cents controls stayed visible even when a wave was following the main pitch. That made the card feel technical and implied those controls were active when they were not.

## Per-wave pitch model after the fix

- **👯 Follow Main** is the default for sine, triangle, sawtooth, and square.
  - The wave uses the global pitch start/end controls and curve.
  - Old recipes that have no per-wave pitch fields continue to load as follow-main.
- **🎯 My Note** is opt-in per wave.
  - The wave ignores the global pitch sweep for oscillator frequency.
  - The wave uses its own note, octave, and cents value.
  - Changing one wave's custom note does not change the other waves.

## Toy-style UI changes

Each wave card now has a compact pitch toy:

- A single mode button that reads **👯 Follow Main** or **🎯 My Note**.
- A small status label such as **👯 Main**, **🎯 C5**, or **🎯 E4 +7¢**.
- The custom note picker is hidden while following the main pitch.
- When custom pitch is enabled, the grouped picker uses playful labels:
  - **🎵 Note**
  - **🧸 Size** for octave
  - **🎯 Wiggle** for cents

## Tuning behavior

Per-wave custom notes use the selected tuning method through `frequency_for_note(...)`, the same helper used by the main musical note controls. Unknown tuning IDs fall back through the existing tuning method lookup to piano-style equal temperament.

Cents are applied after the tuning method frequency is calculated, so the cents control remains a fine-tune offset. The global pitch start/end sliders still behave as a continuous equal-ratio sweep, adjusted by the selected main note tuning ratio.

## Recipe compatibility

- Existing recipes without `wave_follow_main_pitch`, `wave_note`, `wave_octave`, or `wave_cents` load with every wave in **👯 Follow Main** mode.
- New recipes save and load each wave's follow-main state, note, octave, and cents.
- Built-in Sound Experiments reset waves to follow-main before applying their classic settings, so **Pure A4** remains a plain A4 recipe even after experimenting with custom per-wave notes.

## Manual test results

Environment note: this container can compile the file, but cannot open the PySide6 app because the system OpenGL runtime library `libGL.so.1` is missing.

Completed checks:

- Syntax check passed with `python -m py_compile wave_toy.py`.
- Per-wave pitch helper test passed with sine following main A4 and triangle/sawtooth/square set to C5/E5/G5.
- Full `generate_audio(...)` returned non-empty stereo audio for the mixed custom-pitch settings.
- `python wave_toy.py` was attempted and failed before app startup due to missing `libGL.so.1` in the environment.

Manual checks still recommended on a desktop with PySide6/OpenGL available:

1. App opens without crash.
2. All waves default to **👯 Follow Main**.
3. **Pure A4** sounds unchanged.
4. Set triangle to **🎯 My Note C5**; triangle pitch changes.
5. Changing triangle note does not change sine/sawtooth/square.
6. Set sine/triangle/sawtooth/square to different custom notes; generated audio uses different frequencies.
7. Switch a wave back to **👯 Follow Main**; it follows global pitch again.
8. Changing tuning map changes custom per-wave notes.
9. Per-wave pitch labels update correctly.
10. Per-wave previews update density/cycles when pitch changes.
11. Save/load preserves per-wave pitch settings.
12. Wave Explorer still opens and updates.

## Remaining limitations

- The Wave Explorer's global pitch overlay still displays the main/global frequency envelope, not four separate per-wave pitch envelopes.
- Custom per-wave notes are steady pitches; they do not currently have their own start/end sweep controls.
- The app still needs a desktop runtime with the PySide6 graphics dependencies installed.

## Recommended next task

Add a small optional Wave Explorer pitch legend that lists each active wave's effective pitch mode and frequency, so custom per-wave notes are visible in the explorer without changing its rendering model.
