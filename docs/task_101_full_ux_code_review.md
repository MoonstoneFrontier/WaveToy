# Task 101 — Full UX Code Review and Workflow Reorganization Plan

## Executive summary

WaveToy has reached a strong feature depth, but the current interface is organized around implementation history rather than user intent. The main window now mixes sound design, phoneme editing, speech-chain building, timeline arrangement, diagnostics, asset storage, and future voice-font planning in a single tab strip. The global command bar attempts to normalize access to common actions, but several of its commands are context-dependent and ambiguous, so users still need to understand which tab owns the current action.

The highest-priority UX problem is the articulation workflow. The core user goal is simple: **click a phoneme, assign a voice/wave variation, adjust timing, preview, then render**. In the current UI this path crosses Articulation Lab, Articulation Timeline → Timeline → Chain, Timing / Performance, Render, Motion, Inspector, Profiles, Speech Assets, and sometimes Voice Lab or Wave Explorer when the source is the current waveform. Source assignment exists in multiple forms: current phoneme controls, chain-level buttons, per-card badges/selectors, and current-wave actions. The result is powerful but hard to learn.

This task intentionally makes no runtime changes. The recommended next step is to rebuild the articulation workflow around a **Selected Phoneme Workbench** that keeps source, timing, expression, and actions in one contextual panel while preserving compact chain cards for quick selection and direct source changes. The broader plan is to reduce global toolbar scope, split workspaces by user goal, collapse advanced/diagnostic controls, and make storage/project state visible as a settings/workspace concern.

## Evidence reviewed

- Main window construction and tab insertion order in `wave_toy.py`.
- Global command bar actions and callbacks.
- File, Library, Edit, View, and Help menu actions.
- Voice Lab, Voice, Wave Explorer, Graphical Editor, Articulation Lab, Articulation Timeline, Performance Timeline, Timeline, Speech Asset Library, and Voice Font construction.
- Speech diagnostics dock, profile controls, storage resolution, and project/data-directory actions.
- Existing regression tests around articulation chain source assignment, storage directory resolution, scroll capture, and UI control classification.

## Top 10 UX problems

1. **Articulation actions are split across too many places.** Source assignment, timing, preview, render, chain editing, and diagnostics live in separate panels and subtabs, forcing users to hunt.
2. **The global command bar is over-scoped.** `Render / Create`, `Add to Timeline`, `Save / Export`, and `Reset` are context-dependent and can mean different things per tab.
3. **Tab names mix product concepts and implementation concepts.** `Articulation Lab`, `Articulation Timeline`, `Performance Timeline`, and `Timeline` are meaningful to developers but not clearly separated for users.
4. **Primary and secondary actions compete visually.** Many buttons share large, saturated story-button styling even when they are secondary, advanced, or diagnostic.
5. **Advanced/debug controls appear beside everyday workflows.** Continuous tuning validation, stop tests, inspector analysis, voice-box/resonance controls, and export-debug actions can crowd normal speech creation.
6. **Source assignment has no single home.** Users can apply the current wave to a current phoneme, selected chain card, or whole chain, while chain cards also show source badges and saved assets carry their own source metadata.
7. **Render/play actions are duplicated.** The app has global play/loop/stop, Voice Lab play/loop/stop, phoneme preview, word/chain playback, motion preview, timeline playback, and rendered mix playback.
8. **Saved assets are discoverable only after learning storage vocabulary.** Speech Assets, Speech Asset Library, File import/export entry actions, library menu actions, and Timeline drawer assets all expose overlapping concepts.
9. **Storage/data-directory state is visible but not actionable enough.** Users see project/data status and File menu data-directory commands, but there is no coherent storage settings page or migration workflow.
10. **Scroll and focus policies are improving but need a documented exception model.** Passive wheel widgets and no-wheel combos reduce accidental capture, yet tables, text edits, and picker panels need predictable local-scroll exceptions.

## Top 10 quick wins

1. Rename future user-facing workspaces around tasks: **Sound Design**, **Speech Builder**, **Arrangement**, **Assets**, and **Settings**.
2. Add a visible heading in Articulation Timeline Chain: **Selected Phoneme Workbench** with source assignment workflow notes before moving controls.
3. Label global buttons with current context in tooltips/status text, especially `Render / Create`, `Save / Export`, and `Reset`.
4. Group current articulation source buttons under a single **Source Assignment** heading wherever they remain.
5. Move or mark advanced controls in docs as future collapsed drawers: Continuous validation, Stop Test, Runtime Inspector, waveform/formant metadata tools.
6. Standardize action labels: use `Play Selected`, `Play Chain`, `Render Word`, `Export Word`, `Save Chain`, `Send to Timeline` instead of mixing Create/Render/Save.
7. Add one persistent **Current data directory** row in the future Settings/Storage workspace, with Open, Change, and Reveal Recovery actions.
8. Make per-chain-card summaries consistently show phoneme, source, duration, and transition.
9. Use separate visual treatments for primary action, secondary action, destructive action, diagnostic action, and status display.
10. Add static doc tests to ensure Task 101 planning docs keep mentioning Selected Phoneme Workbench, source assignment workflow, global toolbar simplification, storage/data directory UX, and tasks 102-110.

## Top 10 larger refactors

1. **Task 102 — Selected Phoneme Workbench Rebuild.** Combine source, timing, expression, actions, and advanced controls for the selected chain phoneme.
2. **Task 103 — Chain Card Compact Action Redesign.** Make chain cards self-contained, compact, source-aware, and directly selectable.
3. **Task 104 — Global Toolbar Simplification.** Keep only universal commands globally; move context-specific commands into workspace toolbars.
4. **Task 105 — App-Wide Visual Density Pass.** Reduce oversized buttons, high saturation, card padding, repeated headers, and long always-visible helper text.
5. **Task 106 — Asset Library Workflow Redesign.** Merge saved voices, waves, words, chains, imports, and profiles into an intent-based library model.
6. **Task 107 — Storage Settings and Migration Wizard.** Add storage settings, current root visibility, migration copy/verify, and safer prompts.
7. **Task 108 — Timeline Workflow Simplification.** Clearly separate speech-chain authoring from audio arrangement.
8. **Task 109 — Inspector and Diagnostics Triage.** Put waveform/formant/debug/profiling tools behind advanced drawers or View menu panels.
9. **Task 110 — First-Time User Guided Workflow.** Add a beginner path for making a first sound, phoneme chain, word, and timeline clip.
10. Later modularization: after UX stabilizes, split `wave_toy.py` UI builders by workspace without changing behavior.

## Risk assessment

| Area | Risk | Why it matters | Mitigation |
|---|---|---|---|
| Playback lifecycle | High | Global/local play, loop, stop, live preview, and render paths are intertwined. | Avoid playback refactors until a dedicated audio lifecycle task; keep Task 102 focused on layout only. |
| Project/schema compatibility | High | Assets, projects, chains, visemes, performance tracks, and storage metadata are persisted. | Do not change schema during UI moves; keep existing callbacks and data fields. |
| Articulation source assignment | High | Per-phoneme source metadata directly affects rendered words. | Preserve current callbacks; add tests around selected/chain apply behavior before moving controls. |
| User discoverability | Medium | Renaming tabs may help new users but disorient existing users. | Stage names with headings/tooltips first, then rename tabs in a later task. |
| Visual density changes | Medium | Reducing sizes can hurt touch-friendly operation. | Keep minimum touch target for primary/transport controls; collapse only advanced/secondary sections. |
| Asset library consolidation | Medium | Users may rely on current Speech Assets and Library separation. | Keep both entry points initially; cross-link and progressively unify. |
| Storage migration | High | Incorrect migration could lose user data. | Build read-only audit and copy/verify wizard before any delete/move options. |
| Diagnostics relocation | Low-medium | Advanced users may lose quick access. | Keep View menu and collapsible drawers; never remove diagnostics. |

## Current tab-structure review

| Current tab | User-facing clarity | Main issue | Recommended future form |
|---|---:|---|---|
| Voice | Medium | Entry tab name is broad; overlaps future voice-source/profile concepts. | Sound Design home or simplified Start workspace. |
| Voice Lab | Medium | Clear to existing users but implementation-oriented; dense mixer/synth controls. | Sound Design → Classic/Advanced Controls section. |
| Wave Explorer | Medium-high | Goal is visual exploration, but it also exposes editing/preset workspaces. | Sound Design → Explorer workspace. |
| Graphical Editor | High | User can infer direct manipulation, but it duplicates Voice Lab. | Sound Design → Graphical Editor mode. |
| Articulation Lab | Medium | Good concept, but current phoneme editing is disconnected from chain work. | Speech Builder → Phoneme Design drawer/panel. |
| Articulation Timeline | Low-medium | Highest-value speech workflow but name sounds technical and overlaps Timeline. | Speech Builder primary workspace. |
| Performance Timeline | Low-medium | Timing automation is valuable but not clearly tied to speech or arrangement. | Speech Builder → Timing/Performance or Arrangement → Automation depending context. |
| Timeline | High | Clear for arranging clips, but speech-chain actions also send here. | Arrangement workspace. |
| Speech Asset Library | Medium | Useful but partly overlaps Timeline speech drawer and File/Library menu. | Assets workspace. |
| Voice Font | Medium | Future planning space; not yet a production workflow. | Assets/Profiles → Voice Font planning, advanced/future drawer. |

## Articulation workflow review — highest priority

### Current pain points

- Phoneme preset selection and current phoneme editing happen in Articulation Lab, while chain construction and selected chain-card actions happen in Articulation Timeline.
- Source assignment is split between current phoneme controls, selected chain actions, whole-chain actions, and per-card state display.
- `Play Phoneme`, `Play Word`, `Play Chain`, motion preview, and global play all coexist without a single action hierarchy.
- Timing/performance controls are pushed to a separate Timing / Performance subtab, while selected phoneme controls remain in the Timeline subtab.
- Render/export/save chain controls live near chain controls but are semantically separate from editing the selected phoneme.
- Inspector and advanced motion tools compete with common tasks when a user only wants to assign a voice variation and render a word.

### Target layout concept

Create a **Selected Phoneme Workbench** inside the Speech Builder workspace.

Sections:

1. **Source**
   - Voice/wave variation selector.
   - Source badge and source detail summary.
   - Apply source to selected.
   - Apply source to remaining chain.
   - Reset selected source.
2. **Timing**
   - Duration.
   - Lead/transition length.
   - Micro pause / stretch controls.
   - Link to Timing / Performance for beat/measure tools.
3. **Expression**
   - Stress, intensity, mouth openness, nasal/airflow emphasis, pitch/voice-source accents.
4. **Actions**
   - Play selected.
   - Duplicate.
   - Remove.
   - Move left/right.
   - Add/send selected to assets/timeline where appropriate.
5. **Advanced**
   - Source metadata details.
   - Motion/debug toggles.
   - Analysis/profiling links.

Chain cards should always show:

- Phoneme name and IPA.
- Voice/wave source.
- Duration.
- Transition.

Chain cards should support:

- Direct selection.
- Quick play.
- Compact source selector.
- Compact move/delete actions.

## Global command bar review

The global command bar is useful for universal transport and help, but current context-sensitive actions make users ask: “What will this do from here?” The future global bar should keep:

- Play/Stop only if behavior is clearly tied to the active workspace.
- Project dirty/status indicator.
- Current data directory/status shortcut.
- Help.

Move these into workspace toolbars:

- Render / Create.
- Add to Timeline.
- Save / Export.
- Reset, unless replaced with explicit `Reset current sound`, `Clear chain`, or `Reset timeline view` actions in context.

`Reset` is especially dangerous globally because destructive scope changes per tab.

## Visual-density review

| Element | Classification | Recommendation |
|---|---|---|
| Large story buttons | too_large / too_colorful | Reserve for primary workspace actions; use compact buttons for secondary actions. |
| Chain action groups | redundant / should_be_contextual | Move selected-only actions into Selected Phoneme Workbench. |
| Continuous motion controls | advanced_debug / should_be_collapsed | Collapse under Advanced Motion. |
| Inspector waveform/formant save/load | diagnostic / should_be_collapsed | Keep in Inspector advanced drawer. |
| Repeated workflow helper text | redundant | Replace long always-visible text with short current-step summaries. |
| Picker/list panels | too_wide in some contexts | Keep sidebar width policy and avoid stretching picker panels across workflow pages. |
| Saturated per-action colors | too_colorful | Use color primarily for category/danger/transport, not every button. |
| Tab strip | misplaced emphasis | Fewer top-level tabs; use workspace-local drawers. |

## Scroll and focus review

Recommended passive wheel policy:

- Combo boxes should not change value on accidental wheel unless explicitly focused/open.
- Tables and text edits should be passive when embedded in page scroll, except when their content area is intentionally scrollable and hovered/focused.
- Asset lists and picker panels may scroll locally because browsing lists is their primary purpose.
- Timeline canvases should keep local wheel/drag behavior because zooming and navigation are direct manipulation actions.
- Long form pages should prefer a single outer `WaveToyScrollArea` to reduce nested scroll traps.

Known local-scroll exceptions:

- Timeline canvas and arrangement lanes.
- Asset library table when browsing many assets.
- Speech asset cards inside timeline drawers.
- Wave Explorer visual dashboard panels where direct manipulation is expected.

## Storage and project UX review

Current storage behavior is technically sound but not yet user-centered. The app resolves a data root from environment override, saved config, or platform default, then creates Projects, Assets, Exports, Cache, Recovery, LegacyImports, Audio, Voices, Words, Phonemes, Animations, and Visemes. Users can open/change the data directory and reveal recovery from the File menu, and a project path label is visible in the main shell.

Future storage UX should provide:

- A **Settings → Storage** page.
- Visible current data directory with source: environment override, saved config, or platform default.
- Buttons: Open Data Directory, Change Data Directory, Reveal Recovery Folder.
- Guided migration: choose old root, choose new root, copy, verify counts/checksums, then optionally switch.
- Safer project save prompts that distinguish `Save Project`, `Save Project As`, `Export Audio`, and `Export Library Entry`.
- A recovery status section showing last autosave/recovery location.

## Conclusion

The next implementation should not start by moving random buttons. It should first establish the user workflow architecture and then move one coherent slice at a time. The first slice should be the **Selected Phoneme Workbench** because it resolves the most frequent and highest-friction speech workflow: source assignment, timing, preview, and render preparation for the selected phoneme.
