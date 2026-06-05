# Task 090 — Articulation Timeline Layout Cleanup

Task 090 reorganizes the existing Articulation Timeline workflow without adding synthesis features, changing render defaults, changing project schema, or removing controls.

## Before layout audit

The previous Articulation Timeline tab placed these workflow groups in one long scrollable page:

- phoneme chain builder and chain edit actions;
- visual articulation timeline and zoom/playhead controls;
- selected phoneme/timeline item editor;
- word render controls (`Create Word`, `Play Word`, raw chain preview, and `Export Word`);
- word export and send-to-timeline actions;
- performance-oriented controls including voice profile, envelope/formant preview tracks, and musical timing;
- Continuous Mouth Motion diagnostics, validation status, waveform diagnostics, and debug bypass/tuning controls;
- advanced chain cards/source actions;
- saved/list picker areas such as Speech Assets and the CV/VC library.

The biggest usability issue was that unrelated workflows competed vertically. A user could scroll past render controls, diagnostics, timeline graphics, chain cards, and asset pickers in the same page even when they only wanted to build a chain or render a word.

## After structure

The parent tab remains **Articulation Timeline**, but it now contains internal subtabs:

1. **Build** — chain builder actions, live preview, chain cards/source actions, compact Speech Assets sidebar, and CV/VC library.
2. **Visual Timeline** — visual speech timeline, zoom controls, playhead/scrub status, selected timeline item inspector, and word motion preview.
3. **Render / Export** — primary word render actions plus render mode settings.
4. **Performance** — musical timing, voice profile, and read-only articulation envelope/formant track previews.
5. **Advanced** — Continuous Mouth Motion diagnostics, validation output, and verbose/debug status.

This preserves the same callbacks and render settings while separating workflows by intent.

## List picker width policy

Articulation picker/list sidebars use the shared compact width policy:

- minimum width: `220` px;
- preferred width: `300` px;
- maximum width: `380` px.

Speech Assets uses this policy in the Articulation Timeline context so saved/list picker content no longer spans the whole workflow page by default. The Build page gives the active chain editor stretch priority and keeps saved assets in the sidebar.

## Vertical scrolling reduction strategy

- The Build workflow starts with chain actions and live preview rather than burying them below diagnostics.
- Visual timeline content moved to its own page so the graphic and playhead controls are near the top.
- Primary render controls moved to a dedicated Render / Export page so `Play Word`, `Create Word`, and `Export Word` are visible together.
- Performance and musical timing controls moved away from core Build/Render workflows.
- Continuous diagnostics and verbose validation labels moved to Advanced.
- Scroll areas remain inside subtabs where content can still grow, but unrelated workflows no longer share one long scroll stack.

## Contextual inspector plan

The existing selected phoneme/timeline item controls now live next to the visual timeline workflow. Timeline selection continues to use the existing `blockSelected` signal and `_select_articulation_chain_item` / `_refresh_selected_component_controls` path. No new editing behavior was added.

Future refinement can convert the selected controls into a narrower right-side inspector once the timeline page receives a larger split-panel editor.

## Known limitations

- The chain card list can still become tall for very long words; this task keeps it visible and reviewable rather than replacing it with a virtualized list.
- Render buttons appear in both Build and Render / Export contexts so existing workflows remain discoverable while the dedicated render page is introduced.
- GUI geometry is intentionally not pixel-perfect tested; coverage focuses on stable helper policy and existing render/timeline tests.

## Harmony Workbench TODO

Pitch and Harmony Workbench controls are also getting dense, but Task 090 intentionally does not expand Harmony Workbench. A future task may split pitch/harmony controls into a dedicated **Music Theory / Harmony** tab or internal subtabs.
