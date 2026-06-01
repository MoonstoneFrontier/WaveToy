# Task 051 — Split Articulation Timeline and Fix Loop Routing

## Summary

The articulation workflow now separates single-phoneme design from chain and word editing:

1. **Articulation Lab** focuses on designing, previewing, saving, and staging one phoneme.
2. **Articulation Timeline** owns the shared chain model, block timing, transition curves, word motion preview, word rendering, export, saved chain I/O, and transfer to the main Timeline.

Both tabs continue to use the existing `ArticulationChainItem` list on the main window, so there is still one editable chain state and existing chain JSON files remain compatible.

## New tab separation

The top-level articulation workflow is now split into:

- **Articulation Lab** — source voice selection, vocal tract preview, phoneme families, current phoneme controls, phoneme preview, save phoneme, and add phoneme to Articulation Timeline.
- **Articulation Timeline** — chain blocks, block timing, transition timing, transition curves, raw chain preview, smoothed word rendering, word motion preview, speech assets, chain save/load, word export, and Timeline transfer.

This keeps phrase-level controls out of the phoneme-design workspace while preserving the shared chain and saved-chain compatibility.

## Articulation Lab responsibilities

Articulation Lab should be used when the user is shaping one phoneme. Its visible responsibilities are:

- Select a phoneme family or saved phoneme.
- Edit the vocal tract and articulatory sliders for the current phoneme.
- Choose or reset the source voice for the current phoneme.
- Play, loop, and stop the current phoneme preview.
- Save the current phoneme.
- Add the current phoneme to the shared Articulation Timeline chain.

Word creation, chain playback, chain save/load, word export, and Timeline transfer were removed from this tab so they no longer crowd phoneme-design controls.

## Articulation Timeline responsibilities

Articulation Timeline should be used after phonemes have been staged into a chain. Its responsibilities are:

- Display and edit the shared phoneme-chain blocks.
- Adjust individual block durations by dragging block edges.
- Adjust transition timing and transition curves between blocks.
- Preview raw chain order with **Play Chain (raw sequence)**.
- Render and preview output with **Play Word (smoothed render)** and Word Motion Preview using the selected render mode: Plain, Clip Crossfade, or Continuous Mouth Motion.
- Create syllables/words as Speech Assets.
- Export the rendered word audio.
- Save and load the chain.
- Send the rendered word or raw chain to the main Timeline.

## Word render modes

Play Word now routes through the selected word render mode before playback:

- **Plain** concatenates rendered phonemes without the coarticulated overlap path, giving a baseline sequence for comparison.
- **Clip Crossfade** uses the clip-overlap/coarticulation path and is intentionally distinct from Plain.
- **Continuous Mouth Motion** uses the continuous articulator-envelope renderer and preserves voiced source energy instead of letting noise replace voiced gain.

Each render path writes debug output with `render_mode`, `voiced_gain`, `noise_gain`, `source_mode`, and `final_peak` so regressions such as whisper-like Continuous output or identical Plain/Crossfade routing are easier to spot.

## Play Word vs Play Chain

The two playback paths are intentionally separated and labeled differently:

- **Play Chain (raw sequence)** plays each phoneme sequentially through the raw phoneme render path. It is useful for checking order and individual block edits, but it may sound less smooth.
- **Play Word (smoothed render)** plays the smoothed/coarticulated rendered word using transition handling and Word Motion Preview/final render settings.

Tooltips on the buttons explain this distinction so the two controls do not appear interchangeable.

## Loop behavior decision

The ambiguous global Loop action was isolated by active workspace:

- Voice/Classic-style synthesis workspaces continue to use the existing live loop.
- Articulation Lab uses **Loop Phoneme Preview**, which loops only the current phoneme and bypasses the normal one-second playback activation gate on loop ticks so short phonemes do not fight the rate limiter.
- Articulation Timeline uses **Loop Word Motion**, which loops the rendered word/motion preview and toggles off when activated while already looping.
- Unsupported workspaces show: `Loop is unavailable for this workspace until context looping is rebuilt.`

Stop now funnels through the broad stop path so it stops live loop playback, phoneme preview loops, word motion audio, timeline playback, and fallback subprocess playback.

## Data flow

The intended data flow is now explicit:

1. Design a phoneme in Articulation Lab.
2. Click **Add to Articulation Timeline**.
3. Edit the shared chain in Articulation Timeline.
4. Tune durations, transitions, and transition curves.
5. Create a syllable/word/phrase Speech Asset.
6. Preview or export the result.
7. Send the result to the main Timeline.

The chain remains backed by the existing `articulation_chain_items` list and `ArticulationChainItem` serialization, so saved articulation chains continue to load through the existing loader.
