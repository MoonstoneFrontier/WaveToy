# Task 097 — Motion Curve Visualization and Transition Analysis

Task 097 adds a read-only Motion Curves inspection layer to **Articulation Timeline → Timeline → Motion**. It builds on the Task 096/096a Motion Timeline and Viseme Track by showing how normalized articulator values move through phoneme holds and transition regions.

## Curve sampling behavior

- `build_motion_curve_points(chain_items, sample_step_ms=25)` derives samples from the existing articulation chain data and the same phoneme-pair transition interpolation used by motion previews.
- The helper samples both hold and transition segments without rendering audio.
- The default sample step is 25 ms.
- The minimum accepted sample step is clamped to 10 ms.
- The maximum point count is capped at 1200 for UI/test safety.
- Empty chains return an empty point list and safe zero summaries.
- The sampled data is deterministic and does not mutate phoneme presets or chain items.

## Sampled articulator fields

Each `MotionCurvePoint` contains:

- `time_ms`
- `mouth_open`
- `lip_rounding`
- `tongue_height`
- `tongue_frontness`
- `nasal_open`
- `closure`
- `voiced_gain`
- `airflow`
- `phoneme`
- `segment_kind`
- `transition_progress`

The default visible curves are Mouth, Lips, Tongue Height, and Closure. Tongue Frontness, Nasal, Voicing, and Airflow are available as optional toggles.

## Fit-to-view behavior

The curve canvas is compact, read-only, and fit-to-view only. It uses Qt painting directly and adds no external plotting dependency. Transition regions are shaded behind the curves and labeled with concise phoneme-pair labels such as `AH→M`, while the red playhead remains the dominant timing marker.

Functional horizontal zoom and deeper curve-detail inspection remain deferred to Task 098.

## Transition analysis

The Motion Summary card now includes a compact Transition Analysis line derived from motion segments and sampled curves:

- transition count
- average transition duration
- longest transition duration
- shortest transition duration
- fastest sampled curve change
- largest mouth, lip-rounding, tongue, and closure changes

Limitations: the analysis is a lightweight debugging summary, not a scientific articulatory metric. It compares sampled normalized UI values, so very short transitions are constrained by the sampling step.

## Export and persistence safety

Motion curve samples are debug/UI data only:

- no project schema fields are added
- no motion curve data is serialized into chain/project files
- Viseme JSON export remains unchanged
- Animation JSON export remains unchanged
- no `motion_curve`, `motion_curves`, or `curve_points` payload fields are added


## Task 097a discoverability follow-up

Task 097a keeps the Motion Curve work in place and restores discoverability for the older performance controls after the layout split:

- The internal Timeline subtab is labeled **Timing / Performance**.
- The Chain page includes the visible note “Tempo / Singing Preview moved to Timeline → Timing.” with a shortcut button.
- The Timing / Performance page adds a compact **Performance Timing** header above Musical Timing and Singing Preview controls.
- The old crowded Performance tab is not restored.
- Render/audio behavior is unchanged.

### Playback-path investigation

Sample/live preview and rendered-word playback intentionally use different paths. Live Preview renders the selected phoneme, selected transition, selected timeline fragment, or CV/VC combination through short preview helpers, then plays the temporary audio. Play Word, Create Word, and Export Word use `_render_word_audio_for_current_chain()` and the current word-render signature/cache before playback or file export. If a user hears sample playback distortion but exported word audio is clean, compare the selected live-preview target against the full word render path and check whether playback rate limiting or fallback playback is active before changing synthesis.

Accessibility check: Smooth Mouth Transitions, Word Render Mode, Bypass formants, Validate Continuous, Run Stop Test, Formant Intensity, and Pitch Glide remain in Render → Render Mode Settings. Musical Timing, BPM, snap, Count-in, Show Beat Grid, and Singing Preview are in Timeline → Timing / Performance.
