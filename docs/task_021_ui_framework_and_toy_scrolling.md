# Task 021 — Unified UI Framework and Toy Scrolling System

## Summary

This task introduces a small, shared WaveToy UI framework inside `wave_toy.py` so the single-file desktop app can use consistent touch-friendly sizes, toy colors, padding, and scrolling behavior without adding new dependencies or changing the main entry point.

## Design system

### `WaveToySizing`

`WaveToySizing` centralizes the project sizing tokens used by the refreshed controls:

- Minimum touch target: **48 px**
- Normal button height: **56 px**
- Large button height: **72 px**
- Icon sizes: **32 / 48 / 64 px**
- Minimum card height: **96 px**
- Toy scrollbar width: **22 px**
- Shared page margins, card padding, and section spacing

### `WaveToyTheme`

`WaveToyTheme` centralizes the toy palette and shared style snippets for:

- Larger default buttons and form controls
- Touch-friendly checkboxes
- Rounded toy scrollbars
- Consistent surfaces, cards, accents, and dashboard colors

The app still uses its existing custom per-panel styles where needed; the theme is layered on top to remove tiny defaults and normalize spacing.

## Toy scrolling

### `WaveToyScrollArea`

`WaveToyScrollArea` replaces ad-hoc `QScrollArea` usage in the main editor, Timeline, Audio Palette, and Saved Phoneme Cards.

Supported behaviors:

- Mouse-wheel scrolling with configurable speed
- Drag-to-scroll on the scroll viewport and eligible content widgets
- Kinetic scrolling after drag release
- Oversized 22 px rounded scrollbar tracks and handles
- Keyboard navigation with arrows and page keys
- Horizontal/vertical conflict reduction by honoring the dominant wheel or drag direction

The Timeline canvas keeps its own clip-drag behavior by disabling content-level drag scrolling for that canvas while still using WaveToy scrollbars and wheel behavior around it.

## Articulation Lab layout cleanup

The Articulation Lab now groups preset shelves into touch-friendly collapsible sections:

- Vowels
- Fricatives
- Stops
- Nasals
- Saved Phonemes

Only the vowel and saved sections start expanded. The consonant sections start collapsed to reduce visual density and scrolling, while keeping all existing preset buttons and saved phoneme behavior available.

## Timeline and palette layout

The Timeline keeps its existing card-based clip canvas and Audio Palette cards, but the scrolling containers now use the unified WaveToy-managed scroll area and larger scrollbar handles. Palette cards keep drag-to-timeline behavior; the scroll area handles wheel scrolling and viewport dragging without replacing palette card drag behavior.

## Wave Explorer controls

The Wave Explorer preserves mouse-wheel waveform zoom behavior and adds explicit touch-friendly controls for:

- Zoom in
- Zoom out
- Pan left
- Pan right
- Reset zoom

These controls appear in both the embedded dashboard Wave Explorer and the pop-out Wave Explorer window.

## Verification notes

Programmatic verification completed:

```bash
python -m py_compile wave_toy.py
```

An offscreen Qt instantiation check was attempted, but the container is missing `libGL.so.1`, so PySide6 cannot import its GUI bindings in this environment. This is an environment dependency issue rather than a syntax issue.

Manual checks recommended on a desktop with PySide6 GUI dependencies installed:

- Confirm no clipped button labels in Classic Editor, Articulation Lab, Timeline, and Wave Explorer.
- Confirm all buttons visibly meet the 48 px touch-target baseline.
- Confirm mouse-wheel scrolling works in WaveToyScrollArea regions.
- Confirm drag-to-scroll and kinetic scrolling work where content does not own drag gestures.
- Confirm Timeline clip dragging still works.
- Confirm Audio Palette card dragging still works.
- Confirm scrollbar handles are visibly large and rounded.
- Confirm Articulation Lab requires less scrolling with collapsed consonant sections.
- Confirm Wave Explorer mouse-wheel zoom still works and zoom/pan buttons operate correctly.
