# Task 023 — Articulation Lab Workspace Redesign

## Reason for workspace redesign

The Articulation Lab had grown from a playful phoneme builder into a cramped settings-style page. The previous layout stacked the Wave Toy banner, tab navigation, a large Articulation Lab title, a long subtitle, a vocal-tract drawing, dense sliders, and multiple collapsible phoneme sections. At normal desktop sizes that made the most important speech-building tasks compete for vertical space.

This redesign prioritizes a toy-like speech workstation:

- A compact application header preserves the Wave Toy identity while reducing wasted height.
- The Articulation Lab keeps a small local title and an info badge instead of another large page header.
- The main workspace is split into a focused vocal display, a readable control card, and one active phoneme drawer.
- Scrolling is limited to the drawer and the articulation controls when their contents overflow.

## Header/tab merge approach

The in-app title banner was shortened so `⭐ Wave Toy ⭐` and `Build Sounds by Shaping Waves` still appear prominently without consuming as much height. The application shell spacing was tightened, and the tab bar remains directly attached beneath the banner so the banner and navigation read as one compact header region rather than separate stacked chrome.

Inside the Articulation Lab, the former large centered title and long explanatory subtitle were replaced with a small workstation header:

- `🗣 Articulation Lab`
- A compact badge explaining that the page is a toy speech workstation.

This avoids a third large title/header row and reserves more space for the explorer and controls.

## Icon rail and drawer behavior

The old right-side stack of collapsible sections was replaced by a right-side icon rail plus one active drawer. The rail has five large buttons:

- `😀` Vowels
- `🌬` Fricatives
- `💥` Stops
- `👃` Nasals
- `💾` Saved Phonemes

Only one drawer page is visible at a time. Clicking an icon switches the `QStackedWidget` to the matching page and checks only that rail button, creating a single focused phoneme selection surface. Each drawer uses one scroll area for the whole drawer body, avoiding nested scrolling inside individual phoneme sections.

## Vocal Explorer/control split

The Vocal Explorer and articulation controls now live in separate cards in the left main workspace:

1. **Vocal Explorer** sits at the top with a bounded height so the mouth visualization remains clear but does not consume the whole page.
2. **Articulation Controls** sits below it and receives the larger share of vertical space.

The transport buttons remain with the Vocal Explorer so Play, Loop, and Stop stay near the current phoneme display.

## Toy control styling

Dense slider rows were replaced with toy-style articulation rows. Each row includes:

- A large emoji/plain-English label.
- A low-end meaning.
- A horizontal slider.
- A high-end meaning.
- A current value badge.

The voice toggle was also restyled as a large card-like control with an explanatory hint. The controls card scrolls only if the available vertical space is not enough for all controls.

## Saved phoneme card redesign

Saved phonemes remain reusable cards, but the saved drawer gives them a dedicated card workspace instead of burying them under collapsed sections. Each saved card continues to show:

- Phoneme name.
- IPA symbol.
- Phoneme family/summary.
- Play action.
- Load/edit action.
- Duplicate action.
- Delete action.

The cards keep touch-like minimum action sizes and are placed in the saved drawer below a large Save Phoneme button.

## Scroll behavior

The Articulation Lab no longer relies on full-window scrolling for the main workspace. Controlled scrolling is limited to:

- The active phoneme drawer.
- The articulation controls card, if the controls overflow.

This keeps mouse-wheel behavior focused where the pointer is and avoids nested scroll fights. Wave Explorer zoom/pan and playback scrolling were not modified.

## Remaining limitations

- The layout is still implemented in the single-file PySide6 application to preserve the current project structure.
- The drawer assumes the existing consonant preset section order: fricatives, stops, then nasals.
- Runtime GUI verification requires PySide6's native library dependencies, including `libGL.so.1`, to be available in the environment.
