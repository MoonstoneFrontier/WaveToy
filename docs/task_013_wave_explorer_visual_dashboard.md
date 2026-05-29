# Task 013 — Wave Explorer Visual Dashboard

## Why the main scroll was reduced

WaveToy had placed nearly every sound-shaping control directly on the main page. That made the interface tall and encouraged long scroll gestures across sliders, combo boxes, and spin boxes. The dashboard pass adds a compact Wave Explorer-centered launch area at the top of the app so users can start from playful visual buttons instead of hunting through dense always-open editor sections.

The existing detailed sections remain available below the dashboard as a migration fallback. This keeps synthesis, export, recipes, Wave Explorer, Note Wheel, per-wave pitch, mute/solo, and Paulstretch behavior stable while the app moves toward Explorer-based workspaces.

## Wheel-event safety approach

The patch introduces no-wheel subclasses for common value controls:

- `NoWheelSlider`
- `NoWheelComboBox`
- `NoWheelSpinBox`
- `NoWheelDoubleSpinBox`

These widgets ignore wheel events so parent scroll areas can continue scrolling instead of accidentally changing sound parameters. The Wave Explorer canvas keeps its own wheel zoom behavior.

## VisualPanelButton design

`VisualPanelButton` is a custom painted dashboard launcher. Each button includes:

- a toy-like emoji label,
- a cached/symbolic or live miniature preview,
- compact current-state status text,
- button behavior that switches the dashboard Wave Explorer into a focused workspace.

The previews draw lightweight shapes from current UI/settings state and cached audio thumbnails. They do not run Paulstretch or perform full synthesis inside `paintEvent`.

## Buttons added and preview meanings

- **🎚 Shape Mix** — draws a cached live mixed-wave thumbnail when rendered audio is available, falling back to a small composite of the four wave shapes using current start/end levels. Muted waves are dimmed and soloed waves are emphasized in the fallback.
- **🎯 Pitch Toys** — draws a note-orbit preview showing main-follow and custom per-wave notes.
- **🎼 Tuning Map** — draws a curved tuning ladder with the current tuning label and root note.
- **👂 Stereo Space** — draws left/center/right guide lanes with colored wave blobs based on current per-wave pan, width, and dance.
- **✨ Sound Magic** — draws effect blobs plus a cached current-output waveform thumbnail showing the effect playground state.
- **🌈 Sound Experiments** — draws stacked toy cards and reports the saved experiment count or custom-wave state.

## Wave Explorer workspaces

The visual buttons now switch the dashboard Wave Explorer into an in-place workspace instead of opening more floating dialogs:

- **🎚 Shape Mix Workspace** — exposes per-wave start/end level controls around the still-visible Wave Explorer.
- **🎯 Pitch Workspace** — exposes main note, size, wiggle, pitch motion, and per-wave follow/note/octave controls around the waveform.
- **🎼 Tuning Workspace** — exposes tuning method, home note, and A4 reference controls.
- **👂 Stereo Workspace** — exposes left/right start, left/right end, width, dance, and dance-speed controls.
- **✨ Sound Magic Workspace** — exposes Paulstretch nap, dream amount, and evolution controls.
- **🌈 Experiments Workspace** — exposes built-in recipe launchers plus save/load shortcuts.

The workspace controls synchronize back to the existing main controls, so existing generation, recipe, and playback paths remain unchanged.

## Inline areas that remain

The detailed wave cards, Sound Modules, Whole-Mix Stereo Space, and Sound Experiments sections remain inline below the dashboard. They are kept as a safe fallback until each Explorer workspace is validated.

## Recommended next migration step

Move more of the detailed wave-card editing into the Explorer workspaces, then collapse or hide the duplicated inline sections once the workspaces cover the same functionality. Shape Mix and Stereo Space should be migrated first because they contain most of the remaining per-wave sliders.
