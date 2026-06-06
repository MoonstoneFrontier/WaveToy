# WaveToy UX Reorganization Plan

## Design principles

1. Organize around user goals, not implementation history.
2. Keep universal actions global; keep contextual actions near the selected object.
3. Keep the selected phoneme as the center of speech editing.
4. Preserve all existing features while changing layout in small, reversible steps.
5. Collapse advanced diagnostics by default without removing them.
6. Make storage and project state visible, explicit, and safe.

## Proposed future workspace architecture

### Top-level workspaces

| Future workspace | Replaces / absorbs | User goal |
|---|---|---|
| Start / Voice | Voice landing content, basic first-run guidance | Start a sound or speech workflow. |
| Sound Design | Voice Lab, Wave Explorer, Graphical Editor | Create and shape waves, stereo motion, pitch, and texture. |
| Speech Builder | Articulation Lab, Articulation Timeline Chain/Timing/Render/Motion, selected phoneme controls | Build phoneme chains, assign source variations, preview, and render words. |
| Arrangement | Timeline and clip-level editing | Arrange audio and speech assets into lanes and render a mix. |
| Assets | Speech Asset Library, Speech Assets drawers, voice/wave/profile libraries | Find, load, duplicate, tag, import, and export reusable assets. |
| Settings | Storage/data directory, project/recovery state, advanced preferences | Manage project storage and app behavior safely. |
| Advanced / Diagnostics | Inspector, Speech Diagnostics dock, waveform/formant analysis, continuous validation | Inspect, debug, and tune advanced speech/synthesis behavior. |

### Workspace-local navigation

- Sound Design modes: **Classic**, **Explorer**, **Graphical**, **Presets**.
- Speech Builder modes: **Build Chain**, **Selected Phoneme**, **Timing**, **Render**, **Motion**, **Profiles**, **Advanced Inspector**.
- Arrangement modes: **Clips**, **Lanes**, **Automation**, **Mix Render**.
- Assets modes: **All Assets**, **Speech**, **Audio**, **Profiles**, **Analyses**, **Imports/Exports**, **Voice Font Planning**.
- Settings modes: **Storage**, **Projects**, **Recovery**, **Shortcuts**, **Advanced**.

## Recommended action hierarchy

### Global shell

Keep globally visible:

- Active workspace indicator.
- Project dirty/status indicator.
- Current data directory shortcut/status.
- Universal Stop.
- Help.

Conditionally keep only if status text is explicit:

- Play active workspace.
- Loop active workspace.

Move out of the global toolbar:

- `Render / Create` → workspace render/create toolbar.
- `Add to Timeline` → Sound Design, Speech Builder, and Asset card contextual actions.
- `Save / Export` → explicit Save Project, Save Asset, Export Audio, Export Word, Export Mix.
- `Reset` → explicit contextual destructive actions.

This is the core **global toolbar simplification**: global actions must be universal, predictable, and low-risk.

## Proposed Speech Builder / articulation workflow

### Primary user goal

> Click phoneme, assign voice variation, adjust timing, preview, render.

### Target layout

```
Speech Builder
├─ Left: Phoneme source/preset drawer
│  ├─ Vowels / Consonants / CV-VC combinations
│  └─ Saved phonemes
├─ Center: Chain cards + visual speech timeline
│  ├─ Card: phoneme / IPA / source / duration / transition
│  ├─ Quick play
│  ├─ Compact source selector
│  └─ Move / duplicate / delete
└─ Right: Selected Phoneme Workbench
   ├─ Source
   ├─ Timing
   ├─ Expression
   ├─ Actions
   └─ Advanced
```

### Selected Phoneme Workbench requirements

#### Source

- Voice/wave variation selector.
- Current source badge.
- Apply source to selected.
- Apply source to remaining chain.
- Reset selected source.
- Open source details.

#### Timing

- Duration.
- Transition/crossfade.
- Offset/pause.
- Link to Timing / Performance for tempo and singing preview.

#### Expression

- Stress and intensity.
- Voice source pitch/strength when applicable.
- Mouth/tongue/lip/nasal/airflow emphasis.

#### Actions

- Play selected.
- Duplicate.
- Remove.
- Move left/right.
- Save selected phoneme.
- Send selected phoneme to assets/timeline.

#### Advanced

- Motion curves.
- Source metadata.
- Analysis/debug links.

### Source assignment workflow

Current source assignment should be reframed as one clear workflow:

```
Select chain card
→ Choose voice/wave source in Selected Phoneme Workbench
→ Apply to selected, remaining chain, or whole chain
→ Card updates source badge immediately
→ Preview selected or play chain
→ Render word
```

Rules:

- The selected card is the default scope.
- Whole-chain actions require clear labels and confirmation if destructive/resetting.
- Per-card source selector is a compact shortcut, not a separate source model.
- Current Unsaved Voice Lab Sound is a source option, but users should not have to leave Speech Builder just to understand what is assigned.

## Proposed timeline workflow

Separate **speech-chain authoring** from **arrangement**.

Current problem:

```
Speech Builder creates a word
→ Send Word / Phoneme / Chain to Timeline
→ Timeline also has Speech Assets drawer
→ Global Add to Timeline may do something else depending active tab
```

Future flow:

```
Speech Builder: Render Word
→ Save as Speech Asset
→ Add to Arrangement (explicit)
→ Arrangement opens with new clip selected
→ Timeline toolbar handles clip move/trim/stretch/split/render mix
```

Arrangement actions should be clip-centric:

- Import sounds.
- Add speech/audio asset.
- Move/trim/stretch/split/delete/duplicate clip.
- Add lane / voice lane.
- Render mix.
- Export last mix.

## Proposed asset library workflow

Unify asset discovery around user intent.

```
Assets workspace
├─ Search and filters always visible
├─ Asset type chips: Audio, Speech, Phonemes, Chains, Words, Profiles, Analyses, Imports
├─ Selected asset preview/details panel
├─ Primary action changes by asset: Load / Add to Speech Builder / Add to Arrangement / Play
└─ Secondary actions: Rename, Duplicate, Favorite, Tags/Notes, Import, Export, Delete
```

Quick wins:

- Rename `Speech Asset Library` to `Assets` after adding explanatory headings.
- Keep Timeline drawers but treat them as asset pickers, not full library management.
- Keep File → Import/Export Library Entry for power users, but surface import/export in Assets.

## Proposed storage/settings workflow

Create **Settings → Storage**.

```
Storage Settings
├─ Current data directory
│  ├─ Path
│  ├─ Source: environment override / saved config / platform default
│  ├─ Open Data Directory
│  ├─ Change Data Directory
│  └─ Reveal Recovery Folder
├─ Project
│  ├─ Current project path
│  ├─ Dirty state
│  ├─ Save Project
│  └─ Save Project As
├─ Recovery
│  ├─ Last recovery path
│  └─ Open Recovery Folder
└─ Migration Wizard
   ├─ Choose source root
   ├─ Choose destination root
   ├─ Copy files
   ├─ Verify
   └─ Switch active root
```

The storage/data directory UX should clearly distinguish app data, project files, audio exports, library entries, and recovery files.

## Proposed diagnostics workflow

Move diagnostics behind clear advanced entry points:

- View → Speech Diagnostics remains.
- Speech Builder → Advanced Inspector drawer links to waveform, formant, source metadata, motion validation, continuous renderer tests.
- Normal users see only high-level status and warnings.

## Staged roadmap for Tasks 102-110

### Task 102 — Selected Phoneme Workbench Rebuild

Purpose: Move source/timing/expression/actions into one focused selected-phoneme panel.

Deliverables:

- Workbench UI panel in Speech Builder/Articulation Timeline.
- Preserve existing callbacks for apply source, play selected, duplicate/remove/move where available.
- Tests for source assignment workflow remain passing.

### Task 103 — Chain Card Compact Action Redesign

Purpose: Make chain cards self-contained, compact, and source-aware.

Deliverables:

- Card layout shows phoneme, source, duration, transition.
- Quick play, compact source selector, move/delete/duplicate controls.
- Selected card state visually clear.

### Task 104 — Global Toolbar Simplification

Purpose: Remove ambiguous context actions from global bar and keep only universal actions.

Deliverables:

- Global toolbar contains only predictable actions.
- Context render/save/export/add-to-timeline actions move to workspace toolbars.
- `Reset` replaced by contextual destructive actions.

### Task 105 — App-Wide Visual Density Pass

Purpose: Reduce button sizes, card padding, saturation, and excessive borders.

Deliverables:

- Primary/secondary/destructive/diagnostic styles consistently applied.
- Long helper text moved to compact hints or collapsible help.
- Touch target minimums preserved for primary/transport controls.

### Task 106 — Asset Library Workflow Redesign

Purpose: Make saved voices, waves, words, and chains discoverable and reusable.

Deliverables:

- Assets workspace/action model.
- Timeline drawers become lightweight pickers.
- Asset details panel shows path/source/provenance and contextual actions.

### Task 107 — Storage Settings and Migration Wizard

Purpose: Expose data directory and guided migration clearly.

Deliverables:

- Settings → Storage page.
- Visible data root, source, project path, recovery status.
- Copy/verify migration wizard without destructive deletion.

### Task 108 — Timeline Workflow Simplification

Purpose: Clarify arrangement vs speech-chain workflows.

Deliverables:

- Arrangement toolbar organized by clip tasks.
- Speech Builder sends explicit rendered assets to Arrangement.
- Global Add to Timeline no longer required.

### Task 109 — Inspector and Diagnostics Triage

Purpose: Move debug/diagnostic tools behind advanced drawers.

Deliverables:

- Inspector controls categorized as waveform, formant, source metadata, motion, runtime.
- Advanced drawer defaults collapsed.
- View menu entry retained for diagnostics dock.

### Task 110 — First-Time User Guided Workflow

Purpose: Add onboarding path for creating first voice, phoneme chain, and word.

Deliverables:

- Guided checklist: create sound → add phoneme → assign source → play selected → render word → save asset → add to arrangement.
- Non-modal hints that can be dismissed.
- No new synthesis behavior.

## Implementation sequencing notes

1. Do Task 102 before visual-density work so the primary speech workflow has a stable target.
2. Do Task 103 immediately after Task 102 because chain cards and workbench selection are coupled.
3. Do Task 104 before Task 108 so global/context action ownership is clear.
4. Do Task 106 before Task 110 so onboarding can point to the final asset model.
5. Do Task 107 independently; avoid coupling storage migration to UI rearrangement.
6. Do Task 109 before or alongside Task 105 to avoid polishing debug controls that will become collapsed.
