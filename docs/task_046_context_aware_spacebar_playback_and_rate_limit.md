# Task 046: Context-Aware Spacebar Playback and Rate Limit

## Context-aware Spacebar behavior

Spacebar now routes through `WaveToyWindow._handle_spacebar_playback()` instead of directly calling the base synthesis `_play()` path. The router resolves the active main tab with `self.tabs.currentWidget()` and prefers each tab widget's stable `objectName()` before falling back to normalized tab text. This avoids coupling playback routing to decorative labels or future tab label copy changes.

Shift+Space continues to use the existing live-loop toggle path.

## Tab playback routing table

| Main tab | Spacebar target | Current implementation |
| --- | --- | --- |
| Synthesis | Current rendered WaveToy synthesis audio | Calls `_play()` |
| Voice Lab | Current rendered WaveToy synthesis audio | Calls `_play()` |
| Wave Explorer | Active Wave Explorer workspace output or current rendered audio | Calls `_play_wave_explorer_context()`, currently falls back to `_play()` with TODO for deeper workspace renders |
| Articulation Lab | Current selected phoneme preview, or chain/word context when chain widgets have focus | Calls `_play_articulation_context()` |
| Articulation Timeline | Created word/current chain render, word motion audio when applicable, then chain fallback | Implemented as `_play_articulation_timeline_context()` and reached from Articulation Lab chain/timeline focus |
| Graphical Editor | Selected graphical section output, selected layer/mix, then full synthesis output | Calls `_play_graphical_editor_context()`, currently falls back to `_play()` with TODO for section/layer renders |
| Timeline | Final arranged timeline mix from the current playhead | Calls `_timeline_play_story()`, which now slices playback from `timeline_playhead_seconds` |
| Library | Selected Speech Asset preview, selected Audio Asset preview, no-op status message otherwise | Calls `_play_library_context()` |

## Rate limiting behavior

Playback activation is globally rate-limited through `WaveToyWindow._can_start_playback()`. The default field is:

```python
self.playback_rate_limit_seconds = 1.0
```

That default permits a maximum of one user-initiated playback activation per second. The timestamp is stored in:

```python
self.last_playback_activation_monotonic = 0.0
```

When a playback start is blocked, WaveToy shows the non-modal status message:

> Playback is rate-limited. Try again in a moment.

The limiter is applied to Spacebar routing, primary Play buttons, Timeline Play, Articulation play/preview actions, saved phoneme previews, Speech Asset previews, Library Audio Asset preview routing, and live-loop activation. Internal timed live-loop refreshes are not rate-limited because they are part of an already-started playback mode rather than a new user activation.

## Stop/cancel exemption

Stop paths are intentionally not rate-limited. The main Stop button, Timeline Stop, and articulation motion stop remain immediate so users can interrupt playback regardless of the last activation time.

## Remaining TODOs

- Wave Explorer Spacebar routing currently falls back to the shared synthesis render until Wave Explorer has separate workspace-specific final renders.
- Graphical Editor Spacebar routing currently falls back to the shared synthesis render until selected section/layer mixdown outputs are exposed as playback-ready audio products.
- Library Audio Asset preview uses the existing app playback helper; a future pass can add a sample-rate-aware helper for imported assets whose source sample rate differs from WaveToy's synthesis sample rate.
