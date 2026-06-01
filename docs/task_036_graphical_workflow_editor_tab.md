# Task 036 — Graphical Workflow Editor Tab

## Purpose

The new **🧩 Graphical Editor** tab provides a visual-first path through WaveToy so users can shape sounds by dragging graphical objects before falling back to sliders. It gathers the most important graphical controls from Classic Editor, Wave Explorer, Articulation Lab, Articulation Chain, and Timeline handoff into one linear workflow.

The original Classic Editor, Articulation Lab, Articulation Chain, Timeline, save/load, synthesis, export, and slider controls remain in place.

## Workflow order

The tab is organized as collapsible section cards:

1. **Shape Source Wave** — wave layer cards, waveform/envelope preview, add/duplicate/mute/solo/remove actions.
2. **Place Sound in Stereo Space** — stereo field canvas with left/right ears and draggable start/end pan dots.
3. **Tune Pitch Motion** — octave-grid pitch curve with draggable start/end pitch points and a wiggle overlay.
4. **Add Sound Magic** — visual signal-order effect blocks for noise, shimmer, stretch, and filter/magic.
5. **Shape Mouth / Articulation** — editable Vocal Explorer canvas for tongue, mouth, lips, nose, voicing, and airflow.
6. **Build Speech Motion** — phoneme timeline blocks with draggable duration/transition handles, curve buttons, playhead scrubbing, and mouth preview.
7. **Send to Timeline** — preview/handoff buttons for existing Speech Bin and Timeline workflows.

Each section includes an advanced-controls shortcut back to the original tab that owns the full slider/control set.

## Direct manipulation architecture

The first implementation intentionally reuses the same widgets and data flow already used by the rest of WaveToy:

- Wave layer drag edits write to `wave_start_sliders` and `wave_end_sliders`.
- Stereo field drag edits write to `pan_start_slider`, `pan_end_slider`, and `width_slider`.
- Pitch curve drag edits write to `pitch_start` and `pitch_end`.
- Vocal tract drag/click edits write to `articulation_sliders` and `articulation_voiced_checkbox`.
- Articulation chain drag edits write to the existing `articulation_chain_items` duration, transition, and curve fields.

The graphical tab does not maintain a separate recipe or disconnected model. It repaints from existing UI/model state.

## Two-way sync rules

Implemented sync behavior:

- Graphical edits update the same widgets/model used by Classic Editor, Articulation Lab, and Articulation Chain.
- Existing scheduled generation and preview refresh paths run after graphical edits.
- Slider, preset, and recipe changes repaint the Graphical Editor through the shared render/refresh path.
- Articulation Lab preset/slider changes repaint the graphical vocal canvas.
- Articulation Chain changes repaint the graphical chain canvas and mouth preview.
- Loaded recipes use the existing `_apply_recipe` path, which updates sliders and then triggers the shared preview refresh.
- Loaded articulation chains use the existing chain refresh path, which updates both original and graphical chain canvases.

## Editable in this phase

Editable in the first version:

- Wave layer start/end amplitude handles.
- Wave layer add, duplicate, mute, solo, and remove for user-added layers.
- Stereo start/end pan dots and mouse-wheel width adjustment.
- Pitch start/end points.
- Vocal tract tongue position, mouth opening, lip rounding, nasal toggle, voice toggle, and airflow.
- Articulation chain duration handles, transition handles, selected transition curve, playhead scrubbing, and mouth preview.

## Preview-only in this phase

Preview-only / roadmap sections:

- Sound Magic noise, shimmer, stretch, and filter/magic blocks show signal order and current concept but do not yet provide full block-level direct editing for every effect.
- Timeline handoff remains a launch/send panel; detailed clip manipulation remains in the existing Timeline tab.
- Deeper waveform phase/offset handles are not included yet; the current wave layer editor focuses on amplitude envelope handles.

## Future roadmap

Recommended follow-up phases:

1. Add phase/offset handles and wave-layer drag ordering.
2. Add block-level Sound Magic intensity handles and effect bypass state directly inside each visual block.
3. Add richer pitch curve bending and note labels from the tuning map.
4. Add graphical Timeline drop targets so Graphical Editor can send sounds directly to lanes.
5. Add visual state badges for recipe/chain load events and more automated GUI tests when the Qt runtime is available.
