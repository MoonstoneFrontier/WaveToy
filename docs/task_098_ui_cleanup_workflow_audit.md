# Task 098 UI Cleanup Workflow Audit and Chain Card Variation Plan

## Scope and control classification

WaveToy's current interface is feature rich, but many unrelated actions share the same visual weight. This audit classifies visible controls by purpose so later rearrangement can move tools without removing existing synthesis, export, preset, visualization, or Paulstretch workflows.

### Control categories

| Category | Meaning | Styling direction |
|---|---|---|
| `primary_action` | Main task completion actions such as Create Word, Play Word, Save Project, Export Word. | Limited per panel, clearer accent color, slightly taller than compact secondary controls. |
| `secondary_action` | Local edits such as Add Current, Apply Source, Send to Timeline, duplicate/move. | Compact, neutral, grouped near the object they affect. |
| `transport` | Playback, stop, loop, scrub, zoom-to-playhead style controls. | Consistent transport strip treatment, green/teal accent, never confused with destructive actions. |
| `destructive_action` | Remove, Clear Chain, Reset Whole Chain, delete library entry. | Caution red, placed away from primary flow, confirm when broad. |
| `navigation` | Tabs, sub-tabs, jump buttons, collapsible sections, page selectors. | Compact, flat, consistent selected state. |
| `editor_control` | Sliders, spin boxes, envelopes, curves, graph handles, duration fields. | Dense labels, predictable alignment, compact spacing. |
| `selector` | Combos, pickers, profile/source selectors, note lists. | Size to content; avoid full-width selectors unless browsing lists. |
| `diagnostic` | Validation output, inspectors, meters, analysis summaries. | Subdued, readable, advanced area when not part of primary workflow. |
| `export_import` | Export JSON/WAV, import library entry, save/load dialogs. | Grouped together, separated from edit buttons. |
| `library_asset` | Speech Assets, Wave Explorer entries, palette items, saved recipes. | Card/list style with metadata and explicit add/edit actions. |
| `debug_advanced` | Stop tests, validation toggles, bypasses, deep render diagnostics. | Collapsed by default or visually quiet. |
| `status_only` | Hints, badges, state labels, warnings. | Non-clickable, low visual competition, high contrast. |

## Area-by-area audit

### Global command bar
- **Purpose:** App-level project and workspace entry points.
- **Current controls:** New/load/save project, global toolbar buttons, top workspace navigation.
- **Classification:** Save Project `primary_action`; load/new `export_import`; workspace tabs `navigation`; hints/status `status_only`.
- **Misplaced/duplicated:** Project actions visually compete with local edit/play buttons.
- **Move/collapse/rename/contextual:** Keep project actions together; expose contextual save/export names by current workspace.
- **Density/color issues:** Toolbar buttons are tall and saturated compared with content cards.
- **Suggested future layout:** Slim persistent command bar with a single primary Save/Export affordance and lower-weight workspace navigation.

### Top-level tabs
- **Purpose:** Switch between major workflows.
- **Current controls:** Classic Controls, Articulation Lab/Timeline, Voice Font, Performance Timeline, Graphical Editor, Timeline, Speech Asset Library, Wave Explorer, related pages.
- **Classification:** All tabs `navigation`.
- **Misplaced/duplicated:** Some workflow-specific tools are reachable from multiple tabs with inconsistent names.
- **Move/collapse/rename/contextual:** Keep tabs task-oriented; avoid names that sound like implementation details.
- **Density/color issues:** Tab height and selected-state styling should be calmer and more compact.
- **Suggested future layout:** Group sound design, speech, timeline, and library workflows; use compact selected underline.

### Classic Controls
- **Purpose:** Primary waveform synthesis and classic WaveToy sound design.
- **Current controls:** Wave rows, oscillators, sliders, mute/solo, current sound generation/play/export, tuning and effects controls.
- **Classification:** Generate/play `primary_action` or `transport`; sliders `editor_control`; wave shape selectors `selector`; mute/solo `secondary_action`; export/save `export_import`; meters/status `diagnostic`/`status_only`.
- **Misplaced/duplicated:** Current sound source assignment for phonemes is too far from Chain cards.
- **Move/collapse/rename/contextual:** Keep synthesis controls here, but expose “Current Classic Wave” as a chain-card source selector.
- **Density/color issues:** Many controls are equal weight; sliders and buttons feel bulky.
- **Suggested future layout:** Compact wave rows with local mute/solo, a separated transport/export strip, and source routing shown contextually in speech workflows.

### Articulation Lab
- **Purpose:** Edit and preview individual phoneme articulation and mouth/tract state.
- **Current controls:** Phoneme presets, mouth/tongue/lip sliders, voice/air/noise controls, preview/save/apply controls.
- **Classification:** Preview `transport`; Save/Apply phoneme `primary_action` or `secondary_action`; sliders `editor_control`; presets `library_asset`; source combo `selector`; diagnostics `diagnostic`.
- **Misplaced/duplicated:** Per-phoneme source controls overlap with Chain workflow but were not visible on each chain card.
- **Move/collapse/rename/contextual:** Keep detailed controls here; make card-level source edits possible in Chain.
- **Density/color issues:** Dense controls need clearer section grouping and less button saturation.
- **Suggested future layout:** Left preset/library picker, center articulation controls, right preview/diagnostics.

### Articulation Timeline
- **Purpose:** Build, time, render, inspect, and profile spoken chains.
- **Current controls:** Internal Timeline/Render/Inspector/Profiles subtabs, chain builder, timing canvas, motion previews, render actions.
- **Classification:** Subtabs `navigation`; Create/Play/Export Word `primary_action`; chain edit buttons `secondary_action`; reset/clear `destructive_action`; render modes `selector`; validation `diagnostic`/`debug_advanced`.
- **Misplaced/duplicated:** Timing selection became the effective selection gateway even when Chain cards were visible.
- **Move/collapse/rename/contextual:** Direct card selection and card-local Voice / Wave Variation selectors reduce cross-tab jumping.
- **Density/color issues:** Chain cards had tall buttons and heavy padding.
- **Suggested future layout:** Chain for content/source, Timing / Performance for durations and beat grid, Motion for curves/visemes, Render for output.

### Articulation Timeline → Timeline → Chain
- **Purpose:** Assemble phoneme chain and choose each card's sound source.
- **Current controls:** Add Current, Create Syllable, Clear Chain, Apply Current Wave to Selected/Chain, Reset Selected/Chain Sources, chain cards, CV/VC library.
- **Classification:** Add/Create `secondary_action`/`primary_action`; Clear/Reset Chain `destructive_action`; Apply/Reset Selected `secondary_action`; cards `library_asset` plus `editor_control`; Voice / Wave Variation combo `selector`; Play on card `transport`.
- **Misplaced/duplicated:** Old Apply Wave buttons remain useful as batch fallbacks but should not be the only per-card source path.
- **Move/collapse/rename/contextual:** Keep batch buttons, rename for clarity, and put per-card source selector on each card.
- **Density/color issues:** Reduced card minimum height, padding, and secondary button height in this patch.
- **Suggested future layout:** Card-first workflow: click card, edit source/duration/accent nearby, batch controls in a compact action strip.

### Articulation Timeline → Timeline → Timing / Performance
- **Purpose:** Visual timeline selection, durations, transitions, tempo, singing and beat-grid preview.
- **Current controls:** Speech Timeline Tracks canvas, zoom/fit controls, duration/transition handles, musical timing controls.
- **Classification:** Canvas handles `editor_control`; zoom/fit `navigation`/`editor_control`; playhead scrub `transport`; tempo/snap selectors `selector`; diagnostics `diagnostic`.
- **Misplaced/duplicated:** Timing should synchronize selection, not be required for basic card selection.
- **Move/collapse/rename/contextual:** Selection stays synchronized with Chain cards; advanced beat controls stay here.
- **Density/color issues:** Track area is large by nature; surrounding buttons should be compact.
- **Suggested future layout:** A dedicated timing editor with compact toolbar and collapsed advanced lanes by default.

### Articulation Timeline → Timeline → Motion
- **Purpose:** Inspect continuous mouth motion, visemes, transition curves, and animation-readiness.
- **Current controls:** Motion canvases, viseme timeline, curve toggles, validation summaries.
- **Classification:** Curves/canvases `editor_control`; viseme export previews `diagnostic`; toggles `selector`; validation `debug_advanced`.
- **Misplaced/duplicated:** Motion summaries can update from Chain selection but detailed editing belongs here.
- **Move/collapse/rename/contextual:** Keep motion tools out of Chain except concise selected-card summaries.
- **Density/color issues:** Many visual panels compete; collapse deep diagnostics.
- **Suggested future layout:** One primary motion preview, optional layers below.

### Articulation Timeline → Render
- **Purpose:** Word playback, asset creation, export, render settings.
- **Current controls:** Play Word, Create Word, Export Word, Play Chain, send/save controls, render-mode choices.
- **Classification:** Play/Create/Export `primary_action`; Play Chain `transport`; Send/Save Chain `secondary_action`/`export_import`; render mode `selector`; debug render toggles `debug_advanced`.
- **Misplaced/duplicated:** Playback and export should not mix with low-level chain editing buttons.
- **Move/collapse/rename/contextual:** Keep primary render strip prominent; move debug toggles lower/collapsed.
- **Density/color issues:** Too many equally colorful buttons.
- **Suggested future layout:** Primary render strip, export/import strip, advanced render diagnostics accordion.

### Articulation Timeline → Inspector
- **Purpose:** Analyze current rendered word/source and show waveform/formant/diagnostic details.
- **Current controls:** Source selectors, analysis views, status text, diagnostic output.
- **Classification:** Source combo `selector`; analysis panels `diagnostic`; export analysis `export_import`; status labels `status_only`.
- **Misplaced/duplicated:** Inspector should not duplicate edit controls from Chain.
- **Move/collapse/rename/contextual:** Keep read-only/diagnostic emphasis.
- **Density/color issues:** Diagnostic labels should be subdued and scrollable.
- **Suggested future layout:** Source selector top, compact summary, then collapsible detailed plots.

### Articulation Timeline → Profiles
- **Purpose:** Voice source/profile, CV/VC, character voice and speech-organization controls.
- **Current controls:** Voice profile combo, apply/reset, CV/VC filters, profile descriptions.
- **Classification:** Profile combo `selector`; apply/reset `secondary_action`/`destructive_action`; CV/VC entries `library_asset`; notes `status_only`.
- **Misplaced/duplicated:** Character profiles should not replace direct phoneme controls.
- **Move/collapse/rename/contextual:** Keep profile application separate from card source assignment.
- **Density/color issues:** Profile sections can be flatter and less saturated.
- **Suggested future layout:** Profile source/timing/accent controls grouped separately from phoneme articulation.

### Voice Font
- **Purpose:** Plan/manage voice-source style assets and prompt/recording guidance.
- **Current controls:** Voice source/profile selectors, recording prompt helpers, save/load actions.
- **Classification:** Voice selectors `selector`; save/load `export_import`; prompt list `library_asset`; notes `status_only`.
- **Misplaced/duplicated:** Voice variation names should appear as chain-card options only when backed by existing safe data.
- **Move/collapse/rename/contextual:** Future voice variations can feed the same `available_chain_voice_wave_variations()` surface.
- **Density/color issues:** Needs compact list-card treatment.
- **Suggested future layout:** Voice library left, selected profile editor right, export/import bottom.

### Performance Timeline
- **Purpose:** Arrange clips and performance assets over time.
- **Current controls:** Clip tracks, add/remove, undo/redo, transport, clip edit fields.
- **Classification:** Play/stop/loop `transport`; add clips `secondary_action`; delete clips `destructive_action`; undo/redo `secondary_action`; track handles `editor_control`; save/export `export_import`.
- **Misplaced/duplicated:** Send-to-timeline buttons from speech should land here but not duplicate all timeline editing.
- **Move/collapse/rename/contextual:** Keep performance editing local to selected clip.
- **Density/color issues:** Transport and edit buttons should not share styling.
- **Suggested future layout:** Transport strip, timeline canvas, selected clip inspector.

### Graphical Editor
- **Purpose:** Graphical wave and chain editing.
- **Current controls:** Wave cards/canvases, graphical chain timeline, add/remove wave controls, selection previews.
- **Classification:** Canvas controls `editor_control`; add/remove `secondary_action`/`destructive_action`; selectors `selector`; previews `diagnostic`.
- **Misplaced/duplicated:** Graphical chain selection should sync with Chain cards and Timing selection.
- **Move/collapse/rename/contextual:** Share selected chain index, avoid separate source routing.
- **Density/color issues:** Card colors can be calmer and buttons shorter.
- **Suggested future layout:** Canvas-first, controls in compact contextual sidebars.

### Timeline
- **Purpose:** Audio clip arrangement and palette usage outside speech-specific pages.
- **Current controls:** Audio palette, clip canvas, import/export, transport, trim/stretch handles.
- **Classification:** Transport `transport`; import/export `export_import`; palette `library_asset`; clip handles `editor_control`; destructive clip delete `destructive_action`.
- **Misplaced/duplicated:** Imported audio selection can be a chain-card source only when safe and explicit.
- **Move/collapse/rename/contextual:** Keep source asset selection visible as library context.
- **Density/color issues:** Palette cards and timeline clips need compact metadata.
- **Suggested future layout:** Palette left, timeline center, selected clip inspector right.

### Speech Asset Library
- **Purpose:** Store generated words, phonemes, chain assets, analyses and speech-related records.
- **Current controls:** Asset cards, load/edit/add to timeline, import/export, delete.
- **Classification:** Asset rows `library_asset`; load/add `secondary_action`; delete `destructive_action`; import/export `export_import`; filters `selector`.
- **Misplaced/duplicated:** Library browse controls should not be mixed with Chain edit buttons.
- **Move/collapse/rename/contextual:** Let selected assets surface as source options only if an existing API can route them safely.
- **Density/color issues:** Cards should use less padding and calmer badges.
- **Suggested future layout:** Filter/search top, compact list, selected asset details/actions.

### Wave Explorer
- **Purpose:** Explore generated/imported wave assets and waveform analysis.
- **Current controls:** Wave asset cards, waveform previews, analysis controls, export/import.
- **Classification:** Asset cards `library_asset`; analysis `diagnostic`; selectors `selector`; export/import `export_import`; preview play `transport`.
- **Misplaced/duplicated:** Analysis diagnostics should not compete with source assignment.
- **Move/collapse/rename/contextual:** Expose selected wave assets to Chain later through the variation helper.
- **Density/color issues:** Preview cards can be flatter and visually quieter.
- **Suggested future layout:** Explorer list with preview pane and explicit “Use as chain variation” contextual action.

### Docks
- **Purpose:** Optional diagnostics, side inspectors, library/status panels.
- **Current controls:** Text diagnostics, status summaries, optional analysis views.
- **Classification:** Mostly `diagnostic`, `status_only`, and `debug_advanced`.
- **Misplaced/duplicated:** Dock content can feel like core workflow when too saturated.
- **Move/collapse/rename/contextual:** Start nonessential docks collapsed or clearly optional.
- **Density/color issues:** Text panels need compact typography and subdued backgrounds.
- **Suggested future layout:** Dock title shows purpose and severity; advanced details collapsed.

### Dialogs
- **Purpose:** Save/load/export/import, confirmation, configuration, warnings.
- **Current controls:** File pickers, confirmation buttons, validation warnings.
- **Classification:** Confirm/save `primary_action`; cancel `secondary_action`; destructive confirmation `destructive_action`; warnings `status_only`/`diagnostic`.
- **Misplaced/duplicated:** Destructive actions need consistent caution language.
- **Move/collapse/rename/contextual:** Keep dialogs task-focused with one primary action.
- **Density/color issues:** Use standard compact dialog spacing.
- **Suggested future layout:** Short body text, explicit affected item count, clear primary/cancel/destructive buttons.

### Note picker / music theory dialog
- **Purpose:** Pick notes, intervals, scales, chords, and harmony helpers.
- **Current controls:** Note wheel/list, theory tabs, preview, export/use buttons.
- **Classification:** Note/chord selectors `selector`; preview `transport`; use/apply `primary_action`/`secondary_action`; theory explanations `status_only`; export `export_import`.
- **Misplaced/duplicated:** Music theory actions should remain separate from speech chain source routing.
- **Move/collapse/rename/contextual:** Keep educational diagnostics subdued.
- **Density/color issues:** Wheel/list controls need compact sidebar policy.
- **Suggested future layout:** Compact picker, preview strip, theory details below.

## Visual design cleanup plan

### Immediate direction
- Use smaller default secondary buttons in dense card areas: `UI_BUTTON_HEIGHT_COMPACT = 28`.
- Keep primary actions readable but not oversized: `UI_BUTTON_HEIGHT_PRIMARY = 34`.
- Reduce chain-card padding: `UI_CARD_PADDING_COMPACT = 8` and `UI_SECTION_SPACING_COMPACT = 6`.
- Target compact tabs with `UI_TAB_HEIGHT_COMPACT = 30` in the future.
- Use less saturated neutral secondary controls and reserve strong color for primary/destructive/transport states.
- Make selected states clear through outlines/accent borders rather than full-card high-saturation fills.
- Keep destructive styling red and separate from primary blue and transport green.
- Keep diagnostics purple/subdued and move advanced diagnostics into collapsible sections.

### Proposed constants
- `UI_BUTTON_HEIGHT_COMPACT`
- `UI_BUTTON_HEIGHT_PRIMARY`
- `UI_CARD_PADDING_COMPACT`
- `UI_SECTION_SPACING_COMPACT`
- `UI_TAB_HEIGHT_COMPACT`
- `UI_PRIMARY_ACTION_COLOR`
- `UI_SECONDARY_ACTION_COLOR`
- `UI_DESTRUCTIVE_ACTION_COLOR`
- `UI_TRANSPORT_ACTION_COLOR`
- `UI_DIAGNOSTIC_COLOR`

## Button/tool reclassification rules

- **Primary actions:** Create Word, Play Word, Save Project, Export Word. Limit to one small cluster per panel.
- **Secondary actions:** Add Current, Apply Current Wave to Selected, Apply Current Wave to Chain, Send to Timeline. Keep compact and neutral.
- **Transport actions:** Play, Stop, Loop, scrub, preview. Use consistent transport strip styling.
- **Destructive actions:** Clear Chain, Remove, Reset Chain Sources. Use caution styling and avoid adjacency to primary actions when possible.
- **Diagnostics:** Validate Continuous, Run Stop Test, waveform/formant summaries. Prefer subdued advanced/debug areas.
- **Export/import:** Export JSON/WAV, Import Library Entry, Save Chain. Group together and do not mix with per-card edits.

## Implemented workflow change in Task 098

- Chain cards are directly selectable in the Chain tab.
- The selected card has a stronger outline/accent and stores selected object state.
- Card selection updates the shared `articulation_selected_chain_index`, which continues to sync with Timing / Performance timeline selection.
- Each card exposes a compact `Voice / Wave Variation` selector with at least `Default Voice` and `Current Classic Wave`.
- Mix waves are exposed as existing source options without changing the project or export schema.
- Existing Apply Current Wave to Selected/Chain and Reset Selected/Chain Sources actions remain as fallback/batch operations.
- Selection and source assignment do not render audio; preview/play/render are still explicit user actions.

## Deferred to follow-up tasks

- Full palette replacement.
- Global theme redesign.
- Moving all buttons across all tabs.
- Removing duplicate controls.
- Project schema changes or migrations.
- Any ML voice cloning or measured formant extraction.
