# Task 096 — Articulation Motion Timeline and Viseme Track

## Scope

Task 096 adds a read-only motion-analysis layer to **Articulation Timeline → Timeline → Motion**. It exposes animation timing derived from the existing articulation chain without changing synthesis, project storage, or animation/viseme export schemas.

## Motion tab additions

The Motion workflow now presents these sections in order:

1. **Motion Summary**
2. **Motion Timeline**
3. **Viseme Track**
4. **Word Motion Preview**
5. **Vocal tract side-cutaway (SVG)**

The Motion Timeline and Viseme Track are derived views only. They do not store motion state, do not add project fields, and do not alter Viseme JSON or Animation JSON payloads.

## Segment boundary policy

Motion and viseme segments use half-open timing intervals for active-segment detection:

- normal segment containment is `start_ms <= playhead_ms < end_ms`;
- the final segment is still treated as active when the playhead reaches the total duration endpoint.

This avoids dual-active ambiguity at shared boundaries such as a hold ending at `200 ms` and a transition starting at `200 ms`: only the later segment is active at the boundary.

## Fit-to-view behavior

Task 096 timeline canvases are intentionally **fit-to-view** and read-only. They map the full current motion duration across the available lane width so users can inspect durations and pacing at a glance.

Functional horizontal zoom for detailed animation curves is deferred to Task 098. Until that work exists, Motion Timeline text should not imply that a user-controlled zoom scale changes the rendering geometry.

## Motion Summary behavior

The compact Motion Summary reports:

- phoneme count;
- unique viseme count;
- total viseme holds;
- total motion duration;
- transition count;
- average phoneme duration.

Example: `Motion Summary: 5 phonemes • 3 unique visemes / 5 viseme holds • 900 ms total • 4 transitions • avg phoneme 180 ms`.

Unique viseme count is distinct from viseme holds so repeated shapes are easy to identify during animation pacing review.

## Non-goals

- No synthesis changes.
- No motion playback rewrite.
- No project schema changes.
- No Viseme JSON schema changes.
- No Animation JSON schema changes.
- No new export formats.
- No ML lip-sync or voice cloning.
