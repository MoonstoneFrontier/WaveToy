# Task 018 — Emotional Note Wheel

WaveToy's Circle of Fifths Note Wheel now presents notes as emotional characters instead of plain theory-only pitch names. Recipes continue to store only note names; moods, colors, and relationship labels are derived at runtime by the UI.

## Emotion and color mapping

| Note | Emoji | Mood | Color |
| --- | --- | --- | --- |
| C | 🙂 | Balanced | `#F4F1DE` |
| G | 😁 | Confident | `#FFD166` |
| D | 🚀 | Adventurous | `#F8961E` |
| A | 🔥 | Energetic | `#F94144` |
| E | ⚡ | Excited | `#F3722C` |
| B | 🤩 | Brilliant | `#F9C74F` |
| F# | 🌌 | Cosmic | `#577590` |
| C# | 🔮 | Mysterious | `#6A4C93` |
| G# | 🌙 | Dreamy | `#4361EE` |
| D# | 🥲 | Melancholy | `#4D908E` |
| A# | 😢 | Sad | `#277DA1` |
| F | 🫂 | Warm | `#90BE6D` |

## Relationship system

Relationships are calculated around the circle of fifths, comparing any selected note to the current main note as the emotional center or “Home.”

- Same note: `🏠 Home`
- One step clockwise: `🤝 Best Friend`
- One step counterclockwise: `🫂 Comfort`
- Two steps clockwise: `🚶 Adventure`
- Three steps clockwise: `🔥 Energy`
- Four steps clockwise: `⚡ Excitement`
- Two steps counterclockwise: `😢 Tension`
- The most distant fifths positions: `🧭 Far Away`
- Other nearby positions: `🌈 Partner`

For example, when C is Home, G is a Best Friend, D is an Adventure, A brings Energy, E brings Excitement, F provides Comfort, and A# creates Tension.

## Current UI behavior

- Note bubbles display their note name, emoji, and mapped background color.
- The selected note appears larger with a stronger outline and glow.
- Hovering over a note bubble updates the tooltip with the note mood and relationship to Home.
- The note wheel dialog shows both the Home note and the selected note's mood/relationship summary.
- Per-wave note buttons now show the note emoji beside the pitch name.
- The Pitch Toy panel includes an emotional explanation area and uses the selected note color as a swatch.

## Future integration opportunities

- Wave Explorer cards can prefix lanes with note emojis, such as `Melody: 🙂 C`, `Atmosphere: 🌙 G#`, or `Bass: 🔥 A`.
- Future timeline clips can use note colors for clip accents and note emojis in clip titles.
- Preset browsers can use note-character labels without changing the saved recipe schema.
- Subtle arcs between close relationships could be added to the wheel for visual teaching without changing synthesis behavior.
