# WaveToy

WaveToy is a Python desktop audio/sci-fi soundscape generator centered on a single PySide6 GUI script. It is currently an educational waveform synthesizer for exploring sound waves, musical tuning, stereo motion, file export, and experimental Paulstretch-style ambience.

This repository is intentionally being stabilized before larger playback, cancellation, debug logging, and responsiveness work. Avoid major redesigns until the audio lifecycle issues are addressed in focused follow-up tasks.

## Current entry point

Run the app from:

```bash
python wave_toy.py
```

`wave_toy.py` defines `main()` and executes it under the standard `if __name__ == "__main__"` guard. Preserve this script name as the primary entry point unless a future task explicitly changes it.

`wave_toy_single_module.py` is also present and appears to contain a similar single-file implementation snapshot. Treat `wave_toy.py` as the active entry point for now.

## Dependencies

Imports in the current Python files indicate these runtime dependencies:

Required:

- `PySide6` — GUI framework
- `numpy` — audio/waveform array processing

Optional:

- `sounddevice` — direct audio playback; the app falls back when unavailable
- `ffmpeg` executable — MP3, OGG, and FLAC export support through subprocess calls

The remaining imports are from the Python standard library.

## Setup with `.venv`

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install PySide6 numpy
```

Optional direct playback support:

```bash
python -m pip install sounddevice
```

Optional export support for MP3/OGG/FLAC requires installing `ffmpeg` with your operating system package manager and ensuring it is available on `PATH`.

## Run

```bash
source .venv/bin/activate
python wave_toy.py
```

## Safe verification

Before finalizing code changes, run:

```bash
python -m py_compile wave_toy.py
```

For dependency visibility in a fresh environment, check whether the imported third-party packages are installed:

```bash
python - <<'PY'
import importlib.util
for package in ['numpy', 'PySide6', 'sounddevice']:
    print(f'{package}:', 'found' if importlib.util.find_spec(package) else 'missing')
PY
```

## Known current issues

- Long-running Paulstretch playback has recently not stopped reliably.
- Stop/cancel behavior, playback lifecycle control, and UI responsiveness need focused follow-up work.
- Debug logging is not yet formalized for audio lifecycle events.
- `sounddevice` and `ffmpeg` availability varies by local machine, so playback/export behavior may differ by environment.

## Future development notes

- Prefer small, reviewable patches with clear before/after verification.
- Do not remove existing audio generation features without explicit approval.
- Preserve `wave_toy.py` as the main script name unless instructed otherwise.
- Prioritize audio lifecycle control, cancellation, debug logging, and responsiveness in upcoming tasks.
- Avoid introducing large new dependencies unless they are clearly required and documented.
