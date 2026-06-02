# AGENTS.md — WaveToy Agent Instructions

## Project purpose

WaveToy is a Python desktop audio/sci-fi soundscape generator. The active application entry point is `wave_toy.py`, a PySide6/numpy single-file GUI for waveform synthesis, stereo visualization, file export, and Paulstretch-style ambience experiments.

## Development rules

- Keep changes small, focused, and reviewable.
- Do not perform broad redesigns or major refactors unless the user explicitly requests them.
- Do not remove existing audio generation, synthesis, export, preset, visualization, or Paulstretch-related features without explicit approval.
- Preserve `wave_toy.py` as the main script name and primary entry point unless instructed otherwise.
- Prefer documenting dependency or environment assumptions rather than silently adding large new dependencies.
- Avoid changing playback, stop/cancel, or audio lifecycle logic unless the task specifically asks for that work.
- Keep user-facing behavior stable when doing repository hygiene, documentation, or verification tasks.

## Verification

- Run syntax checks before finalizing Python changes:

  ```bash
  python -m py_compile wave_toy.py
  ```

- If dependency availability matters, report missing third-party packages rather than masking the issue.

## Task 063 roadmap reminders

- Voice Source is an upstream vocal-source/voice-box layer; keep it separate from mouth/nose articulation and do not implement ML voice cloning.
- Character Voice Profiles may drive voice source, timing, accentuation, and expressive delivery, but must not replace direct phoneme controls.
- Musical Timing is a future beat/measure architecture; current millisecond timing remains the default speech workflow.
- Viseme Timeline and Animation Export should start with generic, human-readable JSON before target-specific add-ons such as Blender.
- Continuous Mouth Motion quality remains the highest speech-rendering priority, but Clip Crossfade stays the stable default until Continuous is validated.
- Keep Task 063 patches small, focused, and reviewable.
