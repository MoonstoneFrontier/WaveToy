# Viseme Timeline Plan

WaveToy can now derive generic `VisemeFrame` JSON from existing phoneme and articulation state. Frames include time, phoneme, viseme label, mouth opening, lip rounding, tongue height/frontness, nasal opening, closure, voiced gain, airflow, and transition progress.

The first export is generic JSON. It is intentionally not a Blender, Unity, Godot, Unreal, or VTuber-specific rig format yet. Future work can add target-specific adapters after the generic data proves useful.
