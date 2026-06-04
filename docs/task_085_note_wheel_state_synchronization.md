# Task 085 — Note Wheel State Synchronization and Live Refresh

Task 085 hardens the note/color/mood picker added in Tasks 083 and 084. The focus is live UI correctness: visible wheel dialogs, note buttons, labels, colors, tooltips, previews, and Voice Range wording should all follow the current pitch state without adding new synthesis features or persistent project schema fields.

## Live refresh triggers

WaveToy now centralizes note-wheel refreshes through window-level helpers:

- `_refresh_note_wheel_dialogs()` refreshes every visible note wheel dialog from the current home note and the owning wave's selected pitch class.
- `_refresh_note_pitch_panels()` refreshes existing wave pitch-panel note buttons and emotional relationship labels.

These helpers are called when the main/base note changes and when pitch controls resynchronize. Existing wave note controls still update their own panel state, and visible dialogs refresh from the same current home note rather than keeping stale labels.

## Pitch class vs displayed spelling

The wheel stores selected notes as normalized pitch classes such as `C#` and `A#`. Display spelling is separate:

- **Auto** follows the current home key orientation.
- **Sharps** forces sharp spellings.
- **Flats** forces flat spellings.

Changing spelling mode changes labels and tooltips only. It does not change the selected pitch class, and the default display still shows one spelling rather than both enharmonic names.

## Layout refresh behavior

Switching between **Intervals** and **Circle of Fifths** updates the picker geometry immediately while preserving the selected pitch class.

- **Intervals** keeps the current home/root at the top and then proceeds chromatically.
- **Circle of Fifths** intentionally preserves the fixed order `C, G, D, A, E, B, F#, C#, G#, D#, A#, F`.

Known limitation: Circle of Fifths does not currently rotate around the home note. A future optional mode may add that behavior without replacing the stable fixed-order teaching view.

## Preview state behavior

Note-wheel previews remain short, in-memory sine tones. Starting a new preview first asks `sounddevice` to stop current playback, then plays the new home, note, melodic interval, or harmonic interval preview. Closing or accepting the dialog also stops preview playback when `sounddevice` is available.

Preview audio uses pitch class and current tuning values for sound. Current spelling affects only visual labels and tooltips. No preview audio files are written to disk.

## Voice Range refresh behavior

The Voice Range label continues to derive from the current tuned frequency when available and falls back to the slider threshold labels when frequency is unavailable. Main note, octave/range, cents, tuning method, tuning root, and A4 reference changes all flow through pitch synchronization, so the visible register label updates with the current tuned frequency. The wording remains musical-register-only and does not imply gender, body size, volume, or biological identity.
