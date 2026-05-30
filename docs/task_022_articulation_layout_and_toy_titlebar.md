# Task 022 — Articulation Lab Layout and Toy Title Banner

## Layout problem observed

The Articulation Lab sidebar had independent preset sections and a nested saved-phoneme scroll area. When the window height was constrained, expanded sections competed for vertical space and the saved cards could introduce nested scrolling. Preset buttons also used large fixed dimensions inside a narrow sidebar, which made the selector area feel cramped.

## Sidebar redesign approach

The right Articulation Lab sidebar now uses one main `WaveToyScrollArea` for all selector sections, the save button, and saved phoneme cards. The sidebar content is a single vertical stack, so expanded sections participate in one predictable scroll region instead of creating scroll fights.

Preset groups are built by a shared helper that creates a roomy two-column grid with consistent spacing, card padding, expanding button widths, and a 56 px minimum height for phoneme selector buttons.

## Collapsible section behavior

Vowels, Fricatives, Stops, Nasals, and Saved Phonemes remain collapsible. Each section expands within the single sidebar scroll area, and section contents are normal widgets rather than nested scroll areas. Headers keep the same large, touch-friendly style with added padding.

## Toy title bar implementation

The application now has an in-app branded banner above the tab widget. It leaves the native operating-system window controls intact and does not use custom title-bar chrome. The banner displays:

- `⭐ Wave Toy ⭐`
- `Build Sounds by Shaping Waves`
- toy icon rails with train, star, wave, and speaker icons

The banner uses rounded glossy panel styling and the existing WaveToy pink, cream, blue, and yellow palette while staying compact.

## Scroll behavior

The Articulation Lab sidebar reuses the existing `WaveToyScrollArea` toy scrollbar styling from the shared UI framework. Its large handles and wheel handling apply to the whole sidebar. The saved phoneme list no longer has its own scroll area, so mouse-wheel movement should scroll the sidebar predictably.

## Remaining limitations

- The preset grid is intentionally two columns for readability rather than a fully custom flow layout.
- Saved cards still expose Load, Rename, and Duplicate in addition to the requested Play and Delete controls, preserving existing saved-phoneme functionality.
- Runtime GUI verification could not complete in this container because PySide6 import fails without `libGL.so.1`; syntax compilation still passes.
