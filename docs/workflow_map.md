# WaveToy Workflow Map — Task 101

This document maps primary workflows from the current UI to a proposed future path. Click counts are practical estimates for a user starting from an arbitrary tab with no modal dialogs open. They are approximate because tab position, current selection, saved state, and menu shortcuts can vary.

## Legend

- `Tab` means changing a top-level tab or major subtab.
- `Click` means button, card, menu item, or selection.
- Proposed paths assume the future architecture from `docs/wavetoy_ux_reorganization_plan.md`.

## 1. Create a basic sound

Current path:

```
Classic Controls
→ adjust wave shape/pitch/stereo/texture sliders
→ ▶ Play or global Play
→ Save Audio if needed
```

Estimated current cost: 1 tab if not already there, then many control adjustments, 1 play click.

Hunt points:

- Classic Controls, Wave Explorer, and Graphical Editor all support sound design with overlapping controls.
- Global `Render / Create` and Classic `▶ Play` can feel like competing primary actions.

Recommended future path:

```
Sound Design
→ choose Classic / Explorer / Graphical mode
→ adjust sound
→ Play Sound
→ Export Audio or Save as Asset
```

Quick win: add a Sound Design heading and keep play/export local.

Larger refactor: merge Classic, Wave Explorer, and Graphical Editor under one Sound Design workspace.

## 2. Save a sound

Current path:

```
Classic Controls or Wave Explorer
→ Save Audio / Save
```

Alternative current path:

```
Global command bar
→ Save / Export
```

Estimated current cost: 1-2 clicks after sound creation.

Hunt points:

- `Save / Export` is ambiguous: project, audio, asset, word, or mix?
- File menu project save actions are separate from audio export.

Recommended future path:

```
Sound Design
→ Export Audio or Save Sound Asset
```

Quick win: rename local buttons and tooltips to distinguish `Export Audio` from `Save Project`.

Larger refactor: asset-save flow in Assets workspace.

## 3. Create a voice/wave variation

Current path:

```
Classic Controls / Wave Explorer / Graphical Editor
→ adjust wave layers and pitch/stereo/texture
→ optionally use Articulation Lab Apply Current Wave or Articulation Timeline Apply Current Wave actions
```

Estimated current cost: 1-3 tabs plus source apply click.

Hunt points:

- The variation is created in sound-design tabs but assigned in speech tabs.
- Users must know that Current Classic Wave can be used as an articulation source.

Recommended future path:

```
Sound Design
→ Save as Voice/Wave Source Variation
→ Speech Builder Selected Phoneme Workbench → Source selector
```

Quick win: document Current Classic Wave as a source option in source-assignment sections.

Larger refactor: dedicated source variation asset type/picker in Assets/Speech Builder.

## 4. Build a phoneme chain

Current path:

```
Articulation Lab
→ choose phoneme preset or edit current phoneme
→ Add to Articulation Timeline
→ Articulation Timeline → Timeline → Chain
→ repeat Add Current / chain card actions
```

Estimated current cost: 2 top-level tabs plus repeated add clicks.

Hunt points:

- `Articulation Lab` and `Articulation Timeline` sound related but separate preset/edit and chain-building tasks.
- `Add Current` exists in the Chain subtab, while presets live elsewhere.

Recommended future path:

```
Speech Builder
→ phoneme drawer selects preset
→ Add to Chain
→ chain card appears selected
```

Quick win: cross-link Articulation Lab and Chain with clearer labels.

Larger refactor: put phoneme drawer, chain cards, and Selected Phoneme Workbench in one Speech Builder screen.

## 5. Assign voice variation per phoneme

Current path:

```
Articulation Timeline → Timeline → Chain
→ select chain card
→ Wave Source group
→ Apply Current Wave to Selected
```

Alternative current path:

```
Articulation Lab
→ Apply Current Wave to current phoneme
→ Add to Articulation Timeline
```

Estimated current cost: 1-3 tabs depending whether the source is already prepared; 2-4 clicks after source creation.

Hunt points:

- Source assignment workflow is split between current phoneme and selected chain item.
- Whole-chain source controls sit beside selected-only controls.
- Per-card source state is visible but not the main editing home.

Recommended future path:

```
Speech Builder
→ select chain card
→ Selected Phoneme Workbench → Source
→ choose voice/wave variation
→ Apply to selected / remaining chain / whole chain
```

Quick win: group source controls under one visible heading and explain selected vs whole-chain scope.

Larger refactor: Selected Phoneme Workbench source section with compact card source selectors.

## 6. Play selected phoneme

Current path:

```
Articulation Lab → Play Phoneme
```

or

```
Articulation Timeline → select visual timeline block/card
→ selected controls or saved phoneme card Play where applicable
```

Estimated current cost: 1-2 tabs plus selection/play.

Hunt points:

- Current phoneme preview and selected chain phoneme preview are conceptually different.
- Global Play may not mean selected phoneme.

Recommended future path:

```
Speech Builder
→ select chain card
→ Selected Phoneme Workbench → Play Selected
```

Quick win: label current vs selected preview explicitly.

Larger refactor: make selected card drive all workbench actions.

## 7. Play full word

Current path:

```
Articulation Timeline → Timeline/Chain or Render
→ ▶ Play Word
```

Estimated current cost: 1-2 tabs, 1 click.

Hunt points:

- Play Word, Play Chain, Play Word Motion, global Play, and timeline Play all coexist.

Recommended future path:

```
Speech Builder
→ Render toolbar → Play Word
```

Quick win: separate Chain Preview from Rendered Word Preview in labels.

Larger refactor: render result panel with Play, Save, Export, Add to Arrangement.

## 8. Render/export word

Current path:

```
Articulation Timeline → Render or Chain action area
→ Create Word
→ Export Word or Send Word to Timeline
```

Estimated current cost: 1-2 subtabs, 1-3 clicks.

Hunt points:

- `Create Word` sounds like asset creation but also implies render.
- Export Word, Save Chain, Send Word, Send Chain, and Send Phoneme are adjacent.

Recommended future path:

```
Speech Builder
→ Render Word
→ result panel: Play / Save Speech Asset / Export Audio / Add to Arrangement
```

Quick win: add a short render flow label.

Larger refactor: dedicated render result panel.

## 9. Inspect waveform

Current path:

```
Articulation Timeline → Inspector
→ waveform analysis controls
→ Save Waveform Analysis if needed
```

Estimated current cost: 1 tab/subtab plus 1-2 clicks.

Hunt points:

- Normal speech creation users see analysis controls as peer workflows.

Recommended future path:

```
Speech Builder or Sound Design
→ Advanced Inspector
→ Waveform Analysis
```

Quick win: collapse analysis save/load controls.

Larger refactor: Diagnostics/Advanced workspace.

## 10. Inspect formants/resonance

Current path:

```
Articulation Timeline → Inspector
→ Save Formant Analysis / Load Analysis Metadata
```

or

```
View → Speech Diagnostics
→ Voice Box / Resonance controls
```

Estimated current cost: 1 menu/tab plus 1-2 clicks.

Hunt points:

- Formant analysis and resonance control are in different places.

Recommended future path:

```
Advanced / Diagnostics
→ Formants & Resonance
```

Quick win: cross-link Inspector and Speech Diagnostics dock.

Larger refactor: one Diagnostics workspace/drawer.

## 11. Edit timing/performance

Current path:

```
Articulation Timeline → Timeline → Open Timing / Performance
→ Timing / Performance subtab
→ adjust tempo/beat/snap/singing/performance controls
```

or

```
Performance Timeline tab
→ automation track tables/canvas
```

Estimated current cost: 1-2 tabs plus edits.

Hunt points:

- Timing lives partly in speech subtabs and partly in Performance Timeline.
- Millisecond timing and future musical timing concepts are adjacent.

Recommended future path:

```
Speech Builder
→ Selected Phoneme Workbench → Timing for selected phoneme
→ Timing / Performance for chain-level tempo and automation
```

Quick win: keep the Timing / Performance shortcut and clarify what it controls.

Larger refactor: merge selected timing into Workbench and chain timing into Speech Builder timing mode.

## 12. Arrange clips on timeline

Current path:

```
Timeline
→ Import Sounds or Speech Assets drawer
→ drag/add clips
→ select tool: Select/Move, Trim, Time Stretch, Split, Delete
→ Render Mix
```

Estimated current cost: 1 tab plus asset selection/import and clip edits.

Hunt points:

- Speech Builder also has Send Word/Phoneme/Chain to Timeline.
- Global Add to Timeline duplicates context actions.

Recommended future path:

```
Arrangement
→ Add Audio/Speech Asset
→ edit clips/lane
→ Render Mix
```

Quick win: rename Timeline heading to Arrangement in-page before tab rename.

Larger refactor: remove global Add to Timeline and use asset-context actions.

## 13. Save/open project

Current path:

```
File → New/Open/Save/Save As
→ project path label updates in shell
```

Estimated current cost: 1 menu plus action.

Hunt points:

- Project saving is separate from app data directory visibility.
- `Save / Export` global button may be confused with project save.

Recommended future path:

```
File menu for shortcuts
+ Start/Settings project panel for visible project state
```

Quick win: project status label remains visible; tooltip explains File menu save.

Larger refactor: Settings → Project section.

## 14. Find saved assets

Current path:

```
Speech Asset Library
→ search/category/sort
→ table selection
→ Load/Rename/Duplicate/Delete/Favorite/Tags/Notes/Import/Export/Save Profiles
```

Alternative current path:

```
Timeline → Speech Assets drawer
```

Estimated current cost: 1 tab, then search/filter/select/action.

Hunt points:

- Full asset management and lightweight timeline picking use different surfaces.
- File/Library menus duplicate import/export/refresh/profile actions.

Recommended future path:

```
Assets
→ search/filter
→ select asset
→ contextual primary action: Load / Add to Speech Builder / Add to Arrangement / Play
```

Quick win: clarify the Library tab as the source of truth and drawers as pickers.

Larger refactor: Assets workspace with asset details panel.

## 15. Change data directory

Current path:

```
File → Change Data Directory
```

Related current actions:

```
File → Open Data Directory
File → Reveal Recovery Folder
project path label in shell
```

Estimated current cost: 1 menu action, plus dialog.

Hunt points:

- Storage/data directory UX is hidden in File menu.
- Users do not see a storage settings section, migration status, or data-root source explanation.

Recommended future path:

```
Settings → Storage
→ Current data directory
→ Change Data Directory or Migration Wizard
```

Quick win: add a visible current data directory section in docs/tooltips before implementing UI.

Larger refactor: Task 107 Storage Settings and Migration Wizard.

## Workflow priority table

| Workflow | Current tab/menu count | Proposed tab/workspace count | Priority | Main fix |
|---|---:|---:|---|---|
| Assign voice variation per phoneme | 2-3 | 1 | Highest | Selected Phoneme Workbench Source section. |
| Build phoneme chain | 2 | 1 | Highest | Put phoneme drawer and chain cards together. |
| Play selected phoneme | 1-2 | 1 | High | Selection-driven Play Selected. |
| Render/export word | 1-2 | 1 | High | Render result panel. |
| Edit timing/performance | 1-2 | 1 | High | Workbench Timing + chain Timing mode. |
| Arrange clips | 1-2 | 1 | Medium | Arrangement workspace and contextual Add. |
| Find saved assets | 1-2 | 1 | Medium | Assets workspace as source of truth. |
| Change data directory | menu-only | 1 Settings workspace | Medium | Storage settings/migration. |
| Inspect diagnostics | 1-2 | Advanced drawer/workspace | Medium | Inspector triage. |
| Create basic sound | 1-3 | 1 | Medium | Sound Design workspace. |

## Proposed first implementation path

```
Task 102 Selected Phoneme Workbench
→ Task 103 Compact Chain Cards
→ Task 104 Global Toolbar Simplification
→ Task 105 Visual Density Pass
→ Task 106 Asset Library Workflow
→ Task 107 Storage Settings and Migration Wizard
→ Task 108 Timeline Workflow Simplification
→ Task 109 Inspector and Diagnostics Triage
→ Task 110 First-Time User Guided Workflow
```
