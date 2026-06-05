# Task 095 — Articulation Timeline Chain Split

## Workspace shape

Task 094 keeps the top-level **Articulation Timeline** workspace organized as four stable pages:

1. **Timeline**
2. **Render**
3. **Inspector**
4. **Profiles**

Task 095 adds one more layer only inside **Timeline**. The internal Timeline subtabs are:

1. **Chain**
2. **Timing**
3. **Motion**

No render defaults, project schema fields, audio lifecycle behavior, or asset formats changed.

## Chain subtab

**Chain** is for building and managing phoneme chains. It contains:

- Chain Builder actions: **Add Current**, **Create Syllable**, and **Clear Chain**.
- Wave source actions: **Apply Wave to Selected**, **Apply Wave to Whole Chain**, **Reset Selected**, and **Reset Whole Chain**.
- Chain cards and source actions.
- The compact **Speech Assets** sidebar.
- The collapsible **CV / VC Library**.

The Chain page uses a horizontal split so the active chain editor keeps primary space while Speech Assets remains a compact picker/sidebar.

## Timing subtab

**Timing** is for visual timeline editing and timing-focused controls. It contains:

- A read-only current-chain summary.
- **Musical Timing + Singing Preview**.
- Visual Speech Timeline zoom controls.
- The `ArticulationTimelineCanvas` scroll area.
- Selected Phoneme Controls.
- Scrub/playhead status.
- Boundary curve controls.
- Envelope and formant track canvases.

The Timing page keeps selected-phoneme editing near the visual timeline and keeps chain-card management out of the timing workflow.

## Motion subtab

**Motion** is for anatomical preview and animation export. It contains:

- **Motion Summary**, including phoneme count, unique viseme count, viseme holds, total duration, transition count, and average phoneme duration.
- A fit-to-view, read-only **Motion Timeline**; segment active-state checks use half-open intervals (`start_ms <= playhead_ms < end_ms`) with the final segment handled explicitly at the total-duration endpoint.
- A fit-to-view, read-only **Viseme Track** derived from the current chain.
- **Word Motion Preview** controls.
- **Play Word Motion**, **Loop Word Motion**, **Stop Motion**, and **Slow Motion Visual Only**.
- **Export Viseme JSON** and **Export Animation JSON**.
- The front/anatomical motion canvas.
- The collapsible side-cutaway SVG canvas.

Full chain-card editing is intentionally not duplicated here; users can confirm the current chain from the compact summary and return to Chain for edits. Functional horizontal zoom for the Motion Timeline/Viseme Track is deferred to Task 098, so Task 096 wording should describe those lanes as fit-to-view rather than zoomable.

## Why this reduces scrolling

Before Task 095, the Timeline page mixed chain construction, asset/library pickers, visual timing, selected-phoneme controls, envelopes, formants, and anatomical motion into one dense workflow. Splitting the page lets each subtab keep only the controls needed for the current task, so users no longer scroll through motion preview to reach chain cards or through chain-building controls to edit timing.

## Non-goals

- No new synthesis features.
- No measured formant extraction.
- No ML voice cloning.
- No audio engine rewrite.
- No render default changes.
- No project schema changes.
- No asset-format migration.
- No duplicate Articulation Inspector panels.
